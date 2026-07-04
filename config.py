import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = "Ahmed@2026_FieldAttendance"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "attendance.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False