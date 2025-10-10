# app.py (part 1) - imports and config
import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')  # change in production
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'edutrack.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
# app.py (part 2) - models
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role')

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_no = db.Column(db.String(50))
    name = db.Column(db.String(120))
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'))
    dob = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10))
    class_rel = db.relationship('Class', backref='students')

    def to_dict(self):
        return {
            'id': self.id,
            'admission_no': self.admission_no,
            'name': self.name,
            'class_id': self.class_id,
            'dob': self.dob.strftime("%d %b %Y") if self.dob else None,
            'gender': self.gender,
            'class_name': self.class_rel.name if self.class_rel else None,
        }
# app.py (part 3) - login loader & seed command
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.cli.command('initdata')
def initdata():
    """
    Create DB tables and seed roles + an admin user.
    Run in PowerShell: flask --app app.py initdata
    """
    db.create_all()
    if not Role.query.first():
        for r in ['Admin', 'Teacher', 'Student', 'Parent']:
            db.session.add(Role(name=r))
        db.session.commit()
    if not User.query.filter_by(email='admin@example.com').first():
        admin_role = Role.query.filter_by(name='Admin').first()
        u = User(
            name='Admin User',
            email='admin@example.com',
            password_hash=generate_password_hash('password123'),
            role=admin_role
        )
        db.session.add(u)
        db.session.commit()
    print('Initialized DB and added admin@example.com / password123')
# app.py (part 4) - auth and main pages
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, pw):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_students = Student.query.count()
    total_classes = Class.query.count()
    return render_template('dashboard.html', total_students=total_students, total_classes=total_classes)
# app.py (part 5) - students page and API
@app.route('/students')
@login_required
def students_page():
    return render_template('students.html')

@app.route('/api/students', methods=['GET','POST'])
@login_required
def api_students():
    if request.method == 'GET':
        students = Student.query.all()
        return jsonify([s.to_dict() for s in students])
    data = request.json
    dob_value = data.get('dob')
    dob_parsed = None
    if dob_value:
       try:
           dob_parsed = datetime.strptime(dob_value, "%Y-%m-%d").date()
       except ValueError:
            dob_parsed = None #fallback if format is wrong

    s = Student(
        admission_no = data.get('admission_no'),
        name = data.get('name'),
        class_id = data.get('class_id'),
        dob = dob_parsed,
        gender = data.get('gender')
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201
# app.py (new) - classes page
@app.route('/classes')
@login_required
def classes_page():
    return render_template('classes.html')

# app.py (new) - classes API
@app.route('/api/classes', methods=['GET', 'POST'])

def api_classes():
    if request.method == 'GET':
        classes = Class.query.all()
        return jsonify([{"id": c.id, "name": c.name} for c in classes])
    
    data = request.json
    c = Class(name=data.get('name'))
    db.session.add(c)
    db.session.commit()
    return jsonify({"id": c.id, "name": c.name}), 201

# app.py (part 6) - run
if __name__ == '__main__':
    app.run(debug=True)
