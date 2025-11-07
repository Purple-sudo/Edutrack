# app.py (part 1) - imports and config
import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')  # change in production
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'edutrack.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
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
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_no = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    subject_specialization = db.Column(db.String(100))

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_no': self.teacher_no,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'gender': self.gender,
            'subject_specialization': self.subject_specialization
        }

# Association table for many-to-many relationship between teachers and subjects
teacher_subject = db.Table('teacher_subject',
    db.Column('teacher_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subject.id'), primary_key=True)
)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Many-to-many relationship with teachers
    teachers = db.relationship('User', secondary=teacher_subject, backref=db.backref('subjects', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            'teacher_count': len(self.teachers) if self.teachers else 0
        }

# app.py (part 3) - login loader & seed command
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.cli.command('initdata')
def initdata():
    """
    Create DB tables and seed roles + sample users, classes, and data.
    Run in PowerShell: flask --app app.py initdata
    """
    from datetime import date
    
    db.create_all()
    
    # Create roles if they don't exist
    if not Role.query.first():
        roles = ['Admin', 'Teacher', 'Student', 'Parent']
        for role_name in roles:
            db.session.add(Role(name=role_name))
        db.session.commit()
        print('[OK] Created roles: Admin, Teacher, Student, Parent')
    
    # Get role objects
    admin_role = Role.query.filter_by(name='Admin').first()
    teacher_role = Role.query.filter_by(name='Teacher').first()
    student_role = Role.query.filter_by(name='Student').first()
    parent_role = Role.query.filter_by(name='Parent').first()
    
    # Create sample admin users
    admin_users = [
        {'name': 'Admin User', 'email': 'admin@example.com', 'password': 'password123'},
        {'name': 'John Administrator', 'email': 'john.admin@edutrack.com', 'password': 'admin2024'},
        {'name': 'Sarah Principal', 'email': 'principal@edutrack.com', 'password': 'principal123'}
    ]
    
    for admin_data in admin_users:
        if not User.query.filter_by(email=admin_data['email']).first():
            user = User(
                name=admin_data['name'],
                email=admin_data['email'],
                password_hash=generate_password_hash(admin_data['password']),
            role=admin_role
        )
            db.session.add(user)
    
    # Create sample teacher users
    teacher_users = [
        {'name': 'Michael Johnson', 'email': 'michael.johnson@edutrack.com', 'password': 'teacher123'},
        {'name': 'Emily Davis', 'email': 'emily.davis@edutrack.com', 'password': 'teacher123'},
        {'name': 'David Wilson', 'email': 'david.wilson@edutrack.com', 'password': 'teacher123'},
        {'name': 'Lisa Anderson', 'email': 'lisa.anderson@edutrack.com', 'password': 'teacher123'},
        {'name': 'Robert Brown', 'email': 'robert.brown@edutrack.com', 'password': 'teacher123'}
    ]
    
    for teacher_data in teacher_users:
        if not User.query.filter_by(email=teacher_data['email']).first():
            user = User(
                name=teacher_data['name'],
                email=teacher_data['email'],
                password_hash=generate_password_hash(teacher_data['password']),
                role=teacher_role
            )
            db.session.add(user)
    
    # Create sample student users
    student_users = [
        {'name': 'Alice Smith', 'email': 'alice.smith@student.edu', 'password': 'student123'},
        {'name': 'Bob Johnson', 'email': 'bob.johnson@student.edu', 'password': 'student123'},
        {'name': 'Carol Williams', 'email': 'carol.williams@student.edu', 'password': 'student123'},
        {'name': 'Daniel Brown', 'email': 'daniel.brown@student.edu', 'password': 'student123'},
        {'name': 'Eva Garcia', 'email': 'eva.garcia@student.edu', 'password': 'student123'}
    ]
    
    for student_data in student_users:
        if not User.query.filter_by(email=student_data['email']).first():
            user = User(
                name=student_data['name'],
                email=student_data['email'],
                password_hash=generate_password_hash(student_data['password']),
                role=student_role
            )
            db.session.add(user)
    
    # Create sample parent users
    parent_users = [
        {'name': 'Mary Smith', 'email': 'mary.smith@parent.com', 'password': 'parent123'},
        {'name': 'James Johnson', 'email': 'james.johnson@parent.com', 'password': 'parent123'},
        {'name': 'Patricia Williams', 'email': 'patricia.williams@parent.com', 'password': 'parent123'},
        {'name': 'Michael Brown', 'email': 'michael.brown@parent.com', 'password': 'parent123'},
        {'name': 'Linda Garcia', 'email': 'linda.garcia@parent.com', 'password': 'parent123'}
    ]
    
    for parent_data in parent_users:
        if not User.query.filter_by(email=parent_data['email']).first():
            user = User(
                name=parent_data['name'],
                email=parent_data['email'],
                password_hash=generate_password_hash(parent_data['password']),
                role=parent_role
            )
            db.session.add(user)
    
    db.session.commit()
    print('[OK] Created sample users for all roles')
    
    # Create sample classes
    if not Class.query.first():
        teacher_users_db = User.query.join(Role).filter(Role.name == 'Teacher').all()
        sample_classes = [
            {'name': 'Grade 1A', 'teacher_id': teacher_users_db[0].id if teacher_users_db else None},
            {'name': 'Grade 1B', 'teacher_id': teacher_users_db[1].id if len(teacher_users_db) > 1 else None},
            {'name': 'Grade 2A', 'teacher_id': teacher_users_db[2].id if len(teacher_users_db) > 2 else None},
            {'name': 'Grade 3A', 'teacher_id': teacher_users_db[3].id if len(teacher_users_db) > 3 else None},
            {'name': 'Grade 4A', 'teacher_id': teacher_users_db[4].id if len(teacher_users_db) > 4 else None},
        ]
        
        for class_data in sample_classes:
            class_obj = Class(name=class_data['name'], teacher_id=class_data['teacher_id'])
            db.session.add(class_obj)
        
        db.session.commit()
        print('[OK] Created sample classes')
    
    # Create sample teacher records in Teacher table
    if not Teacher.query.first():
        sample_teachers = [
            {'teacher_no': 'T001', 'name': 'Michael Johnson', 'email': 'michael.johnson@edutrack.com', 
             'phone': '555-0101', 'gender': 'Male', 'subject_specialization': 'Mathematics'},
            {'teacher_no': 'T002', 'name': 'Emily Davis', 'email': 'emily.davis@edutrack.com', 
             'phone': '555-0102', 'gender': 'Female', 'subject_specialization': 'English Literature'},
            {'teacher_no': 'T003', 'name': 'David Wilson', 'email': 'david.wilson@edutrack.com', 
             'phone': '555-0103', 'gender': 'Male', 'subject_specialization': 'Science'},
            {'teacher_no': 'T004', 'name': 'Lisa Anderson', 'email': 'lisa.anderson@edutrack.com', 
             'phone': '555-0104', 'gender': 'Female', 'subject_specialization': 'History'},
            {'teacher_no': 'T005', 'name': 'Robert Brown', 'email': 'robert.brown@edutrack.com', 
             'phone': '555-0105', 'gender': 'Male', 'subject_specialization': 'Physical Education'},
        ]
        
        for teacher_data in sample_teachers:
            teacher = Teacher(**teacher_data)
            db.session.add(teacher)
        
        db.session.commit()
        print('[OK] Created sample teacher records')
    
    # Create sample students
    if not Student.query.first():
        classes = Class.query.all()
        sample_students = [
            {'admission_no': 'S001', 'name': 'Alice Smith', 'class_id': classes[0].id if classes else None, 
             'dob': date(2016, 3, 15), 'gender': 'Female'},
            {'admission_no': 'S002', 'name': 'Bob Johnson', 'class_id': classes[0].id if classes else None, 
             'dob': date(2016, 7, 22), 'gender': 'Male'},
            {'admission_no': 'S003', 'name': 'Carol Williams', 'class_id': classes[1].id if len(classes) > 1 else None, 
             'dob': date(2016, 11, 8), 'gender': 'Female'},
            {'admission_no': 'S004', 'name': 'Daniel Brown', 'class_id': classes[1].id if len(classes) > 1 else None, 
             'dob': date(2016, 5, 30), 'gender': 'Male'},
            {'admission_no': 'S005', 'name': 'Eva Garcia', 'class_id': classes[2].id if len(classes) > 2 else None, 
             'dob': date(2015, 9, 12), 'gender': 'Female'},
            {'admission_no': 'S006', 'name': 'Frank Miller', 'class_id': classes[2].id if len(classes) > 2 else None, 
             'dob': date(2015, 12, 3), 'gender': 'Male'},
            {'admission_no': 'S007', 'name': 'Grace Wilson', 'class_id': classes[3].id if len(classes) > 3 else None, 
             'dob': date(2014, 4, 18), 'gender': 'Female'},
            {'admission_no': 'S008', 'name': 'Henry Davis', 'class_id': classes[3].id if len(classes) > 3 else None, 
             'dob': date(2014, 8, 25), 'gender': 'Male'},
            {'admission_no': 'S009', 'name': 'Ivy Anderson', 'class_id': classes[4].id if len(classes) > 4 else None, 
             'dob': date(2013, 6, 7), 'gender': 'Female'},
            {'admission_no': 'S010', 'name': 'Jack Thompson', 'class_id': classes[4].id if len(classes) > 4 else None, 
             'dob': date(2013, 10, 14), 'gender': 'Male'},
        ]
        
        for student_data in sample_students:
            student = Student(**student_data)
            db.session.add(student)
        
        db.session.commit()
        print('[OK] Created sample student records')
    
    # Create sample subjects
    if not Subject.query.first():
        sample_subjects = [
            {'name': 'English', 'code': 'ENG', 'description': 'English language and literature'},
            {'name': 'Kiswahili', 'code': 'KIS', 'description': 'Kiswahili language and literature'},
            {'name': 'Mathematics', 'code': 'MATH', 'description': 'Mathematics and algebra'},
            {'name': 'Biology', 'code': 'BIO', 'description': 'Biological sciences'},
            {'name': 'Chemistry', 'code': 'CHEM', 'description': 'Chemical sciences'},
            {'name': 'Physics', 'code': 'PHY', 'description': 'Physical sciences'},
            {'name': 'Geography', 'code': 'GEO', 'description': 'Geography and environmental studies'},
            {'name': 'History', 'code': 'HIS', 'description': 'History and social studies'},
            {'name': 'Christian Religious Education', 'code': 'CRE', 'description': 'Christian Religious Education'},
            {'name': 'Islamic Religious Education', 'code': 'IRE', 'description': 'Islamic Religious Education'},
            {'name': 'Hindu Religious Education', 'code': 'HRE', 'description': 'Hindu Religious Education'},
            {'name': 'Agriculture', 'code': 'AGR', 'description': 'Agricultural studies'},
            {'name': 'Business Studies', 'code': 'BUS', 'description': 'Business and commerce studies'},
            {'name': 'Home Science', 'code': 'HSC', 'description': 'Home science and domestic studies'},
        ]
        
        teacher_users_db = User.query.join(Role).filter(Role.name == 'Teacher').all()
        
        for idx, subject_data in enumerate(sample_subjects):
            subject = Subject(
                name=subject_data['name'],
                code=subject_data['code'],
                description=subject_data['description'],
                created_by=teacher_users_db[0].id if teacher_users_db else None
            )
            db.session.add(subject)
            db.session.flush()  # Get the subject ID
            
            # Distribute subjects across teachers
            if teacher_users_db:
                # Assign subjects to different teachers based on index
                teacher_idx = idx % len(teacher_users_db)
                teacher_users_db[teacher_idx].subjects.append(subject)
        
        db.session.commit()
        print('[OK] Created subjects and assigned to teachers')
    
    print('\n[SUCCESS] Database seeding completed successfully!')
    print('\nSample login credentials:')
    print('Admin: admin@example.com / password123')
    print('Teacher: michael.johnson@edutrack.com / teacher123')
    print('Student: alice.smith@student.edu / student123')
    print('Parent: mary.smith@parent.com / parent123')

@app.cli.command('add-subjects')
def add_subjects():
    """
    Add subjects to the database (will skip if already exist).
    Run in PowerShell: flask --app app.py add-subjects
    """
    sample_subjects = [
        {'name': 'English', 'code': 'ENG', 'description': 'English language and literature'},
        {'name': 'Kiswahili', 'code': 'KIS', 'description': 'Kiswahili language and literature'},
        {'name': 'Mathematics', 'code': 'MATH', 'description': 'Mathematics and algebra'},
        {'name': 'Biology', 'code': 'BIO', 'description': 'Biological sciences'},
        {'name': 'Chemistry', 'code': 'CHEM', 'description': 'Chemical sciences'},
        {'name': 'Physics', 'code': 'PHY', 'description': 'Physical sciences'},
        {'name': 'Geography', 'code': 'GEO', 'description': 'Geography and environmental studies'},
        {'name': 'History', 'code': 'HIS', 'description': 'History and social studies'},
        {'name': 'Christian Religious Education', 'code': 'CRE', 'description': 'Christian Religious Education'},
        {'name': 'Islamic Religious Education', 'code': 'IRE', 'description': 'Islamic Religious Education'},
        {'name': 'Hindu Religious Education', 'code': 'HRE', 'description': 'Hindu Religious Education'},
        {'name': 'Agriculture', 'code': 'AGR', 'description': 'Agricultural studies'},
        {'name': 'Business Studies', 'code': 'BUS', 'description': 'Business and commerce studies'},
        {'name': 'Home Science', 'code': 'HSC', 'description': 'Home science and domestic studies'},
    ]
    
    teacher_users_db = User.query.join(Role).filter(Role.name == 'Teacher').all()
    added_count = 0
    
    for idx, subject_data in enumerate(sample_subjects):
        # Check if subject with this name or code already exists
        existing = Subject.query.filter(
            (Subject.name == subject_data['name']) | (Subject.code == subject_data['code'])
        ).first()
        
        if not existing:
            subject = Subject(
                name=subject_data['name'],
                code=subject_data['code'],
                description=subject_data['description'],
                created_by=teacher_users_db[0].id if teacher_users_db else None
            )
            db.session.add(subject)
            db.session.flush()  # Get the subject ID
            
            # Distribute subjects across teachers
            if teacher_users_db:
                teacher_idx = idx % len(teacher_users_db)
                teacher_users_db[teacher_idx].subjects.append(subject)
            
            added_count += 1
        else:
            print(f'Skipped {subject_data["name"]} - already exists')
    
    db.session.commit()
    print(f'[OK] Added {added_count} new subjects')
    if added_count > 0:
        print('[OK] Subjects assigned to teachers')
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
    total_teachers = User.query.join(Role).filter(Role.name == 'Teacher').count()
    return render_template('dashboard.html', 
                         total_students=total_students, 
                         total_classes=total_classes,
                         total_teachers=total_teachers,
                         user_role=current_user.role.name)
# app.py (part 5) - students page and API

@app.route('/students')
@login_required
def students_page():
    # Check if user has permission to access students
    if current_user.role.name not in ['Admin', 'Teacher']:
        flash("Access denied: Admins and Teachers only.")
        return redirect(url_for('dashboard'))
    
    return render_template('students.html')

@app.route('/api/students', methods=['GET','POST'])
@login_required
def api_students():
    # Check if user has permission to access students
    if current_user.role.name not in ['Admin', 'Teacher']:
        return jsonify({'error': 'Access denied'}), 403
    
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

@app.route('/api/students/<int:id>', methods=['GET'])
@login_required
def get_student(id):
    # Check if user has permission to access students
    if current_user.role.name not in ['Admin', 'Teacher']:
        return jsonify({'error': 'Access denied'}), 403
    
    student = Student.query.get_or_404(id)
    return jsonify(student.to_dict())

@app.route('/api/students/<int:id>', methods=['PUT'])
@login_required
def update_student(id):
    # Check if user has permission to access students
    if current_user.role.name not in ['Admin', 'Teacher']:
        return jsonify({'error': 'Access denied'}), 403
    
    student = Student.query.get_or_404(id)
    data = request.json

    student.admission_no = data.get('admission_no', student.admission_no)
    student.name = data.get('name', student.name)
    student.class_id = data.get('class_id', student.class_id)
    student.gender = data.get('gender', student.gender)

    dob_value = data.get('dob')
    if dob_value:
        try:
            student.dob = datetime.strptime(dob_value, "%Y-%m-%d").date()
        except ValueError:
            pass

    db.session.commit()
    return jsonify(student.to_dict())

@app.route('/api/students/<int:id>', methods=['DELETE'])
@login_required
def delete_student(id):
    # Check if user has permission to access students
    if current_user.role.name not in ['Admin', 'Teacher']:
        return jsonify({'error': 'Access denied'}), 403
    
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Deleted successfully'}), 200

# ==============================
#   ADMIN: Teacher Management
# ==============================
@app.route('/teachers')
@login_required
def teachers():
    if current_user.role.name != 'Admin':
        flash("Access denied: Admins only.")
        return redirect(url_for('dashboard'))
    
    teachers = User.query.join(Role).filter(Role.name == 'Teacher').all()
    return render_template('teachers.html', teachers=teachers)


@app.route('/teacher/add', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if current_user.role.name != 'Admin':
        flash("Access denied: Admins only.")
        return redirect(url_for('teachers'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        teacher_role = Role.query.filter_by(name='Teacher').first()

        new_teacher = User(name=name, email=email, password_hash=password, role=teacher_role)
        db.session.add(new_teacher)
        db.session.commit()
        flash('Teacher added successfully!')
        return redirect(url_for('teachers'))

    return render_template('add_teacher.html')


@app.route('/teacher/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_teacher(id):
    if current_user.role.name != 'Admin':
        flash("Access denied: Admins only.")
        return redirect(url_for('teachers'))

    teacher = User.query.get_or_404(id)

    if request.method == 'POST':
        teacher.name = request.form['name']
        teacher.email = request.form['email']
        db.session.commit()
        flash('Teacher updated successfully!')
        return redirect(url_for('teachers'))

    return render_template('edit_teacher.html', teacher=teacher)


@app.route('/teacher/delete/<int:id>', methods=['POST'])
@login_required
def delete_teacher(id):
    if current_user.role.name != 'Admin':
        flash("Access denied: Admins only.")
        return redirect(url_for('teachers'))

    teacher = User.query.get_or_404(id)
    db.session.delete(teacher)
    db.session.commit()
    flash('Teacher deleted successfully!')
    return redirect(url_for('teachers'))

# app.py (new) - classes page
@app.route('/classes')
@login_required
def classes_page():
    # Check if user has permission to access classes
    if current_user.role.name not in ['Admin', 'Teacher']:
        flash("Access denied: Admins and Teachers only.")
        return redirect(url_for('dashboard'))
    
    return render_template('classes.html')

# app.py (new) - classes API
@app.route('/api/classes', methods=['GET', 'POST'])
@login_required
def api_classes():
    # Check if user has permission to access classes
    if current_user.role.name not in ['Admin', 'Teacher']:
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'GET':
        classes = Class.query.all()
        return jsonify([{"id": c.id, "name": c.name} for c in classes])
    
    data = request.json
    c = Class(name=data.get('name'))
    db.session.add(c)
    db.session.commit()
    return jsonify({"id": c.id, "name": c.name}), 201

# ==============================
#   TEACHER: Subject Management
# ==============================
@app.route('/subjects')
@login_required
def subjects():
    # Only teachers and admins can access subjects
    if current_user.role.name not in ['Admin', 'Teacher']:
        flash("Access denied: Teachers and Admins only.")
        return redirect(url_for('dashboard'))
    
    subjects = Subject.query.all()
    # Get subjects assigned to current teacher if they're a teacher
    if current_user.role.name == 'Teacher':
        my_subjects = current_user.subjects.all()
    else:
        my_subjects = []
    
    return render_template('subjects.html', subjects=subjects, my_subjects=my_subjects)

@app.route('/subject/add', methods=['GET', 'POST'])
@login_required
def add_subject():
    # Only teachers and admins can add subjects
    if current_user.role.name not in ['Admin', 'Teacher']:
        flash("Access denied: Teachers and Admins only.")
        return redirect(url_for('subjects'))

    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description', '')
        
        # Check if subject with same name or code already exists
        if Subject.query.filter_by(name=name).first():
            flash('Subject with this name already exists!', 'danger')
            return render_template('add_subject.html')
        
        if Subject.query.filter_by(code=code).first():
            flash('Subject with this code already exists!', 'danger')
            return render_template('add_subject.html')
        
        subject = Subject(
            name=name,
            code=code,
            description=description,
            created_by=current_user.id
        )
        db.session.add(subject)
        db.session.commit()
        
        # Automatically assign the subject to the teacher who created it
        if current_user.role.name == 'Teacher':
            current_user.subjects.append(subject)
            db.session.commit()
        
        flash('Subject added successfully!', 'success')
        return redirect(url_for('subjects'))

    return render_template('add_subject.html')

@app.route('/subject/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_subject(id):
    # Only teachers and admins can edit subjects
    if current_user.role.name not in ['Admin', 'Teacher']:
        flash("Access denied: Teachers and Admins only.")
        return redirect(url_for('subjects'))

    subject = Subject.query.get_or_404(id)
    
    # Teachers can only edit subjects they created or are assigned to
    if current_user.role.name == 'Teacher':
        if subject.created_by != current_user.id and subject not in current_user.subjects.all():
            flash("Access denied: You can only edit your own subjects.", 'danger')
            return redirect(url_for('subjects'))

    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description', '')
        
        # Check if another subject with same name or code exists
        existing_name = Subject.query.filter_by(name=name).first()
        if existing_name and existing_name.id != id:
            flash('Subject with this name already exists!', 'danger')
            return render_template('edit_subject.html', subject=subject)
        
        existing_code = Subject.query.filter_by(code=code).first()
        if existing_code and existing_code.id != id:
            flash('Subject with this code already exists!', 'danger')
            return render_template('edit_subject.html', subject=subject)
        
        subject.name = name
        subject.code = code
        subject.description = description
        db.session.commit()
        flash('Subject updated successfully!', 'success')
        return redirect(url_for('subjects'))

    return render_template('edit_subject.html', subject=subject)

@app.route('/subject/delete/<int:id>', methods=['POST'])
@login_required
def delete_subject(id):
    # Only teachers and admins can delete subjects
    if current_user.role.name not in ['Admin', 'Teacher']:
        flash("Access denied: Teachers and Admins only.")
        return redirect(url_for('subjects'))

    subject = Subject.query.get_or_404(id)
    
    # Teachers can only delete subjects they created
    if current_user.role.name == 'Teacher':
        if subject.created_by != current_user.id:
            flash("Access denied: You can only delete your own subjects.", 'danger')
            return redirect(url_for('subjects'))
    
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('subjects'))

@app.route('/subject/<int:id>/assign', methods=['POST'])
@login_required
def assign_subject(id):
    # Only teachers can assign subjects to themselves
    if current_user.role.name != 'Teacher':
        flash("Access denied: Teachers only.")
        return redirect(url_for('subjects'))
    
    subject = Subject.query.get_or_404(id)
    
    if subject in current_user.subjects.all():
        flash('You are already assigned to this subject!', 'info')
    else:
        current_user.subjects.append(subject)
        db.session.commit()
        flash(f'Successfully assigned to {subject.name}!', 'success')
    
    return redirect(url_for('subjects'))

@app.route('/subject/<int:id>/unassign', methods=['POST'])
@login_required
def unassign_subject(id):
    # Only teachers can unassign subjects from themselves
    if current_user.role.name != 'Teacher':
        flash("Access denied: Teachers only.")
        return redirect(url_for('subjects'))
    
    subject = Subject.query.get_or_404(id)
    
    if subject not in current_user.subjects.all():
        flash('You are not assigned to this subject!', 'info')
    else:
        current_user.subjects.remove(subject)
        db.session.commit()
        flash(f'Successfully unassigned from {subject.name}!', 'success')
    
    return redirect(url_for('subjects'))

# app.py (part 6) - run
if __name__ == '__main__':
    app.run(debug=True)
