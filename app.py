import os
import sqlite3
import base64
import io
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# uploads 폴더 없으면 자동 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = 'ulvac_troubleshooting.db'

# DB 연결
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# DB 초기화
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS troubleshooting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trouble_date TEXT,
            device_code TEXT,
            device_name TEXT,
            user_name TEXT,
            trouble_text TEXT,
            solution TEXT,
            category TEXT,
            tags TEXT,
            image TEXT,
            useful_count INTEGER DEFAULT 0
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trouble_id INTEGER,
            commenter_name TEXT,
            comment TEXT,
            FOREIGN KEY (trouble_id) REFERENCES troubleshooting(id)
        )
    ''')
    conn.commit()
    conn.close()

# 루트: 트러블 등록/검색
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        if 'search_query' in request.form:
            search_query = request.form['search_query']
            search_tags = request.form['search_tags']
            query = "SELECT * FROM troubleshooting WHERE trouble_text LIKE ? OR tags LIKE ?"
            like_query = f"%{search_query}%"
            like_tags = f"%{search_tags}%"
            results = cur.execute(query, (like_query, like_tags)).fetchall()

            output = []
            for r in results:
                comments = cur.execute("SELECT * FROM comments WHERE trouble_id = ?", (r['id'],)).fetchall()
                output.append((r, 1.0, r['useful_count'], comments))  # similarity 고정
            conn.close()
            return render_template('index.html', results=output)

        else:
            # trouble 등록
            trouble_date = request.form['trouble_date']
            device_code = request.form['device_code']
            device_name_select = request.form['device_name_select']
            device_name_input = request.form.get('device_name')
            device_name = device_name_input if device_name_select == '직접입력' else device_name_select
            user_name = request.form['user_name']
            trouble_text = request.form['trouble_text']
            solution = request.form['solution']
            category = request.form['category']
            tags = request.form['tags']

            image_filename = None

            # 파일 업로드
            if 'image' in request.files:
                image = request.files['image']
                if image and image.filename != '':
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_filename = filename

            # 클립보드 이미지 업로드
            clipboard_data = request.form.get('clipboard_image_data')
            if clipboard_data:
                img_data = clipboard_data.split(',')[1]
                img_bytes = base64.b64decode(img_data)
                clipboard_filename = f"clipboard_{device_code}_{user_name}.jpg"
                with open(os.path.join(app.config['UPLOAD_FOLDER'], clipboard_filename), 'wb') as f:
                    f.write(img_bytes)
                image_filename = clipboard_filename

            cur.execute('''
                INSERT INTO troubleshooting (trouble_date, device_code, device_name, user_name, trouble_text, solution, category, tags, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trouble_date, device_code, device_name, user_name, trouble_text, solution, category, tags, image_filename))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    conn.close()
    return render_template('index.html')

# 통계 페이지
@app.route('/stats')
def stats():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT category, COUNT(*) as count FROM troubleshooting GROUP BY category", conn)
    conn.close()
    return render_template('stats.html', tables=[df.to_html(classes='data')], titles=df.columns.values)

# 데이터 다운로드
@app.route('/export')
def export():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM troubleshooting", conn)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    conn.close()
    return send_file(output, download_name="ulvac_troubleshooting.xlsx", as_attachment=True)

# 데이터 업로드
@app.route('/import', methods=['POST'])
def import_data():
    file = request.files['file']
    if file:
        df = pd.read_excel(file)
        conn = get_db_connection()
        df.to_sql('troubleshooting', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

# 좋아요 기능
@app.route('/feedback/<int:tid>', methods=['POST'])
def feedback(tid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE troubleshooting SET useful_count = useful_count + 1 WHERE id = ?', (tid,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# 코멘트 추가
@app.route('/comment', methods=['POST'])
def comment():
    trouble_id = request.form['trouble_id']
    commenter_name = request.form['commenter_name']
    comment_text = request.form['comment']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO comments (trouble_id, commenter_name, comment) VALUES (?, ?, ?)',
                (trouble_id, commenter_name, comment_text))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# 서버 시작
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)