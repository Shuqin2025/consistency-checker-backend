from __future__ import annotations

import json
import logging
import os
import time
import uuid
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS

APP_VERSION = "1.0.0"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")  # 部署后可改为你的前端域名
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "1048576"))  # 1MB

# ------------ 日志配置（结构化 + 时间戳）------------
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "msg": record.getMessage(),
            "request_id": getattr(g, "request_id", None),
            "path": getattr(request, "path", None),
            "method": getattr(request, "method", None),
        }
        return json.dumps(payload, ensure_ascii=False)

logger = logging.getLogger("yunivera")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ------------ Flask ------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

# 请求钩子：生成 request_id、限制体积、记录原始体积
@app.before_request
def _before_request():
    g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    raw_len = request.content_length or 0
    g.raw_len = raw_len
    if raw_len > MAX_BODY_BYTES:
        logger.warning(f"Payload too large: {raw_len} bytes > {MAX_BODY_BYTES}")
        return jsonify(error="Payload too large"), 413

# 统一异常处理
@app.errorhandler(Exception)
def _handle_error(e):
    logger.exception(f"Unhandled error: {e}")
    return jsonify(error="Internal server error"), 500

# 统一包装：记录入参、耗时
def traced(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            return fn(*args, **kwargs)
        finally:
            cost = int((time.time() - start) * 1000)
            logger.info(f"done in {cost}ms")
    return wrapper

# ------------ 路由 ------------
@app.route("/", methods=["GET"])
def index():
    return "后端部署成功，Hello from yunivera!"

@app.route("/ping", methods=["GET"])
def ping():
    return "pong"

@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", version=APP_VERSION)

@app.route("/version", methods=["GET"])
def version():
    return jsonify(version=APP_VERSION)

@app.route("/check", methods=["GET", "POST"])
@traced
def check():
    if request.method == "GET":
        # 方便在浏览器直接访问的说明页（烟囱测试）
        text = (
            "请用 POST 调用此接口，示例：\n\n"
            "curl -X POST https://consistency-checker-backend1.onrender.com/check \\\n"
            "-H \"Content-Type: application/json\" \\\n"
            "-d '{\"paragraphs\":[\"你好\",\"这是一个很长很长的句子……\"]}'\n"
        )
        return text, 200, {"Content-Type": "text/plain; charset=utf-8"}

    # POST：真正的检测逻辑
    body = request.get_json(silent=True) or {}
    logger.info(f"收到请求数据: {json.dumps(body, ensure_ascii=False)}  raw={g.raw_len}B")
    paragraphs = body.get("paragraphs", [])

    # 容错：非数组直接处理为空
    if not isinstance(paragraphs, list):
        paragraphs = []

    result = []
    for i, text in enumerate(paragraphs):
        try:
            t = str(text or "")
        except Exception:
            t = ""
        review = "句子过长，建议拆分。" if len(t) > 100 else "无明显问题。"
        result.append({"id": i, "review": review})

    return jsonify({"result": result})


if __name__ == "__main__":
    # 本地调试用；Render 上还是用 gunicorn 启动
    app.run(host="0.0.0.0", port=5000)

