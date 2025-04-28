from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# DB 초기화
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'trouble.db')

def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS troubles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            device TEXT,
            device_name TEXT,
            reporter TEXT,
            symptom TEXT,
            solution TEXT,
            category TEXT,
            mobile_img TEXT,
            pc_img TEXT,
            hashtag TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_trouble():
    data = request.form
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO troubles (date, device, device_name, reporter, symptom, solution, category, mobile_img, pc_img, hashtag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('occur_date'),
        data.get('device_local'),
        data.get('device_name'),
        data.get('reporter_name'),
        data.get('trouble_content'),
        data.get('solution'),
        data.get('category'),
        data.get('mobile_img'),
        data.get('pc_img'),
        data.get('hashtag')
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/stats_devices')
def stats_devices():
    return render_template('stats_devices.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
