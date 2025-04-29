from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///troubles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Trouble(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trouble_date = db.Column(db.String(20), nullable=False)
    device_code = db.Column(db.String(100), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    trouble_text = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    tags = db.Column(db.String(200), nullable=True)
    image = db.Column(db.String(100), nullable=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        trouble_date = request.form['trouble_date']
        device_code = request.form['device_code']
        device_name = request.form['device_name']
        user_name = request.form['user_name']
        trouble_text = request.form['trouble_text']
        solution = request.form['solution']
        category = request.form['category']
        tags = request.form['tags']
        image = request.form['clipboard_image_data']  # 이미지 데이터는 클립보드로 처리

        new_trouble = Trouble(trouble_date=trouble_date, device_code=device_code,
                              device_name=device_name, user_name=user_name, 
                              trouble_text=trouble_text, solution=solution, 
                              category=category, tags=tags, image=image)

        db.session.add(new_trouble)
        db.session.commit()

        return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form['search_query']
    search_tags = request.form['search_tags']
    
    results = Trouble.query.filter(Trouble.trouble_text.like(f"%{search_query}%"), 
                                   Trouble.tags.like(f"%{search_tags}%")).all()

    return render_template('search_results.html', results=results)

@app.route('/stats_devices')
def stats_devices():
    try:
        # 트러블 통계 로직 추가
        # 예시로 모든 장치별로 통계 보기 (DB에서 장치별로 통계를 조회)
        device_stats = db.session.query(Trouble.device_name, db.func.count(Trouble.id).label('count')) \
                                 .group_by(Trouble.device_name).all()
        return render_template('stats_devices.html', device_stats=device_stats)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    db.create_all()  # 처음 실행 시 DB 테이블 생성
    app.run(debug=True)
