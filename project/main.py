from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- НАСТРОЙКИ ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super-secret-key-for-flash-messages' # Нужен для вывода сообщений об ошибках

# Настройка JWT токена (Пункт 08)
app.config["JWT_SECRET_KEY"] = "super-secret-jwt-key" 
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15) # Пункт 09: токен живет 15 минут

db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# --- МОДЕЛИ БАЗЫ ДАННЫХ ---
# Существующая модель
class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    subtitle = db.Column(db.String(200), nullable=True)

# Пункт 04: Новая модель Users
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) # Храним хэш пароля, а не сам пароль!

# --- 3. ДАННЫЕ ДЛЯ СТРАНИЦ ---
menu = [
    {"name": "Главная", "url": "/"},
    {"name": "Обо мне", "url": "/about"},
    {"name": "Дневник", "url": "/notes"},
    {"name": "Вход", "url": "/login"},
    {"name": "Регистрация", "url": "/register"}
]

themes = [
    {"id": 1, "name": "Основы HTML"},
    {"id": 2, "name": "Стилизация CSS"},
    {"id": 3, "name": "Шаблонизатор Jinja2"}
]

# --- МАРШРУТЫ ---
@app.route('/')
def index():
    return render_template('index.html', page_title="Главная", menu=menu)

@app.route('/about')
def about():
    return render_template('about.html', page_title="Обо мне", menu=menu)

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    if request.method == 'POST':
        title = request.form.get('title')
        text = request.form.get('text')
        if title and text:
            new_note = Notes(title=title, text=text)
            db.session.add(new_note)
            db.session.commit()
        return redirect(url_for('notes'))
    all_notes = Notes.query.all()
    return render_template('notes.html', page_title="Дневник", menu=menu, notes=all_notes, themes=themes)

# --- ПУНКТ 01: Страница /home ---
@app.route('/home')
def home():
    return render_template('home.html', page_title="Добро пожаловать")

# --- ПУНКТ 02 и 06: Регистрация ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Проверка, есть ли уже такой пользователь
        user_exists = Users.query.filter_by(username=username).first()
        if user_exists:
            flash('Пользователь с таким логином уже существует!', 'error')
            return redirect(url_for('register'))

        # Хэшируем пароль для безопасности
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Добавляем в БД
        new_user = Users(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', page_title="Регистрация")

# --- ПУНКТ 03, 07 и 08: Логин и генерация токена ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = Users.query.filter_by(username=username).first()

        # Проверяем, существует ли юзер и совпадает ли пароль
        if user and check_password_hash(user.password, password):
            # Пункт 08: Генерируем токен
            access_token = create_access_token(identity=username)
            flash(f'Успешный вход! Ваш токен: {access_token[:15]}...', 'success')
            # В реальном проекте тут нужно сохранить токен в cookie или localStorage
            # и перенаправить на защищенную страницу. Мы просто редиректим на главную.
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль!', 'error')

    return render_template('login.html', page_title="Вход")

# --- ПУНКТ 09: Защищенная страница (проверка токена) ---
@app.route('/protected')
@jwt_required() # Этот декоратор сам проверяет токен и его срок действия!
def protected():
    current_user = get_jwt_identity()
    return f"Привет, {current_user}! Это защищенная страница. Токен действителен."

# --- СОЗДАНИЕ ТАБЛИЦ (Страховка) ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)