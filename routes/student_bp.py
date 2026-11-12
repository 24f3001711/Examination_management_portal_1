from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from db import db
from models import (
    Booking,
    Evaluation,
    EvaluationDetail,
    Examination,
    ExaminationRubric,
    ExaminationSlot,
    ExaminerProfile,
    User,Course
)
from routes.utils import role_required

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


def _booking_open(examination):

    now=datetime.now()

    # Booking ? Admin booking enable ? Booking start time is defined ? Booking End time is defined ? Current time start b/w end 

    return(
        examination.booking_open and examination.slot_booking_start and examination.slot_booking_end and examination.slot_booking_start <=now <= examination.slot_booking_end
    )
    
 





@student_bp.route("/dashboard", methods=["GET"])
@role_required("Student")
def dashboard(current_user):

    search=request.args.get("q","").strip()
    course_id=request.args.get("course_id",type=int)
    examination_type= request.args.get("type","").strip()

    # fetch active courses ? examinations 
    examinations_query=Examination.query.join(Course).filter(Course.status=="Active",Examination.status.notin_(["Draft","Cancelled","Completed"]))

    # search ?
    if search:
        examinations_query=examinations_query.filter(or_(
            Examination.name.ilike(f"%{search}%"),
            Course.course_name.ilike(f"%{search}%"),
            Course.course_type.ilike(f"%{search}%"),

        ))
    if course_id:
        examinations_query=examinations_query.filter(
            Examination.course_id==course_id
        )
    if  examination_type:
        examinations_query=examinations_query.filter(
            Examination.examination_type  ==course_id
        )


    examinations = examinations_query.order_by(Examination.name).all()

    examination_ids=[ exam.id for exam in examinations]

    # slots ? cancel and completed .
    slots=(
        ExaminationSlot.query.filter(
            ExaminationSlot.examination_id.in_(examination_ids), 
            ExaminationSlot.status.notin_(["Cancelled","Completed"])
            
        ).order_by(ExaminationSlot.date,ExaminationSlot.start_time).all()


        if examinations
        else []
    )

    slots_by_exam={}

    for slot in slots:
        slots_by_exam.setdefault(slot.examination_id,[]).append(slot)

    # stu booking 
    bookings=(
        Booking.query.filter_by(student_id=current_user.id).order_by(Booking.created_at.desc()).all()
    )



    Upcoming_bookings=[booking for booking in bookings
                       if booking.status !="Booked"
                       or booking.slot.date >= datetime.now().date()
                       ]
    # boking history 

    history_bookings=[booking for booking in bookings
                       if booking.status !="Booked"
                       or booking.slot.date < datetime.now().date()
                       ]

    # result 
    published_results=[booking for booking in bookings
                       if booking.evaluation and booking.evaluation.is_published
                       ]


    # Active Courses 
    courses=(
        Course.query.filter_by(status="Active").order_by(Course.course_name).all()

    )

    return render_template(
    "student/dashboard.html",
    student=current_user,
    examinations=examinations,
    slots_by_exam=slots_by_exam,
    bookings=bookings,
    upcoming_bookings=Upcoming_bookings,
    history_bookings=history_bookings,
    published_results=published_results,
    courses=courses,
    search=search,
    selected_course=course_id,
    selected_type=examination_type,

)
            

        
@student_bp.route("/profile", methods=["POST"])
@role_required("Student")
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

    return redirect(url_for("student.dashboard"))


@student_bp.route("/slots/<int:slot_id>/book", methods=["POST"])
@role_required("Student")
def book_slot(slot_id, current_user):

    slot = ExaminationSlot.query.filter_by(
        id=slot_id,
    ).first_or_404()

    examination=slot.examination

    # is booking open 
    if _booking_open(examination):
        flash("Booking is not open for this examination","warning")
        return redirect(url_for("student.dashboard"))

    # slot avialbe ? 
    if slot.status != "Available" or slot.available_seats <= 0:
        flash("Slot is not  Available/Full","danger")
        return redirect(url_for("student.dashboard"))

 


    # prevent duplicate booking 
    duplicate=(
        Booking.query.join(ExaminationSlot).filter(
            Booking.student_id == current_user.id,
            Booking.status=="Booking",
            ExaminationSlot.examination_id==ExaminationSlot
        ).first()
    )

    if duplicate:
        flash("You have already booked for this exam","danger")
        return redirect(url_for("student.dashboard"))


    # create new booking 
    booking=Booking(
        student_id=current_user.id,
        slot_id=slot.id,
        status="Booked"
    )

    # Decrease available seats
    slot.available_seats -= 1


    db.session.add(booking)

    if slot.available_seats == 0:
        slot.status="Full"



    db.session.commit()

    flash("Examination slot updated successfully!", "success")

    return redirect(url_for("student.dashboard"))




@student_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role_required("Student")
def cancel_booking(booking_id, current_user):

 
    booking = Booking.query.filter_by(
        id=booking_id,
        student_id=current_user.id
    ).first_or_404()

    slot = booking.slot
    examination = slot.examination

    if booking.status != "Booked":
        flash("Only booked slots can be cancelled.", "warning")
        return redirect(url_for("student.dashboard"))

     
    if datetime.now() > examination.slot_booking_end:
        flash("Booking cancellation deadline has passed.", "danger")
        return redirect(url_for("student.dashboard"))

    
    booking.status = "Cancelled"

    
    slot.available_seats += 1


 
    if slot.status == "Full":
        slot.status = "Available"


    db.session.commit()

    flash("Booking cancelled successfully!", "success")

    return redirect(url_for("student.dashboard"))

 