import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# 指定文件保存的目录
UPLOAD_FOLDER = 'uploads'
# 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/upload', methods=['POST'])
def upload_file():
    # 检查是否有文件在请求中
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    # 如果用户没有选择文件，浏览器也会提交一个空的文件名
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return jsonify({"message": f"File {filename} uploaded successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True)
