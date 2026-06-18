from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User

app = create_app()
with app.app_context():
    if not User.query.filter_by(username='motaruc@gmail.com').first():
        user = User(username='motaruc@gmail.com', email='motaruc@gmail.com', password_hash=bcrypt.generate_password_hash('password').decode('utf-8'), role='admin')
        db.session.add(user)
        db.session.commit()
        print("User created")
    else:
        print("User already exists")
