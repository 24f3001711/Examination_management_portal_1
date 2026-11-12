from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from db import db
from models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/")
def home():
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        if user.status != "Approved":
            flash("Your account is pending or inactive. Please wait for approval.", "warning")
            return redirect(url_for("auth.login"))

        session["user_id"] = user.id
        session["role"] = user.role
        session["name"] = user.name

        if user.role == "Admin":
            return redirect(url_for("admin.dashboard"))
        if user.role == "Examiner":
            return redirect(url_for("examiner.dashboard"))
        if user.role == "Student":
            return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password")
        phone = request.form.get("phone", "").strip() or None
        role = request.form.get("role")

        if not name or not email or not password:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("auth.register"))

        if role not in ["Student", "Examiner"]:
            flash("Please select a valid role.", "danger")
            return redirect(url_for("auth.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists. Try logging in instead.", "danger")
            return redirect(url_for("auth.register"))
        if phone and User.query.filter_by(phone=phone).first():
            flash("That phone number is already in use.", "danger")
            return redirect(url_for("auth.register"))

        user = User(
            name=name,
            email=email,
            role=role,
            phone=phone,
            status="Pending" if role == "Examiner" else "Approved"
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        if role == "Examiner":
            flash("Registration submitted successfully. Please wait for admin approval.", "success")
        else:
            flash("Registration successful. Please log in to continue.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Successfully logged out")
    return redirect(url_for("auth.login"))

 