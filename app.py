from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# 설정
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 데이터베이스 연결 및 예시 데이터
troubles = []
trouble_id = 1

# 파일 확장자 검사
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    global trouble_id

    if request.method == "POST":
        trouble_date = request.form["trouble_date"]
        device_code = request.form["device_code"]
        device_name = request.form["device_name"]
        user_name = request.form["user_name"]
        trouble_text = request.form["trouble_text"]
        solution = request.form["solution"]
        category = request.form["category"]
        tags = request.form["tags"]
        image = request.files.get("image")

        # 파일 업로드 처리
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        # 트러블 데이터 저장
        new_trouble = {
            "id": trouble_id,
            "trouble_date": trouble_date,
            "device_code": device_code,
            "device_name": device_name,
            "user_name": user_name,
            "trouble_text": trouble_text,
            "solution": solution,
            "category": category,
            "tags": tags,
            "image": filename
        }

        troubles.append(new_trouble)
        trouble_id += 1

        return redirect(url_for("index"))

    return render_template("index.html", troubles=troubles)

@app.route("/trouble/<int:trouble_id>")
def trouble_detail(trouble_id):
    trouble = next((t for t in troubles if t["id"] == trouble_id), None)
    if trouble:
        return render_template("trouble_detail.html", trouble=trouble)
    return "Trouble not found", 404

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form["search_query"]
        tags = request.form["search_tags"]
        results = [t for t in troubles if query.lower() in t["trouble_text"].lower() and tags in t["tags"]]
        return render_template("search_results.html", results=results)
    return render_template("search.html")

@app.route("/stats")
def stats():
    return render_template("stats.html", troubles=troubles)

if __name__ == "__main__":
    app.run(debug=True)
