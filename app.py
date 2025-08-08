from flask import Flask, request, jsonify
from flask_cors import CORS
from utils.parser import parse_docx
from utils.checker import run_consistency_check

app = Flask(__name__)
CORS(app)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    paragraphs = parse_docx(file)
    return jsonify({'paragraphs': paragraphs})

@app.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    result = run_consistency_check(data['paragraphs'])
    return jsonify({'result': result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)