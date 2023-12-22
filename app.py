from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://dmitry:123d@localhost:5432/rgz'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/photos'
db = SQLAlchemy(app)
upload_folder = app.config['UPLOAD_FOLDER']
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    search_gender = db.Column(db.String(10), nullable=False)
    about_me = db.Column(db.Text)
    photo = db.Column(db.String(50))
    password_hash = db.Column(db.String(128), nullable=False)
    hidden = db.Column(db.Boolean, default=False)
    print("Profile updated successfully!")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('profile', user_id=user.id))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = []

    visibleUser = "Anon"
    visibleUser = session.get("username")

    if request.method == "GET":
        return render_template("register.html", errors=errors, username=visibleUser)

    username = request.form.get("username")
    password = request.form.get("password")
    age = request.form.get("age")
    gender = request.form.get("gender")
    search_gender = request.form.get("search_gender")
    about_me = request.form.get("about_me")
    photo = request.form.get("photo")

    if 'photo' in request.files:
        photo = request.files['photo']
        if photo.filename != '' and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            flash("Ошибка при загрузке фото. Допустимые форматы: png, jpg, jpeg, gif", "error")
            return render_template("register.html", errors=errors, username=visibleUser)


    if not (username or password):
        errors.append("Пожалуйста, заполните все поля")
        print(errors)
        return render_template("register.html", errors=errors, username=visibleUser)

    hashPassword = generate_password_hash(password)

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        errors.append("Пользователь с данным именем уже существует")
        flash("Ошибка при регистрации: Пользователь с данным именем уже существует", "error")
        return render_template("register.html", errors=errors, username=visibleUser)


    new_user = User (
        username=username,
        age=age,
        gender=gender,
        search_gender=search_gender,
        about_me=about_me,
        photo=photo,
        password_hash=hashPassword
    )
    db.session.add(new_user)
    db.session.commit()

    return redirect("/login")

@app.route('/profile/<int:user_id>')
def profile(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        flash('Недостаточно прав для просмотра данной страницы', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    return render_template('profile.html', user=user)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if request.method == 'POST':
        # Извлечение значения user_id из формы
        user_id_from_form = request.form['user_id']

        # Проверка соответствия user_id в сессии и в форме
        if user_id_from_form != str(user.id):
            return "Несоответствие идентификаторов пользователя."

        user.username = request.form['username']
        user.age = int(request.form['age'])
        user.gender = request.form['gender']
        user.search_gender = request.form['search_gender']
        user.about_me = request.form['about_me']
        user.photo = request.form['photo']
        user.hidden = 'hidden' in request.form

        db.session.commit()

        return redirect(url_for('profile', user_id=user.id))

    return render_template('edit_profile.html', user=user)

@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if user is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        db.session.delete(user)
        db.session.commit()
        session.pop('user_id', None)

        return redirect(url_for('login'))

    return render_template('delete_account.html', user=user)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if request.method == 'POST':
        search_gender = user.search_gender
        # Фильтрация результатов поиска по полу для поиска и видимости профиля
        results = User.query.filter_by(search_gender=search_gender, hidden=False).all()

        return render_template('search_results.html', results=results, user=user)

    return render_template('search.html')

@app.route('/search_results', methods=['POST'])
def search_results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')

        search_gender = user.search_gender

        # Фильтрация результатов поиска в соответствии с вашими условиями
        search_results = User.query.filter(
            User.id != user.id,
            User.search_gender == user.gender,
            User.gender == user.search_gender,
            User.hidden == True
        )

        if name:
            search_results = search_results.filter(User.username.ilike(f"%{name}%"))

        if age:
            search_results = search_results.filter(User.age == age)

        search_results = search_results.all()

        return render_template('search_results.html', results=search_results, user=user)

    return jsonify({'error': 'Invalid request'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)