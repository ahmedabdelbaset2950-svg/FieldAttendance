from functools import wraps
from flask import abort
from flask_login import current_user
from flask import render_template # اتأكد إنك عملت Import للـ render_template هنا
from functools import wraps
from flask_login import current_user

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # التأكد من الصلاحية
            if current_user.role not in roles:
                # التعديل هنا:
                return render_template("403.html"), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator