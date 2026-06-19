from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='user1').first()
    if not user:
        print("User user1 not found")
        exit(1)
        
    token = create_access_token(identity=str(user.user_id))
    client = app.test_client()
    headers = {'Authorization': f'Bearer {token}'}
    
    print("--- API: README ---")
    resp = client.get('/api/repos/user1/dandannn22/readme?branch=master', headers=headers)
    print(resp.get_data(as_text=True))
