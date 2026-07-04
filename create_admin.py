from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():

    username = "Ahmed"

    user = User.query.filter_by(username=username).first()

    if user:
        print("Admin already exists.")
    else:
        admin = User(
            username="Ahmed",
            full_name="Ahmed Mohamed Abdel Baset",
            role="Admin"
        )

        admin.set_password("Ahmed@2026")

        db.session.add(admin)
        db.session.commit()

        print("Admin user created successfully.")