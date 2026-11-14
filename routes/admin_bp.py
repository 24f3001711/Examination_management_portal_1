from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import or_

from db import db
from models import (
    User,
    Examination,
    Course,
    ExaminationSlot,
    Booking,
    Evaluation,
    EvaluationDetail,
    ExaminationRubric,
    ExaminerProfile,
)



admin_bp= Blueprint(
    "admin",__name__,url_prefix="/api/admin"
)

def render_admin_dashboard(active_tab=None):
    search_query = request.args.get("q", "").strip()
    if active_tab is None:
        active_tab = "search" if search_query else "dashboard"
    pattern = f"%{search_query}%"
    record_id = int(search_query) if search_query.isdigit() else None

    courses = Course.query.all()
    examinations = Examination.query.all()
    examiners = User.query.filter_by(role="Examiner").order_by(User.id.desc()).all()
    students = User.query.filter_by(role="Student").all()
    slots = ExaminationSlot.query.all()
    bookings = Booking.query.all()
    search_examinations = []
    search_examiners = []
    search_students = []
    search_bookings = []

    if search_query:
        search_examinations = Examination.query.filter(or_(
            Examination.name.ilike(pattern),
            Examination.examination_type.ilike(pattern),
            Examination.id == record_id,
            Examination.course.has(or_(
                Course.course_code.ilike(pattern),
                Course.course_name.ilike(pattern),
            )),
        )).all()
        search_examiners = User.query.filter(
            User.role == "Examiner",
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                User.id == record_id,
                User.examiner_profile.has(ExaminerProfile.employee_id.ilike(pattern)),
            ),
        ).all()
        search_students = User.query.filter(
            User.role == "Student",
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                User.id == record_id,
            ),
        ).all()
        search_bookings = Booking.query.filter(or_(
            Booking.id == record_id,
            Booking.student.has(or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                User.id == record_id,
            )),
            Booking.slot.has(or_(
                ExaminationSlot.id == record_id,
                ExaminationSlot.examination.has(Examination.name.ilike(pattern)),
                ExaminationSlot.examiner.has(User.name.ilike(pattern)),
            )),
        )).all()

    return render_template(
        "admin/dashboard.html",
        search=search_query,
        active_tab=active_tab,
        courses=courses,
        examinations=examinations,
        examiners=examiners,
        students=students,
        slots=slots,
        bookings=bookings,
        search_examinations=search_examinations,
        search_examiners=search_examiners,
        search_students=search_students,
        search_bookings=search_bookings,
        all_courses=courses,
        all_examinations=examinations,
        all_examiners=examiners,
        all_students=students,
        all_slots=slots,
        all_bookings=bookings,
        rubrics=ExaminationRubric.query.all(),
        total_courses=Course.query.count(),
        total_examinations=Examination.query.count(),
        total_examiners=User.query.filter_by(role="Examiner").count(),
        total_students=User.query.filter_by(role="Student").count(),
        total_slots=ExaminationSlot.query.count(),
        total_bookings=Booking.query.count(),
    )

@admin_bp.route("/")
@admin_bp.route("/dashboard",methods=["GET"])
def dashboard():
    return render_admin_dashboard()


# Create 
@admin_bp.route("/courses", methods=["GET", "POST"])
def create_course():

    if request.method == "POST":
        data = request.form

        course_code = data.get("course_code")
        course_name = data.get("course_name")
        course_description = data.get("course_description")

        if not course_code or not course_name:
            flash("Course code or name are required")
            return redirect(url_for("admin.create_course"))

        if Course.query.filter_by(course_code=course_code).first():
            flash("Course Code Already Exists")
            return redirect(url_for("admin.create_course"))

        course = Course(
            course_code=course_code,
            course_name=course_name,
            description=course_description,
            status=data.get("course_status", "Active")
        )

        if course.status not in ["Active", "Inactive"]:
            flash("Course status is not correct")
            return redirect(url_for("admin.create_course"))

        db.session.add(course)
        db.session.commit()

        flash("Course created successfully!")
        return redirect(url_for("admin.create_course"))

    return render_admin_dashboard()
 




@admin_bp.route("/courses/<int:course_id>", methods=["POST"])
def update_courses(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for("admin.create_course"))

    course_code = request.form.get("course_code", "").strip()
    course_name = request.form.get("course_name", "").strip()
    if not course_code or not course_name:
        flash("Course code and name are required.", "danger")
        return redirect(url_for("admin.create_course"))

    duplicate = Course.query.filter(
        Course.course_code == course_code,
        Course.id != course_id,
    ).first()
    if duplicate:
        flash("Course code already exists.", "danger")
        return redirect(url_for("admin.create_course"))

    status = request.form.get("status", course.status)
    if status not in ["Active", "Inactive"]:
        flash("Invalid course status.", "danger")
        return redirect(url_for("admin.create_course"))

    course.course_code = course_code
    course.course_name = course_name
    course.description = request.form.get("description", "").strip() or None
    course.status = status

    db.session.commit()
    flash("Course updated successfully.", "success")
    return redirect(url_for("admin.create_course"))

# Delete a course when it is not attached to examinations.
@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
def delete_courses(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for("admin.create_course"))

    if course.examinations:
        flash("This course has examinations. Deactivate it instead of deleting.", "warning")
        return redirect(url_for("admin.create_course"))

    db.session.delete(course)
    db.session.commit()
    flash("Course deleted successfully.", "success")
    return redirect(url_for("admin.create_course"))

@admin_bp.route("/examinations", methods=["GET", "POST"])
def create_examination():

    if request.method == "POST":

        data = request.form

        course_id = data.get("course_id", type=int)
        name = data.get("name", "").strip()
        examination_type = data.get("examination_type")
        duration = data.get("duration_in_minutes")
        maximum_marks = data.get("maximum_marks")

        if not course_id or not name or not examination_type:
            flash("Required fields are missing")
            return redirect(url_for("admin.create_examination"))

        course = db.session.get(Course, course_id)

        if not course:
            flash("Course not found")
            return redirect(url_for("admin.create_examination"))

        if examination_type not in ["Viva", "Practical", "Project Demo", "Assessment"]:
            flash("Invalid examination type")
            return redirect(url_for("admin.create_examination"))
 
        try:
            duration = int(duration)
            maximum_marks = float(maximum_marks)
        except (ValueError, TypeError):
            flash("Invalid duration or maximum marks")
            return redirect(url_for("admin.create_examination"))

        if duration <= 0 or maximum_marks <= 0:
            flash("Duration and maximum marks must be positive")
            return redirect(url_for("admin.create_examination"))

        examination = Examination(
            course_id=course_id,
            name=name,
            examination_type=examination_type,
            duration_in_minutes=duration,
            maximum_marks=maximum_marks,
            status="Draft"
        )

        db.session.add(examination)
        db.session.commit()

        flash("Examination created successfully!")
        return redirect(url_for("admin.create_examination"))

    return render_admin_dashboard(active_tab="examination")






@admin_bp.route("/examinations/<int:examination_id>", methods=["GET", "POST"])
def update_examination(examination_id):
    examination = db.session.get(Examination, examination_id)
    if not examination:
        flash("Examination not found.", "danger")
        return redirect(url_for("admin.create_examination"))

    if request.method != "POST":
        return redirect(url_for("admin.create_examination"))

    data = request.form
    updates = {}

    if "course_id" in data:
        course_id = data.get("course_id", type=int)
        course = db.session.get(Course, course_id) if course_id else None
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("admin.create_examination"))
        updates["course_id"] = course.id

    if "name" in data:
        name = data.get("name", "").strip()
        if not name:
            flash("Examination name is required.", "danger")
            return redirect(url_for("admin.create_examination"))
        updates["name"] = name

    if "examination_type" in data:
        examination_type = data.get("examination_type")
        if examination_type not in ["Viva", "Practical", "Project Demo", "Assessment"]:
            flash("Invalid examination type.", "danger")
            return redirect(url_for("admin.create_examination"))
        updates["examination_type"] = examination_type

    if "duration_in_minutes" in data:
        try:
            duration = int(data.get("duration_in_minutes"))
        except (ValueError, TypeError):
            duration = 0
        if duration <= 0:
            flash("Duration must be a positive number of minutes.", "danger")
            return redirect(url_for("admin.create_examination"))
        updates["duration_in_minutes"] = duration

    if "maximum_marks" in data:
        try:
            maximum_marks = float(data.get("maximum_marks"))
        except (ValueError, TypeError):
            maximum_marks = 0
        if maximum_marks <= 0:
            flash("Maximum marks must be positive.", "danger")
            return redirect(url_for("admin.create_examination"))
        updates["maximum_marks"] = maximum_marks

    for field_name, value in updates.items():
        setattr(examination, field_name, value)
    db.session.commit()

    flash("Examination updated successfully.", "success")
    return redirect(url_for("admin.create_examination"))
                         


 


@admin_bp.route("/examinations/<int:examination_id>/delete", methods=["POST"])
def delete_examination(examination_id):

    examination = Examination.query.get(examination_id)

    if not examination:
        flash("Examination not found.", "danger")
        return redirect(url_for("admin.create_examination"))

    if examination.slots:
        flash("Examination has slots. Cancel it instead of deleting.", "warning")
        return redirect(url_for("admin.create_examination"))

    db.session.delete(examination)
    db.session.commit()

    flash("Examination deleted successfully!", "success")

    return redirect(url_for("admin.create_examination"))




 


@admin_bp.route("/rubrics", methods=["GET", "POST"])
def rubrics():

    if request.method == "POST":

        examination_id = request.form.get("examination_id")
        criterion_name = request.form.get("criterion_name")
        maximum_marks = request.form.get("maximum_marks")
        weightage = request.form.get("weightage")
        description = request.form.get("description")

        # Check required fields.
        if not examination_id or not criterion_name or not maximum_marks or weightage is None:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("admin.rubrics"))

        # Validate examination.
        examination = db.session.get(Examination, examination_id)

        if not examination:
            flash("Selected examination does not exist.", "danger")
            return redirect(url_for("admin.rubrics"))

        # Validate numeric values.
        try:
            maximum_marks = float(maximum_marks)
            weightage = float(weightage)
        except (ValueError, TypeError):
            flash("Marks and weightage must be valid numbers.", "danger")
            return redirect(url_for("admin.rubrics"))

        if maximum_marks <= 0:
            flash("Maximum marks must be greater than zero.", "danger")
            return redirect(url_for("admin.rubrics"))

        if not 0 <= weightage <= 100:
            flash("Weightage must be between 0 and 100.", "danger")
            return redirect(url_for("admin.rubrics"))

        # Create rubric.
        rubric = ExaminationRubric(
            examination_id=examination.id,
            criterion_name=criterion_name.strip(),
            maximum_marks=maximum_marks,
            weightage=weightage,
            description=description
        )

        db.session.add(rubric)
        db.session.commit()

        flash("Examination rubric created successfully.", "success")
        return redirect(url_for("admin.rubrics"))

    return render_admin_dashboard()


@admin_bp.route("/rubrics/<int:rubric_id>/edit", methods=["GET", "POST"])
def edit_rubric(rubric_id):

    rubric = db.session.get(ExaminationRubric, rubric_id)

    if not rubric:
        flash("Rubric not found.", "danger")
        return redirect(url_for("admin.rubrics"))

    if request.method == "POST":

        examination_id = request.form.get("examination_id")
        criterion_name = request.form.get("criterion_name")
        maximum_marks = request.form.get("maximum_marks")
        weightage = request.form.get("weightage")
        description = request.form.get("description")

        if (
            not examination_id
            or not criterion_name
            or not criterion_name.strip()
            or not maximum_marks
            or weightage is None
        ):
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("admin.edit_rubric", rubric_id=rubric.id))

        try:
            examination_id = int(examination_id)
        except (ValueError, TypeError):
            flash("Selected examination does not exist.", "danger")
            return redirect(url_for("admin.edit_rubric", rubric_id=rubric.id))

        examination = db.session.get(Examination, examination_id)

        if not examination:
            flash("Selected examination does not exist.", "danger")
            return redirect(url_for("admin.edit_rubric", rubric_id=rubric.id))

        try:
            maximum_marks = float(maximum_marks)
            weightage = float(weightage)
        except (ValueError, TypeError):
            flash("Marks and weightage must be valid numbers.", "danger")
            return redirect(url_for("admin.edit_rubric", rubric_id=rubric.id))

        if maximum_marks <= 0 or not 0 <= weightage <= 100:
            flash("Invalid marks or weightage.", "danger")
            return redirect(url_for("admin.edit_rubric", rubric_id=rubric.id))

        rubric.examination_id = examination.id
        rubric.criterion_name = criterion_name.strip()
        rubric.maximum_marks = maximum_marks
        rubric.weightage = weightage
        rubric.description = (description or "").strip()

        db.session.commit()

        flash("Rubric updated successfully.", "success")
        return redirect(url_for("admin.rubrics"))

    examinations = Examination.query.all()

    return render_template(
        "admin/edit_rubric.html",
        rubric=rubric,
        examinations=examinations
    )


@admin_bp.route("/rubrics/<int:rubric_id>/delete", methods=["POST"])
def delete_rubric(rubric_id):

    rubric = db.session.get(ExaminationRubric, rubric_id)

    if not rubric:
        flash("Rubric not found.", "danger")
        return redirect(url_for("admin.rubrics"))

    if EvaluationDetail.query.filter_by(rubric_id=rubric.id).first():
        flash(
            "This rubric has been deleted.",
            "warning"
        )
        return redirect(url_for("admin.rubrics"))

    db.session.delete(rubric)
    db.session.commit()

    flash("Rubric deleted successfully.", "success")
    return redirect(url_for("admin.rubrics"))



 
 
# ==========================================
# EXAMINER MANAGEMENT
# ==========================================

# Display all examiners and add a new examiner.
@admin_bp.route("/examiners", methods=["GET", "POST"])
def examiners():

    if request.method == "POST":

        # Get user details.
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")

        # Get examiner profile details.
        department = request.form.get("department")
        designation = request.form.get("designation")
        employee_id = request.form.get("employee_id")
        qualification = request.form.get("qualification")

        # Validate required fields.
        if not all([
            name, email, password,
            department, designation, employee_id
        ]):
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("admin.examiners"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("admin.examiners"))

        # Check duplicate email.
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("admin.examiners"))

        # Check duplicate employee ID.
        if ExaminerProfile.query.filter_by(employee_id=employee_id).first():
            flash("Employee ID already exists.", "danger")
            return redirect(url_for("admin.examiners"))

        # Check duplicate phone if provided.
        if phone and User.query.filter_by(phone=phone).first():
            flash("Phone number already exists.", "danger")
            return redirect(url_for("admin.examiners"))

        # Create examiner user.
        examiner = User(
            name=name,
            email=email,
            phone=phone or None,
            role="Examiner",
            status="Pending"
        )

        examiner.set_password(password)

        db.session.add(examiner)
        db.session.flush()
 
        # Create examiner profile.
        profile = ExaminerProfile(
            user_id=examiner.id,
            department=department,
            designation=designation,
            employee_id=employee_id,
            qualification=qualification
        )

        db.session.add(profile)
        db.session.commit()

        flash("Examiner added successfully. Awaiting approval.", "success")

        return redirect(url_for("admin.examiners"))

    return render_admin_dashboard()


# Approve, deactivate, reactivate or block an examiner.
@admin_bp.route("/examiners/<int:user_id>/status", methods=["POST"])
def update_examiner_status(user_id):

    examiner = db.session.get(User, user_id)

    if not examiner or examiner.role != "Examiner":
        flash("Examiner not found.", "danger")
        return redirect(url_for("admin.examiners"))

    new_status = request.form.get("status")

    allowed_statuses = [
        "Approved",
        "Pending",
        "Deactivated",
        "Blocked"
    ]

    if new_status not in allowed_statuses:
        flash("Invalid examiner status.", "danger")
        return redirect(url_for("admin.examiners"))

    examiner.status = new_status

    db.session.commit()

    flash(
        f"Examiner status changed to {new_status}.",
        "success"
    )

    return redirect(url_for("admin.examiners"))


@admin_bp.route("/students/<int:user_id>/status", methods=["POST"])
def update_student_status(user_id):

    student = db.session.get(User, user_id)

    if not student or student.role != "Student":
        flash("Student not found.", "danger")
        return redirect(url_for("admin.students"))

    new_status = request.form.get("status")
    allowed_statuses = ["Approved", "Pending", "Deactivated", "Blocked"]

    if new_status not in allowed_statuses:
        flash("Invalid student status.", "danger")
        return redirect(url_for("admin.students"))

    student.status = new_status
    db.session.commit()

    flash(f"Student status changed to {new_status}.", "success")
    return redirect(url_for("admin.students"))



# Configure examination timelines.
@admin_bp.route("/examinations/<int:examination_id>/timeline", methods=["POST"])
def update_examination_timeline(examination_id):

    examination = db.session.get(Examination, examination_id)

    if not examination:
        flash("Examination not found.", "danger")
        return redirect(url_for("admin.create_examination"))

    fields = [
        "slot_creation_start",
        "slot_creation_end",
        "slot_booking_start",
        "slot_booking_end",
    ]

    try:
        dates = {
            field: datetime.strptime(
                request.form.get(field, ""),
                "%Y-%m-%dT%H:%M",
            )
            for field in fields
        }
    except (TypeError, ValueError):
        flash("Please provide valid dates for all examination timelines.", "danger")
        return redirect(url_for("admin.create_examination"))

    if dates["slot_creation_start"] >= dates["slot_creation_end"]:
        flash("Slot creation start date must be before end date.", "danger")
        return redirect(url_for("admin.create_examination"))

    if dates["slot_booking_start"] >= dates["slot_booking_end"]:
        flash("Student booking start date must be before end date.", "danger")
        return redirect(url_for("admin.create_examination"))

    examination.slot_creation_start = dates["slot_creation_start"]
    examination.slot_creation_end = dates["slot_creation_end"]
    examination.slot_booking_start = dates["slot_booking_start"]
    examination.slot_booking_end = dates["slot_booking_end"]
    db.session.commit()

    

    flash("Examination timeline updated successfully.", "success")
    return redirect(url_for("admin.create_examination"))



@admin_bp.route(
    "/examinations/<int:examination_id>/slot-creation/<string:action>",
    methods=["POST"]
)

def toggle_slot_creation(examination_id, action):

    examination = Examination.query.get_or_404(examination_id)

    if action == "open":

        if not examination.slot_creation_start or not examination.slot_creation_end:
            flash("Configure examiner slot creation timeline first.", "danger")
            return redirect(url_for("admin.create_examination"))

        examination.slot_creation_open = True

        examination.status = "Slot Creation"

        flash("Examiner slot creation opened successfully.", "success")

    elif action == "close":

        examination.slot_creation_open = False

        if examination.booking_open:
            examination.status = "Booking Open"
        else:
            examination.status = "Closed"

        flash("Examiner slot creation closed successfully.", "success")

    else:
        flash("Invalid action.", "danger")
        return redirect(url_for("admin.create_examination"))

    db.session.commit()

    return redirect(url_for("admin.create_examination"))


@admin_bp.route(
    "/examinations/<int:examination_id>/booking/<string:action>",
    methods=["POST"]
)
def toggle_slot_booking(examination_id, action):

    examination = Examination.query.get_or_404(examination_id)

    if action == "open":

        if not examination.slot_booking_start or not examination.slot_booking_end:
            flash("Configure student booking timeline first.", "danger")
            return redirect(url_for("admin.create_examination"))

        if examination.slot_booking_start >= examination.slot_booking_end:
            flash("Student booking start date must be before end date.", "danger")
            return redirect(url_for("admin.create_examination"))

        examination.booking_open = True

        examination.status = "Booking Open"

        flash("Student slot booking opened successfully.", "success")

    elif action == "close":

        examination.booking_open = False

        if examination.slot_creation_open:
            examination.status = "Slot Creation"
        else:
            examination.status = "Closed"

        flash("Student slot booking closed successfully.", "success")

    else:
        flash("Invalid action.", "danger")
        return redirect(url_for("admin.create_examination"))

    db.session.commit()

    return redirect(url_for("admin.create_examination"))




# Admin pages displayed through the sidebar.
@admin_bp.route("/students")
def students():
    return render_admin_dashboard()


@admin_bp.route("/bookings")
def bookings():
    return render_admin_dashboard()


@admin_bp.route("/search")
def search():
    return render_admin_dashboard()


@admin_bp.route("/history")
def history():
    return render_admin_dashboard()


@admin_bp.route("/analytics")
def analytics():
    return render_admin_dashboard()

@admin_bp.route("/logout")
def logout():
    return redirect(url_for("auth.logout"))

@admin_bp.route(
    "/bookings/<int:booking_id>/reschedule",
    methods=["POST"]
)
def reschedule_booking(booking_id):

    # 1. Get existing booking
    booking = Booking.query.get_or_404(booking_id)

    # 2. Check booking status
    if booking.status != "Booked":
        flash("Only active bookings can be rescheduled.", "danger")
        return redirect(url_for("admin.bookings"))

    # 3. Get new slot ID from form
    new_slot_id = request.form.get("slot_id", type=int)

    if not new_slot_id:
        flash("Please select a valid slot.", "danger")
        return redirect(url_for("admin.bookings"))

    # 4. Get target slot
    new_slot = ExaminationSlot.query.get(new_slot_id)

    if not new_slot:
        flash("Selected slot does not exist.", "danger")
        return redirect(url_for("admin.bookings"))

    # 5. Check whether selected slot is the current slot
    if booking.slot_id == new_slot.id:
        flash("Booking is already assigned to this slot.", "warning")
        return redirect(url_for("admin.bookings"))

    # 6. Check examination
    old_slot = booking.slot

    if new_slot.examination_id != old_slot.examination_id:
        flash(
            "You can only reschedule within the same examination.",
            "danger"
        )
        return redirect(url_for("admin.bookings"))

    # 7. Check slot status
    if new_slot.status != "Available":
        flash("Selected slot is not available.", "danger")
        return redirect(url_for("admin.bookings"))

    # 8. Check available capacity
    if new_slot.available_seats <= 0:
        flash("Selected slot is full.", "danger")
        return redirect(url_for("admin.bookings"))

    # 9. Update booking
   
    booking.slot_id = new_slot.id

    # Update old slot status if it was full
    if old_slot.status == "Full":
        old_slot.status = "Available"

 
        # Update new slot status if it becomes full
    if new_slot.available_seats <= 0:
        new_slot.status = "Full"

    db.session.commit()
    flash("Booking rescheduled successfully.", "success")
 

    return redirect(url_for("admin.bookings"))




@admin_bp.route("/slots", methods=["POST"])
def create_slot():
    examination_id = request.form.get("examination_id", type=int)
    examiner_id = request.form.get("examiner_id", type=int)

    examination = db.session.get(Examination, examination_id) if examination_id else None
    examiner = User.query.filter_by(
        id=examiner_id,
        role="Examiner",
        status="Approved",
    ).first() if examiner_id else None

    if not examination:
        flash("Select a valid examination.", "danger")
        return redirect(url_for("admin.create_examination"))

    if examination.status in ["Cancelled", "Completed"]:
        flash("Slots cannot be added to cancelled or completed examinations.", "danger")
        return redirect(url_for("admin.create_examination"))

    if not examiner:
        flash("Select an approved examiner.", "danger")
        return redirect(url_for("admin.create_examination"))

    try:
        slot_date = datetime.strptime(
            request.form.get("date", ""),
            "%Y-%m-%d",
        ).date()
        start_time = datetime.strptime(
            request.form.get("start_time", ""),
            "%H:%M",
        ).time()
        end_time = datetime.strptime(
            request.form.get("end_time", ""),
            "%H:%M",
        ).time()
        capacity = int(request.form.get("maximum_capacity", ""))
    except (TypeError, ValueError):
        flash("Enter a valid date, time, and capacity.", "danger")
        return redirect(url_for("admin.create_examination"))

    if start_time >= end_time or capacity <= 0:
        flash("Enter a valid time range and a capacity greater than zero.", "danger")
        return redirect(url_for("admin.create_examination"))

    conflict = ExaminationSlot.query.filter(
        ExaminationSlot.examiner_id == examiner.id,
        ExaminationSlot.date == slot_date,
        ExaminationSlot.status.notin_(["Cancelled", "Completed"]),
        ExaminationSlot.start_time < end_time,
        ExaminationSlot.end_time > start_time,
    ).first()

    if conflict:
        flash("This examiner already has another examination during that time.", "danger")
        return redirect(url_for("admin.create_examination"))

    slot = ExaminationSlot(
        examination_id=examination.id,
        examiner_id=examiner.id,
        date=slot_date,
        start_time=start_time,
        end_time=end_time,
        maximum_capacity=capacity,
    )
    db.session.add(slot)
    db.session.commit()

    flash("Examination slot added successfully.", "success")
    return redirect(url_for("admin.create_examination"))


@admin_bp.route(
    "/slots/<int:slot_id>/change-examiner",
    methods=["POST"]
)
def change_examiner(slot_id):

    # 1. Get examination slot
    slot = ExaminationSlot.query.get_or_404(slot_id)

    # 2. Get new examiner ID
    new_examiner_id = request.form.get("examiner_id", type=int)

    if not new_examiner_id:
        flash("Please select an examiner.", "danger")
        return redirect(url_for("admin.create_examination"))

    # 3. Check slot status
    if slot.status in ["Cancelled", "Completed"]:
        flash(
            "Examiner cannot be changed for cancelled or completed slots.",
            "danger"
        )
        return redirect(url_for("admin.create_examination"))

    # 4. Get new examiner
    examiner = User.query.filter_by(
        id=new_examiner_id,
        role="Examiner",
        status="Approved"
    ).first()

    if not examiner:
        flash("Selected examiner is not approved or does not exist.", "danger")
        return redirect(url_for("admin.create_examination"))

    # 5. Check whether examiner is already assigned
    if slot.examiner_id == examiner.id:
        flash("This examiner is already assigned to the slot.", "warning")
        return redirect(url_for("admin.create_examination"))

    # 6. Check examiner's existing slot conflicts
    conflict = ExaminationSlot.query.filter(
        ExaminationSlot.examiner_id == examiner.id,
        ExaminationSlot.date == slot.date,
        ExaminationSlot.id != slot.id,
        ExaminationSlot.status.notin_(["Cancelled", "Completed"]),
        ExaminationSlot.start_time < slot.end_time,
        ExaminationSlot.end_time > slot.start_time
    ).first()


 


    if conflict:
        flash(
            "This examiner already has another examination during this time.",
            "danger"
        )
        return redirect(url_for("admin.create_examination"))

 
    slot.examiner_id = examiner.id

    db.session.commit()

    flash(
            f"Examiner successfully changed to {examiner.name}.",
            "success"
        )


    return redirect(url_for("admin.create_examination"))