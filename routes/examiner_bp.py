from datetime import datetime
from math import isfinite

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from db import db
from routes.utils import role_required
from models import (
    Booking,
    Evaluation,
    EvaluationDetail,
    Examination,
    ExaminationRubric,
    ExaminationSlot,
    ExaminerProfile,
    User,
)

examiner_bp = Blueprint("examiner", __name__, url_prefix="/api/examiner")

@examiner_bp.route("/logout")
def logout():
    return redirect(url_for("auth.logout"))

def _slot_creation_open(examination):
    now = datetime.now()
    return (
        examination.slot_creation_open
        and examination.slot_creation_start
        and examination.slot_creation_end
        and examination.slot_creation_start <= now <= examination.slot_creation_end
    )


def _booking_started(examination):
    return examination.booking_open or (
        examination.slot_booking_start
        and datetime.now() >= examination.slot_booking_start
    )


def _slot_form_data():
    try:
        slot_date = datetime.strptime(
            request.form.get("date", ""), "%Y-%m-%d"
        ).date()
        start_time = datetime.strptime(
            request.form.get("start_time", ""), "%H:%M"
        ).time()
        end_time = datetime.strptime(
            request.form.get("end_time", ""), "%H:%M"
        ).time()
        capacity = int(request.form.get("maximum_capacity", ""))
    except (TypeError, ValueError):
        return None

    if start_time >= end_time or capacity <= 0:
        return None

    return slot_date, start_time, end_time, capacity


def render_examiner_dashboard(examiner):
    slots = (
        ExaminationSlot.query.filter_by(examiner_id=examiner.id)
        .order_by(ExaminationSlot.date, ExaminationSlot.start_time)
        .all()
    )
    assigned_examination_ids = {slot.examination_id for slot in slots}
    examinations = [
        examination
        for examination in Examination.query.all()
        if (
            examination.id in assigned_examination_ids
            or _slot_creation_open(examination)
        )
    ]
    booked_students = Booking.query.filter(
        Booking.status == "Booked",
        Booking.slot.has(examiner_id=examiner.id),
    ).count()
    pending_evaluations = (
        Booking.query.filter(
            Booking.status == "Booked",
            Booking.slot.has(examiner_id=examiner.id),
            ~Booking.evaluation.has(),
        )
        .count()
    )
    rubrics_by_examination = {}
    slot_permissions = {}
    for examination in examinations:
        rubrics_by_examination[examination.id] = ExaminationRubric.query.filter_by(
            examination_id=examination.id,
        ).order_by(ExaminationRubric.id).all()
        slot_permissions[examination.id] = {
            "can_create_slots": _slot_creation_open(examination),
            "can_manage_slots": not _booking_started(examination),
        }

    context = {
        "examiner": examiner,
        "examinations": examinations,
        "slots": slots,
        "rubrics_by_examination": rubrics_by_examination,
        "slot_permissions": slot_permissions,
        "booked_students": booked_students,
        "pending_evaluations": pending_evaluations,
    }
    return render_template("examiner/dashboard.html", **context)






@examiner_bp.route("/dashboard", methods=["GET"])
@role_required("Examiner")
def dashboard(current_user):
    return render_examiner_dashboard(current_user)


 
@examiner_bp.route("/profile", methods=["POST"])
@role_required("Examiner")
def update_profile(current_user):

    examiner = current_user

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip() or None

    department = request.form.get("department", "").strip()
    designation = request.form.get("designation", "").strip()
    employee_id = request.form.get("employee_id", "").strip()
    qualification = request.form.get("qualification", "").strip() or None

    if not all([name, email, department, designation, employee_id]):
        flash("Please fill all required fields.", "danger")
        return redirect(url_for("examiner.dashboard"))

    existing_email = User.query.filter(
        User.email == email,
        User.id != examiner.id
    ).first()

    if existing_email:
        flash("Email address is already registered.", "danger")
        return redirect(url_for("examiner.dashboard"))

    if phone:
        existing_phone = User.query.filter(
            User.phone == phone,
            User.id != examiner.id
        ).first()

        if existing_phone:
            flash("Phone number is already registered.", "danger")
            return redirect(url_for("examiner.dashboard"))

    existing_employee = ExaminerProfile.query.filter(
        ExaminerProfile.employee_id == employee_id,
        ExaminerProfile.user_id != examiner.id
    ).first()

    if existing_employee:
        flash("Employee ID is already registered.", "danger")
        return redirect(url_for("examiner.dashboard"))

    examiner.name = name
    examiner.email = email
    examiner.phone = phone

    profile = examiner.examiner_profile

    if profile:
        profile.department = department
        profile.designation = designation
        profile.employee_id = employee_id
        profile.qualification = qualification

    else:
        profile = ExaminerProfile(
            user_id=examiner.id,
            department=department,
            designation=designation,
            employee_id=employee_id,
            qualification=qualification
        )

        db.session.add(profile)

    db.session.commit()

    session["name"] = examiner.name

    flash("Profile updated successfully.", "success")

    return redirect(url_for("examiner.dashboard"))





@examiner_bp.route(
    "/examinations/<int:examination_id>/slots",
    methods=["POST"]
)
@role_required("Examiner")
def create_slot(examination_id, current_user):

    examination = db.session.get(Examination, examination_id)

    if not examination:
        flash("No examination found.", "danger")
        return redirect(url_for("examiner.dashboard"))

    if not _slot_creation_open(examination):
        flash("Slot creation is not open for this examination.", "warning")
        return redirect(url_for("examiner.dashboard"))

    slot_data = _slot_form_data()
    if not slot_data:
        flash("Enter a valid date, time range, and capacity.", "danger")
        return redirect(url_for("examiner.dashboard"))
    date, start_time, end_time, capacity = slot_data

    # Check overlapping slots
    conflict = ExaminationSlot.query.filter(
        ExaminationSlot.examiner_id == current_user.id,
        ExaminationSlot.date == date,
        ExaminationSlot.status.notin_(["Cancelled", "Completed"]),
        ExaminationSlot.start_time < end_time,
        ExaminationSlot.end_time > start_time
    ).first()

    if conflict:
        flash(
            "You already have another examination during this time.",
            "danger"
        )
        return redirect(url_for("examiner.dashboard"))

    slot = ExaminationSlot(
        examination_id=examination.id,
        examiner_id=current_user.id,
        date=date,
        start_time=start_time,
        end_time=end_time,
        maximum_capacity=capacity
    )

    db.session.add(slot)
    db.session.commit()

    flash("Examination slot created successfully!", "success")

    return redirect(url_for("examiner.dashboard"))


@examiner_bp.route("/slots/<int:slot_id>/update", methods=["POST"])
@role_required("Examiner")
def update_slot(slot_id, current_user):

    slot = ExaminationSlot.query.filter_by(
        id=slot_id,
        examiner_id=current_user.id
    ).first_or_404()

    if _booking_started(slot.examination) or slot.bookings:
        flash(
            "Slots can only be changed before booking starts and before students book the slot.",
            "warning"
        )
        return redirect(url_for("examiner.dashboard"))

    slot_data = _slot_form_data()
    if not slot_data:
        flash("Enter a valid date, time range, and capacity.", "danger")
        return redirect(url_for("examiner.dashboard"))
    date, start_time, end_time, capacity = slot_data

    # Check overlapping slots
    conflict = ExaminationSlot.query.filter(
        ExaminationSlot.examiner_id == current_user.id,
        ExaminationSlot.date == date,
        ExaminationSlot.id != slot.id,
        ExaminationSlot.status.notin_(["Cancelled", "Completed"]),
        ExaminationSlot.start_time < end_time,
        ExaminationSlot.end_time > start_time
    ).first()

    if conflict:
        flash(
            "You already have another examination during this time.",
            "danger"
        )
        return redirect(url_for("examiner.dashboard"))

    slot.date = date
    slot.start_time = start_time
    slot.end_time = end_time
    slot.maximum_capacity = capacity

    db.session.commit()

    flash("Examination slot updated successfully!", "success")

    return redirect(url_for("examiner.dashboard"))


# DELETE EXAMINATION SLOT
@examiner_bp.route("/slots/<int:slot_id>/delete", methods=["POST"])
@role_required("Examiner")
def delete_slot(slot_id, current_user):

    slot = ExaminationSlot.query.filter_by(
        id=slot_id,
        examiner_id=current_user.id
    ).first_or_404()

    if _booking_started(slot.examination) or slot.bookings:
        flash(
            "Slot can only be deleted before booking starts and before any student books it.",
            "warning"
        )
        return redirect(url_for("examiner.dashboard"))

    db.session.delete(slot)
    db.session.commit()

    flash("Examination slot deleted successfully.", "success")

    return redirect(url_for("examiner.dashboard"))


# EVALUATE STUDENT
@examiner_bp.route(
    "/bookings/<int:booking_id>/evaluate",
    methods=["POST"]
)
@role_required("Examiner")
def evaluate_student(booking_id, current_user):

    # 1. Check booking belongs to examiner
    booking = Booking.query.join(ExaminationSlot).filter(
        Booking.id == booking_id,
        ExaminationSlot.examiner_id == current_user.id
    ).first_or_404()

    # 2. Check booking status
    if booking.status != "Booked":
        flash("This booking cannot be evaluated.", "danger")
        return redirect(url_for("examiner.dashboard"))

    # 3. Fetch examination rubrics
    rubrics = ExaminationRubric.query.filter_by(
        examination_id=booking.slot.examination_id
    ).order_by(ExaminationRubric.id).all()

    if not rubrics:
        flash("No evaluation criteria found.", "danger")
        return redirect(url_for("examiner.dashboard"))

    evaluation = booking.evaluation

    marks_by_rubric = {}

    # 4. Validate marks
    for rubric in rubrics:

        try:
            marks = float(request.form.get(f"marks_{rubric.id}", ""))
        except ValueError:
            flash("Enter valid marks for every criterion.", "danger")
            return redirect(url_for("examiner.dashboard"))

        if not isfinite(marks) or marks < 0 or marks > rubric.maximum_marks:
            flash(
                f"Invalid marks for {rubric.criterion_name}.",
                "danger"
            )
            return redirect(url_for("examiner.dashboard"))

        marks_by_rubric[rubric.id] = marks

    # 5. Calculate total marks
    total_marks = sum(marks_by_rubric.values())

    remarks = request.form.get("remarks", "").strip() or None

    # 6. Create or update evaluation
    if evaluation:

        evaluation.total_marks = total_marks
        evaluation.remarks = remarks
        evaluation.examiner_id = current_user.id

        evaluation.details.clear()

    else:

        evaluation = Evaluation(
            booking_id=booking.id,
            examiner_id=current_user.id,
            total_marks=total_marks,
            remarks=remarks
        )

        db.session.add(evaluation)
        db.session.flush()

    # 7. Save rubric-wise marks
    evaluation.details = [
        EvaluationDetail(
            rubric_id=rubric_id,
            marks_awarded=marks
        )
        for rubric_id, marks in marks_by_rubric.items()
    ]

    db.session.commit()

    flash("Student evaluated successfully.", "success")

    return redirect(url_for("examiner.dashboard"))











