from datetime import datetime

from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_user, logout_user, current_user

from app import db
from app.models import User

# إنشاء الـ Blueprint
auth = Blueprint("auth", __name__)


# =========================
# Login
# =========================
@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        # تعديل: نجرب نجيب اليوزر بالاسم فقط الأول ونشوف النتيجة
        user = User.query.filter_by(username=username).first()
        
        print(f"--- DEBUGGING ---")
        print(f"Searching for username: '{username}'")
        
        if user:
            print(f"User found: {user.username}, Is Active: {user.is_active}")
            # دلوقتي نشيك على الـ active
            if not user.is_active:
                print("User exists but is_active is False!")
        else:
            print("User NOT found in database.")
            # نطبع كل اليوزرات عشان نشوف مكتوبين إزاي
            all_users = User.query.all()
            for u in all_users:
                print(f"Existing user: '{u.username}'")

        if user and user.is_active and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return redirect("/")

        flash("Invalid username or password.", "danger")
    return render_template("login.html")

# =========================
# Logout
# =========================
@auth.route("/logout")
def logout():

    logout_user()

    return redirect("/login")