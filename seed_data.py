from datetime import datetime, timezone, date, time, timedelta
from db import db
from models import (
    User,
    ExaminerProfile,
    Course,
    Examination,
    ExaminationRubric,
    ExaminationSlot,
    Booking,
    Evaluation,
    EvaluationDetail
)



 

from models import (
    User,
    ExaminerProfile,
    Course,
    Examination,
    ExaminationRubric,
    ExaminationSlot,
    Booking,
    Evaluation,
    EvaluationDetail
)


def create_admin():
    admin = User.query.filter_by(email="admin13@gmail.com").first()
    if admin is None:
        admin = User(
            name="Exam Admin",
            email="admin13@gmail.com",
            role="Admin",
            status="Approved",
        )
        admin.set_password("admin123")
        db.session.add(admin) 
        db.session.commit()
        print("Admin Account Created")
    else:    
        print("Admin Already Exists")

def seed_data():

    try:

        # --------------------------------------------------
        # 1. EXAMINERS
        # --------------------------------------------------

        examiners_data = [
            {
                "name": "Rahul Sharma",
                "email": "rahul.examiner@example.com",
                "password": "examiner123",
                "phone": "9876543210",
                "department": "Computer Science",
                "designation": "Assistant Professor",
                "employee_id": "EMP001",
                "qualification": "M.Tech Computer Science"
            },
            {
                "name": "Priya Verma",
                "email": "priya.examiner@example.com",
                "password": "examiner123",
                "phone": "9876543211",
                "department": "Data Science",
                "designation": "Associate Professor",
                "employee_id": "EMP002",
                "qualification": "PhD Data Science"
            },
            {
                "name": "Amit Kumar",
                "email": "amit.examiner@example.com",
                "password": "examiner123",
                "phone": "9876543212",
                "department": "Artificial Intelligence",
                "designation": "Assistant Professor",
                "employee_id": "EMP003",
                "qualification": "M.Tech Artificial Intelligence"
            }
        ]

        examiners = []

        for data in examiners_data:

            user = User.query.filter_by(email=data["email"]).first()

            if not user:

                user = User(
                    name=data["name"],
                    email=data["email"],
                    phone=data["phone"],
                    role="Examiner",
                    status="Approved"
                )

                user.set_password(data["password"])

                db.session.add(user)
                db.session.flush()

            profile = ExaminerProfile.query.filter_by(
                user_id=user.id
            ).first()

            if not profile:

                profile = ExaminerProfile(
                    user_id=user.id,
                    department=data["department"],
                    designation=data["designation"],
                    employee_id=data["employee_id"],
                    qualification=data["qualification"]
                )

                db.session.add(profile)

            examiners.append(user)

        db.session.flush()

        # --------------------------------------------------
        # 2. STUDENTS
        # --------------------------------------------------

        students_data = [
            ("Aman Kumar", "aman.student@example.com", "9876500001"),
            ("Rohit Singh", "rohit.student@example.com", "9876500002"),
            ("Neha Gupta", "neha.student@example.com", "9876500003"),
            ("Karan Mehta", "karan.student@example.com", "9876500004"),
            ("Sneha Sharma", "sneha.student@example.com", "9876500005"),
            ("Vikas Yadav", "vikas.student@example.com", "9876500006")
        ]

        students = []

        for name, email, phone in students_data:

            user = User.query.filter_by(email=email).first()

            if not user:

                user = User(
                    name=name,
                    email=email,
                    phone=phone,
                    role="Student",
                    status="Approved"
                )

                user.set_password("student123")

                db.session.add(user)
                db.session.flush()

            students.append(user)

        # --------------------------------------------------
        # 3. COURSES
        # --------------------------------------------------

        courses_data = [
            {
                "course_code": "CS101",
                "course_name": "Python Programming",
                "description": "Fundamentals of Python programming."
            },
            {
                "course_code": "CS102",
                "course_name": "Data Structures and Algorithms",
                "description": "Study of fundamental data structures and algorithms."
            },
            {
                "course_code": "DS101",
                "course_name": "Data Science",
                "description": "Introduction to data science and analytics."
            },
            {
                "course_code": "AI101",
                "course_name": "Artificial Intelligence",
                "description": "Fundamentals of artificial intelligence and machine learning."
            }
        ]

        courses = {}

        for data in courses_data:

            course = Course.query.filter_by(
                course_code=data["course_code"]
            ).first()

            if not course:

                course = Course(
                    course_code=data["course_code"],
                    course_name=data["course_name"],
                    description=data["description"],
                    status="Active"
                )

                db.session.add(course)
                db.session.flush()

            courses[data["course_code"]] = course

        # --------------------------------------------------
        # 4. EXAMINATIONS
        # --------------------------------------------------

        examinations_data = [
            {
                "course": "CS101",
                "name": "Python Programming Viva",
                "type": "Viva",
                "duration": 30,
                "marks": 100
            },
            {
                "course": "CS102",
                "name": "DSA Practical Examination",
                "type": "Practical",
                "duration": 60,
                "marks": 100
            },
            {
                "course": "DS101",
                "name": "Data Science Project Demo",
                "type": "Project Demo",
                "duration": 45,
                "marks": 100
            },
            {
                "course": "AI101",
                "name": "AI Assessment",
                "type": "Assessment",
                "duration": 30,
                "marks": 100
            }
        ]

        examinations = []

        for index, data in enumerate(examinations_data):

            examination = Examination.query.filter_by(
                course_id=courses[data["course"]].id,
                name=data["name"]
            ).first()

            if not examination:

                today = datetime.now(timezone.utc)

                examination = Examination(
                    course_id=courses[data["course"]].id,
                    name=data["name"],
                    examination_type=data["type"],
                    duration_in_minutes=data["duration"],
                    maximum_marks=data["marks"],

                    slot_creation_start=today - timedelta(days=2),
                    slot_creation_end=today + timedelta(days=10),

                    slot_booking_start=today - timedelta(days=1),
                    slot_booking_end=today + timedelta(days=15),

                    slot_creation_open=True,
                    booking_open=True,
                    status="Booking Open"
                )

                db.session.add(examination)
                db.session.flush()

            examinations.append(examination)

        # --------------------------------------------------
        # 5. EXAMINATION RUBRICS
        # --------------------------------------------------

        rubric_data = [
            [
                ("Conceptual Knowledge", 30, 30),
                ("Technical Knowledge", 30, 30),
                ("Communication", 20, 20),
                ("Problem Solving", 20, 20)
            ],
            [
                ("Algorithm Design", 30, 30),
                ("Code Implementation", 30, 30),
                ("Time Complexity", 20, 20),
                ("Problem Solving", 20, 20)
            ],
            [
                ("Project Understanding", 25, 25),
                ("Implementation", 30, 30),
                ("Presentation", 25, 25),
                ("Innovation", 20, 20)
            ],
            [
                ("AI Concepts", 30, 30),
                ("Technical Implementation", 30, 30),
                ("Problem Solving", 20, 20),
                ("Explanation", 20, 20)
            ]
        ]

        for examination, rubrics in zip(examinations, rubric_data):

            existing = ExaminationRubric.query.filter_by(
                examination_id=examination.id
            ).first()

            if not existing:

                for name, marks, weightage in rubrics:

                    db.session.add(
                        ExaminationRubric(
                            examination_id=examination.id,
                            criterion_name=name,
                            maximum_marks=marks,
                            weightage=weightage,
                            description=f"Evaluation of {name.lower()}."
                        )
                    )

        db.session.flush()

        # --------------------------------------------------
        # 6. EXAMINATION SLOTS
        # --------------------------------------------------

        slots = []

        today = date.today()

        for index, examination in enumerate(examinations):

            examiner = examiners[index % len(examiners)]

            for day_offset in range(1, 4):

                slot_date = today + timedelta(days=day_offset)

                start = time(10 + day_offset, 0)
                end = time(11 + day_offset, 0)

                slot = ExaminationSlot.query.filter_by(
                    examination_id=examination.id,
                    examiner_id=examiner.id,
                    date=slot_date,
                    start_time=start
                ).first()

                if not slot:

                    slot = ExaminationSlot(
                        examination_id=examination.id,
                        examiner_id=examiner.id,
                        date=slot_date,
                        start_time=start,
                        end_time=end,
                        maximum_capacity=5,
                        status="Available",
                        meeting_link="https://meet.google.com/example"
                    )

                    db.session.add(slot)
                    db.session.flush()

                slots.append(slot)

        # --------------------------------------------------
        # 7. BOOKINGS
        # --------------------------------------------------

        bookings = []

        for index, student in enumerate(students):

            slot = slots[index % len(slots)]

            booking = Booking.query.filter_by(
                student_id=student.id,
                slot_id=slot.id
            ).first()

            if not booking:

                booking = Booking(
                    student_id=student.id,
                    slot_id=slot.id,
                    status="Booked"
                )

                db.session.add(booking)
                db.session.flush()

            bookings.append(booking)

        # --------------------------------------------------
        # 8. EVALUATIONS
        # --------------------------------------------------

        for index, booking in enumerate(bookings):

            # Keep the last two bookings unevaluated.
            if index >= len(bookings) - 2:
                continue

            if booking.evaluation:
                continue

            slot = booking.slot

            evaluation = Evaluation(
                booking_id=booking.id,
                examiner_id=slot.examiner_id,
                total_marks=0,
                remarks="Good performance.",
                is_published=True
            )

            db.session.add(evaluation)
            db.session.flush()

            # --------------------------------------------------
            # 9. EVALUATION DETAILS
            # --------------------------------------------------

            rubrics = ExaminationRubric.query.filter_by(
                examination_id=slot.examination_id
            ).all()

            total_marks = 0

            for rubric_index, rubric in enumerate(rubrics):

                awarded = round(
                    rubric.maximum_marks * (0.75 + (index % 3) * 0.05),
                    2
                )

                awarded = min(awarded, rubric.maximum_marks)

                total_marks += awarded

                detail = EvaluationDetail(
                    evaluation_id=evaluation.id,
                    rubric_id=rubric.id,
                    marks_awarded=awarded
                )

                db.session.add(detail)

            evaluation.total_marks = total_marks

            booking.status = "Completed"

        # --------------------------------------------------
        # COMMIT
        # --------------------------------------------------

        db.session.commit()

        print("\n===================================")
        print("SEED DATA CREATED SUCCESSFULLY!")
        print("===================================")
        print(f"Examiners: {len(examiners)}")
        print(f"Students: {len(students)}")
        print(f"Courses: {len(courses)}")
        print(f"Examinations: {len(examinations)}")
        print(f"Slots: {len(slots)}")
        print(f"Bookings: {len(bookings)}")
        print(f"===================================\n")

    except Exception as e:

        db.session.rollback()

        print("Error while seeding data:", e)

        raise

 




