from functools import wraps

from flask import flash, redirect, session, url_for

from db import db
from models import User


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user_id = session.get("user_id")
            if session.get("role") != role or not user_id:
                return redirect(url_for("auth.login"))

            user = db.session.get(User, user_id)
            if not user or user.role != role or user.status != "Approved":
                session.clear()
                flash(f"Your {role.lower()} account is not approved. Please contact the administrator.", "warning")
                return redirect(url_for("auth.login"))

            return view(*args, current_user=user, **kwargs)

        return wrapper

    return decorator