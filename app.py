from flask import Flask, redirect, url_for
from config.config import Config
from db import db
from seed_data import create_admin,seed_data
from routes.auth_bp import auth_bp
from routes.admin_bp import admin_bp
from routes.examiner_bp import examiner_bp
from routes.student_bp import student_bp

app = Flask(__name__)

app.config.from_object(Config)
db.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(examiner_bp)
app.register_blueprint(student_bp)


@app.route("/")
def home():
    return redirect(url_for("auth.register"))


@app.route("/register")
def register_page():
    return redirect(url_for("auth.register"))


@app.route("/login")
def login_page():
    return redirect(url_for("auth.login"))


with app.app_context():
    from models import *
    db.create_all()
    create_admin()
    seed_data()


if __name__ == "__main__":
    app.run(debug=True)
