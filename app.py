# app.py
import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------
# 初始化 Flask 與資料庫
# -------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'travel.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------
# 登入管理
# -------------------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# -------------------------------
# 資料表
# -------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Spot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), nullable=True)
    comment = db.Column(db.String(200), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# -------------------------------
# 使用者載入
# -------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------
# 路由
# -------------------------------
@app.route('/')
@login_required
def index():
    city = request.args.get('city')
    query = Spot.query.filter_by(user_id=current_user.id)
    if city:
        query = query.filter(Spot.city.contains(city))
    spots = query.all()
    return render_template('index.html', spots=spots, city=city)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('帳號或密碼錯誤')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('使用者名稱已存在')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('註冊成功，請登入')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# -------------------------------
# 新增景點
# -------------------------------
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_spot():
    if request.method == 'POST':
        name = request.form['name']
        city = request.form.get('city')
        comment = request.form.get('comment')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        spot = Spot(
            name=name, city=city, comment=comment,
            lat=float(lat) if lat else None,
            lng=float(lng) if lng else None,
            user_id=current_user.id
        )
        db.session.add(spot)
        db.session.commit()
        flash('新增成功')
        return redirect(url_for('index'))
    return render_template('add_edit_spot.html', spot=None)

# -------------------------------
# 編輯景點
# -------------------------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_spot(id):
    spot = Spot.query.get_or_404(id)
    if spot.user_id != current_user.id:
        flash('沒有權限編輯此景點')
        return redirect(url_for('index'))
    if request.method == 'POST':
        spot.name = request.form['name']
        spot.city = request.form.get('city')
        spot.comment = request.form.get('comment')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        spot.lat = float(lat) if lat else None
        spot.lng = float(lng) if lng else None
        db.session.commit()
        flash('更新成功')
        return redirect(url_for('index'))
    return render_template('add_edit_spot.html', spot=spot)

# -------------------------------
# 刪除景點
# -------------------------------
@app.route('/delete/<int:id>')
@login_required
def delete_spot(id):
    spot = Spot.query.get_or_404(id)
    if spot.user_id != current_user.id:
        flash('沒有權限刪除此景點')
        return redirect(url_for('index'))
    db.session.delete(spot)
    db.session.commit()
    flash('刪除成功')
    return redirect(url_for('index'))

# -------------------------------
# 地圖檢視
# -------------------------------
@app.route('/map')
@login_required
def map_view():
    spots = Spot.query.filter_by(user_id=current_user.id).all()
    return render_template('map.html', spots=spots)

# -------------------------------
# 初始化資料庫
# -------------------------------
with app.app_context():
    db.create_all()

# -------------------------------
# 本地測試用
# -------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
