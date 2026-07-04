from datetime import date, datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# =====================================================
# Engineer Model
# =====================================================
class Engineer(db.Model):
    __tablename__ = "engineers"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    company = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    supervisor = db.Column(db.String(120), nullable=True)
    field_name = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    rotation = db.Column(db.String(50), nullable=True)
    current_status = db.Column(db.String(50), default="Off Site")
    check_in_date = db.Column(db.Date, nullable=True)
    check_out_date = db.Column(db.Date, nullable=True)
    start_shift = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, default=True)
    profile_image = db.Column(db.String(100), nullable=False, default='default.png')

    @property
    def days_on_site(self):
        if self.current_status == "On Site" and self.check_in_date:
            return (date.today() - self.check_in_date).days + 1
        return 0

    @property
    def shift_alert(self):
        if self.current_status != "On Site":
            return ""
        if self.days_on_site >= 28:
            return "Extended"
        if self.days_on_site >= 21:
            return "Warning"
        return ""

    def __repr__(self):
        return self.full_name

# =====================================================
# Movement Model
# =====================================================
class Movement(db.Model):
    __tablename__ = "movements"
    id = db.Column(db.Integer, primary_key=True)
    engineer_id = db.Column(db.Integer, db.ForeignKey("engineers.id"), nullable=False)
    action = db.Column(db.String(20))
    movement_date = db.Column(db.Date, default=date.today)
    reason = db.Column(db.String(100))
    notes = db.Column(db.Text)
    days_on_site = db.Column(db.Integer)

    engineer = db.relationship("Engineer", backref=db.backref("movements", cascade="all, delete-orphan"))

# =====================================================
# User Model (تم تحديث الأدوار)
# =====================================================
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # الأدوار: 'Admin' (أنت), 'Manager' (صلاحيات تصدير وإضافة), 'Viewer' (اطلاع فقط)
    role = db.Column(db.String(20), default="Viewer") 
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# =====================================================
# System Settings Model
# =====================================================
class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), default="Royal Wells Alliance")
    system_version = db.Column(db.String(20), default="1.0.0")