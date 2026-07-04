from app import create_app
from app.models import User

app = create_app()

with app.app_context():

    users = User.query.all()

    print("Users Count:", len(users))

    for user in users:
        print("----------------------")
        print("Username :", user.username)
        print("Active   :", user.is_active)
        print("Role     :", user.role)
        print("Password OK:", user.check_password("Ahmed@2026"))