from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def index():
    return "后端部署成功，Hello from yunivera!"


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok")


@app.route("/check", methods=["GET", "POST"])
def check():
    if request.method == "GET":
        # 方便在浏览器里直接访问做“烟囱测试”
        return (
            '请用 POST 调用此接口，示例：'
            'curl -X POST https://consistency-checker-backend1.onrender.com/check '
            '-H "Content-Type: application/json" '
            '-d \'{"paragraphs":["你好","这是一个很长很长的句子……"]}\''
        )

    # POST：真正的检测逻辑
    data = request.get_json(silent=True) or {}
    paragraphs = data.get("paragraphs", [])

    result = []
    for i, text in enumerate(paragraphs):
        review = "句子过长，建议拆分。" if len(text) > 100 else "无明显问题。"
        result.append({"id": i, "review": review})

    return jsonify({"result": result})


if __name__ == "__main__":
    # 本地调试用；Render 上仍然用 gunicorn 启动
    app.run(host="0.0.0.0", port=5000)
