from sqlalchemy.orm import Mapped

from db import db
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime, timezone

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from db import db





class Timestamp:
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc)
    )

class BaseModel(Timestamp,db.Model):
    __abstract__=True
    id = db.Column(
            db.Integer,
            primary_key=True
        )
    




class User(BaseModel):

    __tablename__ = "users"

    

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(200),
        nullable=False,
        unique=True,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # Allowed roles: Admin, Examiner, Student.
    role = db.Column(
        db.String(20),
        nullable=False
    )

    # Account approval and activation status.
    status = db.Column(
        db.String(20),
        nullable=False,
        default="Pending"
    )

    phone = db.Column(
        db.String(15),
        nullable=True,
        unique=True
    )


 
    # One User can have at most one ExaminerProfile.
    examiner_profile = db.relationship(
        "ExaminerProfile",
        back_populates ="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # A student can have multiple bookings.
    bookings = db.relationship(
        "Booking",
        back_populates="student",
        foreign_keys="Booking.student_id"
    )

    # An examiner can create multiple examination slots.
    examination_slots = db.relationship(
        "ExaminationSlot",
        back_populates="examiner",
        foreign_keys="ExaminationSlot.examiner_id"
    )

    # Evaluations submitted by this user as an examiner.
    evaluations = db.relationship(
        "Evaluation",
        back_populates="examiner",
        foreign_keys="Evaluation.examiner_id"
    )

 
    __table_args__ = (

        db.CheckConstraint(
            "role IN ('Admin', 'Examiner', 'Student')",
            name="check_user_role"
        ),

        db.CheckConstraint(
            "status IN "
            "('Pending', 'Approved', 'Deactivated', 'Blocked')",
            name="check_user_status"
        ),

    )

 
    def set_password(self, password):
 
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
 
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"<User {self.email} - {self.role}>"




class ExaminerProfile(BaseModel):

    __tablename__ = "examiner_profiles"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    department = db.Column(
        db.String(100),
        nullable=False
    )

    designation = db.Column(
        db.String(100),
        nullable=False
    )

    employee_id = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )

    qualification = db.Column(
        db.String(150),
        nullable=True
    )

    user = db.relationship(
        "User",
        back_populates="examiner_profile"
    )

    def __repr__(self):
        return (
            f"<ExaminerProfile "
            f"{self.employee_id} - {self.department}>"
        )




class Course(BaseModel):

    __tablename__ = "courses"
 

    course_code = db.Column(
        db.String(30),
        nullable=False,
        unique=True
    )

    course_name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Active"
    )



    examinations = db.relationship(
        "Examination",
        back_populates="course"
    )

    __table_args__ = (

        db.CheckConstraint(
            "status IN ('Active', 'Inactive')",
            name="check_course_status"
        ),

    )

    def __repr__(self):
        return (
            f"<Course {self.course_code} - {self.course_name}>"
        )




class Examination(BaseModel):

    __tablename__ = "examinations"
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id"),
        nullable=False,
        index=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    examination_type = db.Column(
        db.String(30),
        nullable=False
    )

    duration_in_minutes = db.Column(
        db.Integer,
        nullable=False
    )

    maximum_marks = db.Column(
        db.Float,
        nullable=False
    )

    slot_creation_start = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    slot_creation_end = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    slot_booking_start = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    slot_booking_end = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    slot_creation_open= db.Column(
        db.Boolean,
        nullable=False,
        default=False)

    
    booking_open= db.Column(
        db.Boolean,
        nullable=False,
        default=False)



    status = db.Column(
        db.String(30),
        nullable=False,
        default="Draft"
    )

 

    course = db.relationship(
        "Course",
        back_populates="examinations"
    )

    rubrics = db.relationship(
        "ExaminationRubric",
        back_populates="examination",
        cascade="all, delete-orphan"
    )

    slots = db.relationship(
        "ExaminationSlot",
        back_populates="examination"
    )

    __table_args__ = (

        db.CheckConstraint(
            "examination_type IN "
            "('Viva', 'Practical', 'Project Demo', 'Assessment')",
            name="check_examination_type"
        ),

        db.CheckConstraint(
            "duration_in_minutes > 0",
            name="check_examination_duration"
        ),

        db.CheckConstraint(
            "maximum_marks > 0",
            name="check_examination_maximum_marks"
        ),

        db.CheckConstraint(
            "status IN "
            "('Draft', 'Slot Creation', 'Booking Open', "
            "'Closed', 'Completed', 'Cancelled')",
            name="check_examination_status"
        ),

        db.CheckConstraint(
            "slot_creation_start IS NULL "
            "OR slot_creation_end IS NULL "
            "OR slot_creation_start <= slot_creation_end",
            name="check_slot_creation_dates"
        ),

        db.CheckConstraint(
            "slot_booking_start IS NULL "
            "OR slot_booking_end IS NULL "
            "OR slot_booking_start <= slot_booking_end",
            name="check_slot_booking_dates"
        ),

    )

    def __repr__(self):
        return f"<Examination {self.name}>"



class ExaminationRubric(BaseModel):
    __tablename__ = "examination_rubrics"

    # Each rubric belongs to one examination.
    examination_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    criterion_name = db.Column(
        db.String(150),
        nullable=False
                )

    maximum_marks = db.Column(
        db.Float,
        nullable=False
    )

    # Percentage weight assigned to this criterion.
    weightage = db.Column(
        db.Float,
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    examination = db.relationship(
        "Examination",
        back_populates="rubrics"
    )

    # Marks awarded for this criterion in different evaluations.
    evaluation_details = db.relationship(
        "EvaluationDetail",
        back_populates="rubric"  # Fixed from "rubrics" to "rubric"
    )

    __table_args__ = (
        db.CheckConstraint(
            "maximum_marks > 0",
            name="check_rubric_maximum_marks"
        ),
        db.CheckConstraint(
            "weightage >= 0 AND weightage <= 100",
            name="check_rubric_weightage"
        ),
    )

    def __repr__(self):
        return f"<ExaminationRubric {self.criterion_name} - {self.maximum_marks}>"


class ExaminationSlot(BaseModel):

    __tablename__ = "examination_slots"
 
    examination_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.id"),
        nullable=False,
        index=True
    )

    examiner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    maximum_capacity = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Available"
    )

    meeting_link = db.Column(
        db.String(500),
        nullable=True
    )
 


    examination = db.relationship(
        "Examination",
        back_populates="slots"
    )

    examiner = db.relationship(
        "User",
        back_populates="examination_slots",
        foreign_keys=[examiner_id]
    )

    bookings = db.relationship(
        "Booking",
        back_populates="slot"
    )

    __table_args__ = (

        db.CheckConstraint(
            "maximum_capacity > 0",
            name="check_slot_capacity"
        ),

        db.CheckConstraint(
            "start_time < end_time",
            name="check_slot_time"
        ),

        db.CheckConstraint(
            "status IN "
            "('Available', 'Full', 'Cancelled', 'Completed')",
            name="check_slot_status"
        ),

    )

    @property
    def booked_seats(self):
       

        return sum(
            1
            for booking in self.bookings
            if booking.status == "Booked"
        )

    @property
    def available_seats(self):
        """Calculate remaining capacity."""

        return max(
            0,
            self.maximum_capacity - self.booked_seats
        )

    def __repr__(self):
        return f"<ExaminationSlot {self.id} - {self.date} {self.start_time}>"



class Booking(BaseModel):

    __tablename__ = "bookings"
 

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    slot_id = db.Column(
        db.Integer,
        db.ForeignKey("examination_slots.id"),
        nullable=False,
        index=True
    )

    booking_date = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Booked"
    )

    student = db.relationship(
        "User",
        back_populates="bookings",
        foreign_keys=[student_id]
    )

    slot = db.relationship(
        "ExaminationSlot",
        back_populates="bookings"
    )

    evaluation = db.relationship(
        "Evaluation",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (

        db.CheckConstraint(
            "status IN ('Booked', 'Cancelled', 'Completed')",
            name="check_booking_status"
        ),

    )

    def __repr__(self):
        return f"<Booking {self.id} - {self.status}>"




class Evaluation(BaseModel):

    __tablename__ = "evaluations"
   
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id"),
        nullable=False,
        unique=True

    )

   
    examiner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )
    total_marks = db.Column(
            db.Float,
            nullable=False,
           
        )
    
    remarks = db.Column(
            db.Text,
            nullable=True
        )
    
    is_published = db.Column(
            db.Boolean,
            nullable=False,
            default=False
        )
    evaluated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    booking = db.relationship(
        "Booking",
        back_populates="evaluation"
    )   
    examiner = db.relationship(
        "User",
        back_populates="evaluations",
        foreign_keys=[examiner_id]
    )    
    details= db.relationship(
        "EvaluationDetail",
        back_populates="evaluation",cascade="all, delete-orphan"
    )   



#updated Bug fix

class EvaluationDetail(BaseModel):
    __tablename__ = "evaluation_details"

    evaluation_id = db.Column(
        db.Integer,
        db.ForeignKey("evaluations.id"),
        nullable=False
    )

    rubric_id = db.Column(
        db.Integer,
        db.ForeignKey("examination_rubrics.id"),
        nullable=False
    )

    marks_awarded = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    evaluation = db.relationship(
        "Evaluation",
        back_populates="details"
    )

    rubric = db.relationship(
        "ExaminationRubric",
        back_populates="evaluation_details"
    )
 #     