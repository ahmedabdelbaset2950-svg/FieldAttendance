from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from utils import role_required
from app.models import User, Movement, SystemSetting # تأكد إن SystemSetting موجودة هنا
from datetime import date, datetime
import os
from secrets import token_hex
import io
from sqlalchemy import extract
from flask import Blueprint, flash, render_template, request, redirect, current_app, send_file, url_for
from flask import Blueprint, render_template, request, redirect, current_app, send_file
from flask_login import current_user, login_required
import pandas as pd
from werkzeug.security import generate_password_hash
from app import db
from app.models import Engineer, Movement
import shutil
from flask import send_file
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from sqlalchemy import func


main = Blueprint("main", __name__)

def save_picture(form_picture):
    random_hex = token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static', 'profile_pics', picture_fn)
    form_picture.save(picture_path)
    return picture_fn

@main.route("/")
@login_required
def index():
    total_engineers = Engineer.query.count()
    on_site = Engineer.query.filter_by(current_status="On Site").count()
    off_site = Engineer.query.filter_by(current_status="Off Site").count()
    leave = Engineer.query.filter_by(current_status="Leave").count()
    warning = sum(1 for e in Engineer.query.all() if e.shift_alert == "Warning")
    extended = sum(1 for e in Engineer.query.all() if e.shift_alert == "Extended")
    recent_movements = Movement.query.order_by(Movement.id.desc()).limit(10).all()
    return render_template(
        "index.html",
        total_engineers=total_engineers,
        on_site=on_site,
        off_site=off_site,
        leave=leave,
        warning=warning,
        extended=extended,
        recent_movements=recent_movements
    )

@main.route("/dashboard")
@login_required
def dashboard():
    return redirect("/")

@main.route("/engineers")
@login_required
def engineers():
    search = request.args.get("search", "").strip()
    query = Engineer.query
    if search:
        query = query.filter((Engineer.employee_id.ilike(f"%{search}%")) | (Engineer.full_name.ilike(f"%{search}%")) | (Engineer.position.ilike(f"%{search}%")))
    engineers = query.order_by(Engineer.full_name).all()
    calculated_days = {}
    for engineer in engineers:
        if engineer.current_status == "On Site" and getattr(engineer, 'check_in_date', None):
            days = (date.today() - engineer.check_in_date).days + 1
            formatted_date = engineer.check_in_date.strftime("%d-%m-%Y")
            calculated_days[engineer.id] = {"days": f"{days} Days", "start_date": f"Started: {formatted_date}"}
        else:
            calculated_days[engineer.id] = {"days": "-", "start_date": ""}
    return render_template("engineers.html", engineers=engineers, calculated_days=calculated_days, search=search)

@main.route("/engineer/<int:id>")
@login_required
def engineer_profile(id):
    engineer = Engineer.query.get_or_404(id)
    profile_days = "-"
    if engineer.current_status == "On Site" and getattr(engineer, 'check_in_date', None):
        profile_days = (date.today() - engineer.check_in_date).days + 1
    movements = Movement.query.filter_by(engineer_id=id).order_by(Movement.id.desc()).all()
    return render_template("engineer_profile.html", engineer=engineer, profile_days=profile_days, movements=movements)

@main.route("/add_engineer", methods=["GET", "POST"])
@login_required
@role_required(['Admin', 'Manager'])
def add_engineer():
    if request.method == "POST":
        employee_id = request.form["employee_id"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()
        email = email if email else None
        phone = phone if phone else None
        if Engineer.query.filter_by(employee_id=employee_id).first():
            return render_template("add_engineer.html", error="Employee ID already exists!")
        if phone and Engineer.query.filter_by(phone=phone).first():
            return render_template("add_engineer.html", error="Phone number already exists!")
        if email and Engineer.query.filter_by(email=email).first():
            return render_template("add_engineer.html", error="Email already exists!")
        current_status = request.form["current_status"]
        check_in_date = date.today() if current_status == "On Site" else None
        profile_image = 'default.png'
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                profile_image = save_picture(file)
        engineer = Engineer(employee_id=employee_id, full_name=request.form["full_name"], phone=phone, email=email, company=request.form["company"], department=request.form["department"], position=request.form["position"], supervisor=request.form["supervisor"], field_name=request.form["field_name"], location=request.form["location"], rotation=request.form["rotation"], current_status=current_status, check_in_date=check_in_date, profile_image=profile_image)
        db.session.add(engineer)
        db.session.commit()
        return redirect("/engineers")
    return render_template("add_engineer.html")
def add_engineer():
    query = filter_movements_query(Movement.query)
    movements = query.order_by(Movement.id.desc()).all()
    
   # داخل دالة export_excel، قم بتعديل حلقة الـ for كالتالي:

    data = []
    for mv in movements:
        data.append({
            "Month": mv.movement_date.strftime("%B") if mv.movement_date else "-", # إضافة عمود الشهر
            "Engineer Name": mv.engineer.full_name,
            "Action Type": mv.action,
            "Date": mv.movement_date.strftime("%Y-%m-%d") if mv.movement_date else "-",
            "Days on Site": mv.days_on_site if mv.days_on_site else "-",
            "Start Shift": mv.engineer.start_shift.strftime("%Y-%m-%d") if mv.engineer.start_shift else "-",
            "Check-out": mv.engineer.check_out_date.strftime("%Y-%m-%d") if mv.engineer.check_out_date else "-",
            "Reason": mv.reason or "-",
            "Notes": mv.notes or "-"
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Report', startrow=6)
        
        workbook = writer.book
        worksheet = writer.sheets['Report']
        
        # التنسيقات
        title_format = workbook.add_format({'bold': True, 'font_size': 16, 'bg_color': '#1F4E79', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#34495E', 'font_color': 'white', 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        # 1. العنوان (أخذ العرض كامل من A إلى H)
        worksheet.merge_range('A1:I2', 'FIELD ATTENDANCE REPORT', title_format)
        
        # 2. جعل الجدول يأخذ عرض الشيت بالكامل (توزيع الأعمدة)
        # تحديد عرض ثابت للأعمدة لملء الشيت
        worksheet.set_column('A:I', 16, cell_format)
        
        # 3. تنسيق الهيدر
        for idx, col in enumerate(df.columns):
            worksheet.write(6, idx, col, header_format)

    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                     as_attachment=True, download_name=f"Report_{date.today().strftime('%Y-%m-%d')}.xlsx")

@main.route("/edit_engineer/<int:id>", methods=["GET", "POST"])
@login_required
@role_required(['Admin', 'Manager'])
def edit_engineer(id):
    engineer = Engineer.query.get_or_404(id)
    if request.method == "POST":
        employee_id = request.form["employee_id"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()
        email = email if email else None
        phone = phone if phone else None
        exist = Engineer.query.filter(Engineer.employee_id == employee_id, Engineer.id != engineer.id).first()
        if exist:
            return render_template("edit_engineer.html", engineer=engineer, error="Employee ID already exists!")
        if phone:
            exist = Engineer.query.filter(Engineer.phone == phone, Engineer.id != engineer.id).first()
            if exist:
                return render_template("edit_engineer.html", engineer=engineer, error="Phone already exists!")
        if email:
            exist = Engineer.query.filter(Engineer.email == email, Engineer.id != engineer.id).first()
            if exist:
                return render_template("edit_engineer.html", engineer=engineer, error="Email already exists!")
        old_status = engineer.current_status
        new_status = request.form["current_status"]
        if old_status != "On Site" and new_status == "On Site":
            engineer.check_in_date = date.today()
            engineer.check_out_date = None
        elif new_status != "On Site":
            engineer.check_in_date = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                if engineer.profile_image != 'default.png':
                    old_picture_path = os.path.join(current_app.root_path, 'static', 'profile_pics', engineer.profile_image)
                    if os.path.exists(old_picture_path):
                        os.remove(old_picture_path)
                engineer.profile_image = save_picture(file)
        engineer.employee_id = employee_id
        engineer.full_name = request.form["full_name"]
        engineer.phone = phone
        engineer.email = email
        engineer.company = request.form["company"]
        engineer.department = request.form["department"]
        engineer.position = request.form["position"]
        engineer.supervisor = request.form["supervisor"]
        engineer.field_name = request.form["field_name"]
        engineer.location = request.form["location"]
        engineer.rotation = request.form["rotation"]
        engineer.current_status = new_status
        db.session.commit()
        return redirect("/engineers")
    return render_template("edit_engineer.html", engineer=engineer)

@main.route("/delete_engineer/<int:id>")
@login_required
@role_required(['Admin', 'Manager'])
def delete_engineer(id):
    engineer = Engineer.query.get_or_404(id)
    if engineer.profile_image != 'default.png':
        picture_path = os.path.join(current_app.root_path, 'static', 'profile_pics', engineer.profile_image)
        if os.path.exists(picture_path):
            os.remove(picture_path)
    Movement.query.filter_by(engineer_id=engineer.id).delete()
    db.session.delete(engineer)
    db.session.commit()
    return redirect("/engineers")

@main.route("/check_out/<int:id>", methods=["GET", "POST"])
@login_required
@role_required(['Admin', 'Manager'])
def check_out(id):
    engineer = Engineer.query.get_or_404(id)
    actual_days = 0
    if engineer.check_in_date:
        actual_days = (date.today() - engineer.check_in_date).days + 1
    if request.method == "POST":
        movement = Movement(engineer_id=engineer.id, action="Check Out", reason=request.form["reason"], notes=request.form["notes"], days_on_site=actual_days)
        db.session.add(movement)
        engineer.current_status = "Off Site"
        engineer.check_out_date = date.today()
        engineer.check_in_date = None
        db.session.commit()
        return redirect("/engineers")
    return render_template("check_out.html", engineer=engineer)

@main.route("/movements")
@login_required
def movements():
    movements = Movement.query.order_by(Movement.id.desc()).all()
    return render_template("movements.html", movements=movements)

@main.route("/check_in/<int:id>")
@login_required
@role_required(['Admin', 'Manager'])
def check_in(id):
    engineer = Engineer.query.get_or_404(id)
    if engineer.current_status == "On Site":
        return redirect("/engineers")
    movement = Movement(engineer_id=engineer.id, action="Check In", reason="Return to Site", notes="", days_on_site=1)
    db.session.add(movement)
    engineer.current_status = "On Site"
    engineer.check_in_date = date.today()
    engineer.check_out_date = None
    db.session.commit()
    return redirect("/engineers")

@main.route("/reports", methods=["GET"])
@login_required
def reports():
    engineers_list = Engineer.query.order_by(Engineer.full_name).all()
    engineer_id = request.args.get("engineer_id")
    engineer_id = int(engineer_id) if engineer_id else None
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    query = Movement.query
    if engineer_id:
        query = query.filter(Movement.engineer_id == engineer_id)
    if year:
        query = query.filter(extract('year', Movement.movement_date) == year)
    if month:
        query = query.filter(extract('month', Movement.movement_date) == month)
    movements = query.order_by(Movement.id.desc()).all()
    return render_template("reports.html", engineers=engineers_list, movements=movements, selected_engineer=engineer_id, selected_month=month, selected_year=year)

# دالة مساعدة لفلترة الاستعلام حسب الشهر والسنة
def filter_movements_query(query):
    engineer_id = request.args.get("engineer_id", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if engineer_id:
        query = query.filter(Movement.engineer_id == engineer_id)
    if year:
        query = query.filter(extract('year', Movement.movement_date) == year)
    if month:
        query = query.filter(extract('month', Movement.movement_date) == month)
    return query

@main.route("/export_excel", methods=["GET"])
@login_required
@role_required(['Admin', 'Manager'])
def export_excel():
          query = filter_movements_query(Movement.query)
          movements = query.order_by(Movement.id.desc()).all()
    
          data = []
          for mv in movements: 
              data.append({
            "Engineer Name": mv.engineer.full_name,
            "Action Type": mv.action,
            "Date": mv.movement_date.strftime("%Y-%m-%d") if mv.movement_date else "-",
            "Days on Site": mv.days_on_site if mv.days_on_site else "-",
            "Start Shift": mv.engineer.start_shift.strftime("%Y-%m-%d") if mv.engineer.start_shift else "-",
            "Check-out": mv.engineer.check_out_date.strftime("%Y-%m-%d") if mv.engineer.check_out_date else "-",
            "Reason": mv.reason or "-",
            "Notes": mv.notes or "-"
        })
    
          df = pd.DataFrame(data)
          output = io.BytesIO()
    
          with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
               df.to_excel(writer, index=False, sheet_name='Report', startrow=6)
        
               workbook = writer.book
               worksheet = writer.sheets['Report']
        
        # التنسيقات
               title_format = workbook.add_format({'bold': True, 'font_size': 16, 'bg_color': '#1F4E79', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter'})
               header_format = workbook.add_format({'bold': True, 'bg_color': '#34495E', 'font_color': 'white', 'border': 1, 'align': 'center'})
               cell_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        # 1. العنوان (أخذ العرض كامل من A إلى H)
               worksheet.merge_range('A1:H2', 'FIELD ATTENDANCE REPORT', title_format)
        
        # 2. جعل الجدول يأخذ عرض الشيت بالكامل (توزيع الأعمدة)
        # تحديد عرض ثابت للأعمدة لملء الشيت
               worksheet.set_column('A:H', 18, cell_format) 
        
        # 3. تنسيق الهيدر
               for idx, col in enumerate(df.columns):
                worksheet.write(6, idx, col, header_format)

          output.seek(0)
          return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                     as_attachment=True, download_name=f"Report_{date.today().strftime('%Y-%m-%d')}.xlsx")

@main.route("/export_pdf", methods=["GET"])
@login_required
@role_required(['Admin', 'Manager'])
def export_pdf():
    query = filter_movements_query(Movement.query)
    movements = query.order_by(Movement.id.desc()).all()
    
    buffer = io.BytesIO()
    # استخدام الوضع الأفقي ليتسع لكل البيانات
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    # 1. إضافة عنوان التقرير بنفس ستايل الإكسيل
    title = Paragraph("FIELD ATTENDANCE REPORT", styles['Title'])
    story.append(title)
    story.append(Paragraph("<br/>", styles['Normal'])) 
    
    # 2. تجهيز البيانات (مطابقة لأعمدة الإكسيل)
    table_data = [['Engineer Name', 'Action Type', 'Date', 'Days on Site', 'Start Shift', 'Check-out', 'Reason', 'Notes']]
    for mv in movements:
        table_data.append([
            mv.engineer.full_name,
            mv.action,
            mv.movement_date.strftime("%Y-%m-%d") if mv.movement_date else "-",
            str(mv.days_on_site or 0),
            mv.engineer.start_shift.strftime("%Y-%m-%d") if mv.engineer.start_shift else "-",
            mv.engineer.check_out_date.strftime("%Y-%m-%d") if mv.engineer.check_out_date else "-",
            mv.reason or "-",
            mv.notes or "-"
        ])
    
    # 3. ضبط عرض الأعمدة لتملأ الشيت (حوالي 700 نقطة عرض إجمالي)
    t = Table(table_data, colWidths=[120, 80, 70, 60, 80, 80, 80, 100])
    
    # 4. التنسيق (مطابق لألوان الإكسيل #1F4E79 للهيدر والحدود)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')), # أزرق غامق
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),          # نص أبيض للهيدر
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),                     # توسيط كل شيء
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),          # خط عريض للهيدر
        ('FONTSIZE', (0, 0), (-1, 0), 10),                        # حجم الخط
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),           # خلفية بيضاء للبيانات
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),            # حدود سوداء رفيعة
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),                        # حجم خط البيانات
    ])
    
    t.setStyle(style)
    story.append(t)
    
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"Report_{date.today().strftime('%Y-%m-%d')}.pdf")

@main.route("/delete_movement_from_report/<int:id>")
@login_required
@role_required(['Admin', 'Manager'])  # هنا الحماية: الـ Viewer أو الـ Manager مش هيقدروا يدخلوا هنا
def delete_movement_from_report(id):
    movement = Movement.query.get_or_404(id)
    db.session.delete(movement)
    db.session.commit()
    flash("تم حذف الحركة بنجاح", "success")
    return redirect(url_for('main.reports'))

@main.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        # هنا سنضع منطق تحديث كلمة السر أو بيانات النظام
        flash("Settings updated successfully!", "success")
        return redirect(url_for('main.settings'))
    return render_template("settings.html")

@main.route("/update_password", methods=["POST"])
@login_required
@role_required(['Admin', 'Manager'])
def update_password():
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    
    if new_password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect(url_for('main.settings'))
    
    # تحديث كلمة السر للمستخدم الحالي
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash("Password updated successfully!", "success")
    return redirect(url_for('main.settings'))

@main.context_processor
def inject_settings():
    setting = SystemSetting.query.first()
    return dict(system_setting=setting)

@main.route("/update_system", methods=["POST"])
@login_required
@role_required(['Admin'])
def update_system():
    # كود التحديث هنا
    setting = SystemSetting.query.first() or SystemSetting()
    setting.company_name = request.form.get("company_name")
    setting.system_version = request.form.get("system_version")
    
    db.session.add(setting)
    db.session.commit()
    
    flash("System settings updated!", "success")
    return redirect(url_for('main.settings'))

@main.route("/backup_db")
@login_required
@role_required(['Admin'])
def backup_db():
    # مسار قاعدة البيانات (عدل المسار حسب مكان ملف الـ db عندك)
    db_path = os.path.join(current_app.instance_path, 'database.db')
    
    # التأكد من وجود الملف
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True)
    else:
        flash("Database file not found!", "danger")
        return redirect(url_for('main.settings'))
@main.route("/users")
@login_required
def users():
    # لازم تتأكد إنك بتجيب كل المستخدمين من قاعدة البيانات
    all_users = User.query.all()
    return render_template("users.html", users=all_users)



from utils import role_required # استدعينا الحارس اللي عملناه

@main.route("/users")
@login_required
@role_required(['Admin']) # الأدمن فقط اللي يشوف صفحة اليوزرز
def manage_users():
    users = User.query.all()
    return render_template("users.html", users=users)


@main.route("/update_role/<int:user_id>", methods=["POST"])
@login_required
@role_required(['Admin'])
def update_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    user.role = new_role
    db.session.commit()
    flash(f"تم تحديث صلاحية {user.full_name} إلى {new_role}", "success")
    return redirect(url_for('main.manage_users'))

@main.route("/add_user", methods=["GET", "POST"])
@login_required
@role_required(['Admin']) # أنت فقط كأدمن تقدر تضيف مستخدمين
def add_user():
    if request.method == "POST":
        
        # في دالة add_user
        username = request.form.get("username").strip() # إضافة .strip() هنا ضرورية جداً
        full_name = request.form.get("full_name").strip()
        password = request.form.get("password")
        role = request.form.get("role")
        # في دالة الإضافة في routes.py
        new_user = User(username=username, full_name=full_name, role=role, is_active=True)
        # إنشاء المستخدم الجديد
        new_user = User(username=username, full_name=full_name, role=role)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f"تم إضافة المستخدم {full_name} بنجاح!", "success")
        return redirect(url_for('main.manage_users'))
        
    return render_template("add_user.html")

@main.route("/delete_user/<int:user_id>")
@login_required
@role_required(['Admin'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    # منع حذف الأدمن الحالي
    if user.username == current_user.username:
        flash("لا يمكنك حذف حسابك الحالي!", "danger")
        return redirect(url_for('main.manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f"تم حذف المستخدم {user.full_name} بنجاح", "success")
    return redirect(url_for('main.manage_users'))

@main.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
@login_required
@role_required(['Admin'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        user.full_name = request.form.get("full_name")
        user.username = request.form.get("username")
        new_password = request.form.get("password")
        if new_password:
            user.set_password(new_password) # تأكد أن هذه الدالة موجودة في نموذج User
        db.session.commit()
        flash("تم تحديث بيانات المستخدم بنجاح", "success")
        return redirect(url_for('main.manage_users'))
    return render_template("edit_user.html", user=user)

main.route("/archive")
@login_required
@role_required(['Admin', 'Manager'])
def archive():
    # استخراج السنوات المتاحة من جدول الحركات
    years = db.session.query(func.strftime('%Y', Movement.movement_date).label('year')) \
                      .distinct().order_by(func.strftime('%Y', Movement.movement_date).desc()).all()
    return render_template("archive.html", years=years)


@main.route("/archive")
@login_required
@role_required(['Admin', 'Manager'])
def archive():
    # استخراج السنوات المتاحة من جدول الحركات
    years = db.session.query(func.strftime('%Y', Movement.movement_date).label('year')) \
                      .distinct().order_by(func.strftime('%Y', Movement.movement_date).desc()).all()
    return render_template("archive.html", years=years)

@main.route("/archive/<year>")
@login_required
@role_required(['Admin', 'Manager'])
def archive_year(year):
    # استخراج الشهور المتاحة لسنة محددة
    months = db.session.query(func.strftime('%m', Movement.movement_date).label('month')) \
                      .filter(func.strftime('%Y', Movement.movement_date) == year) \
                      .distinct().order_by(func.strftime('%m', Movement.movement_date).desc()).all()
    return render_template("archive_months.html", year=year, months=months)