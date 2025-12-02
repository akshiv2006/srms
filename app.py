import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask import g
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "devkey")
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:akshiv@localhost:5432/srms")
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
		
db = SQLAlchemy(app)


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    courses = relationship("Course", backref="department")
    hods = relationship("HOD", backref="department")

class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # hashed
    role = db.Column(db.String(20), nullable=False)  # Student, Teacher, HOD, Admin

    student = relationship("Student", uselist=False, backref="user")
    teacher = relationship("Teacher", uselist=False, backref="user")
    hod = relationship("HOD", uselist=False, backref="user")
class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    roll_number = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    department = relationship("Department")
    results = relationship("Result", backref="student")

class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    department = relationship("Department")
    courses = relationship("Course", backref="teacher")

class HOD(db.Model):
    __tablename__ = "hods"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))

class Semester(db.Model):
    __tablename__ = "semesters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "SEM 1", "SEM 2", "2025-1"

class Result(db.Model):
    __tablename__ = "results"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    marks = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5), nullable=False)

    course = relationship("Course")
    semester = relationship("Semester")


@app.route("/")
def index():
    return render_template("index.html",current_user=g.user)

@app.before_request
def set_current_user():
    g.user=current_user

# Simple selection route that forwards to appropriate login/form
@app.route("/select/<role>", methods=["GET", "POST"])
def select_role(role):
    role = role.lower()
    if role not in ("student", "teacher", "hod"):
        flash("Invalid role", "danger")
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(user_name=username, password=password, role=role).first()
        if not user:
            flash("Invalid credentials", "danger")
            return redirect(request.url)

        # Redirect to role dashboards with user id in query (simple session-less demo)
        if role == "student":
            return redirect(url_for("student_dashboard", user_id=user.user_id))
        if role == "teacher":
            return redirect(url_for("teacher_dashboard", user_id=user.user_id))
        if role == "hod":
            return redirect(url_for("hod_dashboard", user_id=user.user_id))
    return render_template("login.html", role=role)




# --- Student dashboard ---
@app.route("/student/<int:user_id>")
def student_dashboard(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != "student":
        flash("Not a student user", "danger")
        return redirect(url_for("index"))
    student = user.student
    semesters = Semester.query.all()
    return render_template("student_dashboard.html", student=student, semesters=semesters)

@app.route("/student/<int:user_id>/view_result", methods=["POST"])
def student_view_result(user_id):
    semester_id = int(request.form["semester"])
    user = User.query.get_or_404(user_id)
    student = user.student
    results = Result.query.filter_by(student_id=student.id, semester_id=semester_id).all()
    semester = Semester.query.get(semester_id)
    return render_template("students_result.html", student=student, results=results, semester=semester)

# --- Teacher dashboard ---
@app.route("/teacher/<int:user_id>")
def teacher_dashboard(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != "teacher":
        flash("Not a teacher user", "danger")
        return redirect(url_for("index"))
    teacher = user.teacher
    courses = teacher.courses
    semesters = Semester.query.all()
    return render_template("teacher_dashboard.html", teacher=teacher, courses=courses, semesters=semesters)

@app.route("/teacher/<int:user_id>/course/<int:course_id>", methods=["GET", "POST"])
def teacher_course_update(user_id, course_id):
    user = User.query.get_or_404(user_id)
    if user.role != "teacher":
        flash("Not a teacher user", "danger")
        return redirect(url_for("index"))
    course = Course.query.get_or_404(course_id)
    semesters = Semester.query.all()

    if request.method == "POST":
        semester_id = int(request.form["semester"])
        roll = request.form["roll_number"]
        marks = float(request.form["marks"])
        # find student
        student = Student.query.filter_by(roll_number=roll).first()
        if not student:
            flash("Student roll not found", "danger")
            return redirect(request.url)
        # compute grade (simple mapping)
        grade = compute_grade(marks)
        # upsert result
        existing = Result.query.filter_by(student_id=student.id, course_id=course.id, semester_id=semester_id).first()
        if existing:
            existing.marks = marks
            existing.grade = grade
            db.session.commit()
            flash("Result updated", "success")
        else:
            r = Result(student_id=student.id, course_id=course.id, semester_id=semester_id, marks=marks, grade=grade)
            db.session.add(r)
            db.session.commit()
            flash("Result added", "success")
        return redirect(request.url)

    # show all results for this course
    results = Result.query.filter_by(course_id=course.id).all()
    return render_template("teacher_course.html", course=course, results=results, semesters=semesters)

# --- HOD dashboard ---
@app.route("/hod/<int:user_id>", methods=["GET","POST"])
def hod_dashboard(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != "hod":
        flash("Not a HOD user", "danger")
        return redirect(url_for("index"))
    hod = user.hod
    departments = Department.query.all()
    if request.method == "POST":
        dept_id = int(request.form["department"])
        sem_id = int(request.form["semester"])
        # find students in department and their results for that semester
        students = Student.query.filter_by(department_id=dept_id).all()
        # gather results
        dept_results = Result.query.join(Student).filter(Student.department_id==dept_id, Result.semester_id==sem_id).all()
        semester = Semester.query.get(sem_id)
        department = Department.query.get(dept_id)
        return render_template("hod_view_results.html", hod=hod, results=dept_results, semester=semester, department=department)
    semesters = Semester.query.all()
    return render_template("hod_dashboard.html", hod=hod, departments=departments, semesters=semesters)

# --- Utilities ---
def compute_grade(marks):
    if marks >= 90:
        return "A+"
    if marks >= 80:
        return "A"
    if marks >= 70:
        return "B+"
    if marks >= 60:
        return "B"
    if marks >= 50:
        return "C"
    return "F"

# --- CLI route to seed DB (for demo only) ---
@app.cli.command("initdb")
def initdb():
    db.drop_all()
    db.create_all()
    
    print("Seeding database...")

    # --- Departments ---
    depts = [
        Department(name='Computer Science'),
        Department(name='Electronics and Communication'),
        Department(name='Mechanical Engineering'),
        Department(name='Artificial Intelligence and Data Science'),
        Department(name='Electrical Engineering'),
        Department(name='Information Technology'),
        Department(name='Chemical Engineering'),
        Department(name='Biotechnology'),
        Department(name='Aerospace Engineering'),
        Department(name='Mathematics')
    ]
    db.session.add_all(depts)
    db.session.commit()
    print("Added 10 Departments")
    
    # --- Semesters ---
    sems = [
        Semester(name='Semester 1'),
        Semester(name='Semester 2'),
        Semester(name='Semester 3'),
        Semester(name='Semester 4'),
        Semester(name='Semester 5'),
        Semester(name='Semester 6'),
        Semester(name='Semester 7'),
        Semester(name='Semester 8'),
        Semester(name='Semester 9'),
        Semester(name='Semester 10')
        
    ]
    db.session.add_all(sems)
    db.session.commit()
    print("Added 8 Semesters")
    
    # We need to get the objects back to use their new IDs
    d1, d2, d3, d4, d5, d6, d7, d8, d9, d10 = depts
    s1, s2, s3, s4, s5, s6, s7, s8, s9, s10 = sems

    # --- Users & Teachers ---
    # Create User and Teacher, then link them
    u_t1 = User(user_name='alice.johnson', password='password', role='teacher')
    u_t2 = User(user_name='bob.smith', password='password', role='teacher')
    u_t3 = User(user_name='charlie.brown', password='password', role='teacher')
    u_t4 = User(user_name='david.lee', password='password', role='teacher')
    u_t5 = User(user_name='eva.williams', password='password', role='hod') # HOD
    u_t6 = User(user_name='frank.taylor', password='password', role='hod') # HOD
    u_t7 = User(user_name='grace.moore', password='password', role='teacher')
    u_t8 = User(user_name='henry.thomas', password='password', role='teacher')
    u_t9 = User(user_name='isabella.clark', password='password', role='teacher')
    u_t10 = User(user_name='jack.lewis', password='password', role='teacher')
    db.session.add_all([u_t1, u_t2, u_t3, u_t4, u_t5, u_t6, u_t7, u_t8, u_t9, u_t10])
    db.session.commit()

    teachers = [
        Teacher(user_id=u_t1.user_id, full_name='Alice Johnson', department_id=d1.id),
        Teacher(user_id=u_t2.user_id, full_name='Bob Smith', department_id=d2.id),
        Teacher(user_id=u_t3.user_id, full_name='Charlie Brown', department_id=d3.id),
        Teacher(user_id=u_t4.user_id, full_name='David Lee', department_id=d1.id),
        Teacher(user_id=u_t7.user_id, full_name='Grace Moore', department_id=d6.id),
        Teacher(user_id=u_t8.user_id, full_name='Henry Thomas', department_id=d7.id),
        Teacher(user_id=u_t9.user_id, full_name='Isabella Clark', department_id=d8.id),
        Teacher(user_id=u_t10.user_id, full_name='Jack Lewis', department_id=d9.id)
    ]
    db.session.add_all(teachers)
    
    # HODs (who are also Teachers in this setup, but your model has them separate)
    # We'll create HOD records linked to their User accounts
    hods = [
        HOD(user_id=u_t5.user_id, full_name='Eva Williams', department_id=d4.id),
        HOD(user_id=u_t6.user_id, full_name='Frank Taylor', department_id=d5.id)
    ]
    db.session.add_all(hods)
    db.session.commit()
    print("Added 10 Users (Teachers/HODs)")

    # Get teacher objects for linking to courses
    t1, t2, t3, t4, t7, t8, t9, t10 = teachers

     # --- Courses ---
    courses = [
        Course(code='C001', title='Database Systems', department_id=d1.id, teacher_id=t4.id),
        Course(code='C002', title='Digital Circuits', department_id=d2.id, teacher_id=t2.id),
        Course(code='C003', title='Thermodynamics', department_id=d3.id, teacher_id=t3.id),
        Course(code='C004', title='Machine Learning', department_id=d4.id, teacher_id=None), # Eva is a HOD
        Course(code='C005', title='Power Systems', department_id=d5.id, teacher_id=None), # Frank is a HOD
        Course(code='C006', title='Operating Systems', department_id=d6.id, teacher_id=t7.id),
        Course(code='C007', title='Chemical Process', department_id=d7.id, teacher_id=t8.id),
        Course(code='C008', title='Genetic Engineering', department_id=d8.id, teacher_id=t9.id),
        Course(code='C009', title='Aerodynamics', department_id=d9.id, teacher_id=t10.id),
        Course(code='C010', title='Linear Algebra', department_id=d10.id, teacher_id=t1.id)
    ]
    db.session.add_all(courses)
    db.session.commit()
    print("Added 10 Courses")
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = courses
    
    # --- Users & Students ---
    u_s1 = User(user_name='emma.watson', password='password', role='student')
    u_s2 = User(user_name='liam.miller', password='password', role='student')
    u_s3 = User(user_name='olivia.davis', password='password', role='student')
    u_s4 = User(user_name='noah.wilson', password='password', role='student')
    u_s5 = User(user_name='sophia.brown', password='password', role='student')
    u_s6 = User(user_name='james.taylor', password='password', role='student')
    u_s7 = User(user_name='mia.anderson', password='password', role='student')
    u_s8 = User(user_name='william.thomas', password='password', role='student')
    u_s9 = User(user_name='ava.martinez', password='password', role='student')
    u_s10 = User(user_name='ethan.garcia', password='password', role='student')
    db.session.add_all([u_s1, u_s2, u_s3, u_s4, u_s5, u_s6, u_s7, u_s8, u_s9, u_s10])
    db.session.commit()
    
    students = [
        Student(user_id=u_s1.user_id, roll_number='S001', full_name='Emma Watson', department_id=d1.id),
        Student(user_id=u_s2.user_id, roll_number='S002', full_name='Liam Miller', department_id=d2.id),
        Student(user_id=u_s3.user_id, roll_number='S003', full_name='Olivia Davis', department_id=d3.id),
        Student(user_id=u_s4.user_id, roll_number='S004', full_name='Noah Wilson', department_id=d4.id),
        Student(user_id=u_s5.user_id, roll_number='S005', full_name='Sophia Brown', department_id=d5.id),
        Student(user_id=u_s6.user_id, roll_number='S006', full_name='James Taylor', department_id=d6.id),
        Student(user_id=u_s7.user_id, roll_number='S007', full_name='Mia Anderson', department_id=d7.id),
        Student(user_id=u_s8.user_id, roll_number='S008', full_name='William Thomas', department_id=d8.id),
        Student(user_id=u_s9.user_id, roll_number='S009', full_name='Ava Martinez', department_id=d9.id),
        Student(user_id=u_s10.user_id, roll_number='S010', full_name='Ethan Garcia', department_id=d10.id)
    ]
    db.session.add_all(students)
    db.session.commit()
    print("Added 10 Student Users and 10 Students")
    st1, st2, st3, st4, st5, st6, st7, st8, st9, st10 = students
    
    # --- Results ---
    # We calculate the grade using your function, since there is no GRADE table
    results_data = [
        (st1.id, c1.id, s1.id, 95), (st1.id, c4.id, s2.id, 88), (st2.id, c2.id, s1.id, 82),
        (st3.id, c3.id, s2.id, 93), (st4.id, c4.id, s3.id, 96), (st5.id, c5.id, s1.id, 86),
        (st6.id, c6.id, s2.id, 80), (st7.id, c7.id, s3.id, 92), (st8.id, c8.id, s4.id, 70),
        (st9.id, c9.id, s1.id, 96), (st10.id, c10.id, s2.id, 68), (st1.id, c10.id, s3.id, 94),
        (st2.id, c5.id, s2.id, 85), (st3.id, c6.id, s3.id, 79), (st4.id, c4.id, s4.id, 84),
        (st5.id, c8.id, s2.id, 91), (st6.id, c9.id, s3.id, 77), (st7.id, c10.id, s4.id, 82),
        (st8.id, c1.id, s1.id, 89), (st9.id, c2.id, s2.id, 81)
    ]
    
    results = []
    for (stu_id, crs_id, sem_id, marks) in results_data:
        results.append(
            Result(
                student_id=stu_id, 
                course_id=crs_id, 
                semester_id=sem_id, 
                marks=marks, 
                grade=compute_grade(marks)
            )
        )
        
    db.session.add_all(results)
    db.session.commit()
    print(f"Added {len(results)} Results")
    
    # --- Admin User ---
    admin = User(user_name='admin', password='admin', role='admin')
    db.session.add(admin)
    db.session.commit()
    print("Added Admin user")

    print("\nDB initialized with all new data.")

if __name__ == "__main__":
    app.run(debug=True)