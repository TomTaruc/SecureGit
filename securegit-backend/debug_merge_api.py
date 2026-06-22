import json
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
    
    print("=== 1. Branches API (Frontend Merge dropdown source) ===")
    resp = client.get('/api/branches/user1/dandannn22', headers=headers)
    branches = resp.get_json()
    print([b['name'] for b in branches])
    
    print("\n=== 2. Compare Branches (feature-test -> master) ===")
    resp = client.get('/api/merge/user1/dandannn22/compare?base=master&head=feature-test', headers=headers)
    compare_data = resp.get_json()
    print("Commits:")
    for c in compare_data.get('commits', []):
        print(f"  - {c['short_hash']} {c['message']}")
    print("Diff:")
    for d in compare_data.get('diff', []):
        print(f"  {d.get('status', 'M')} {d.get('new_path', d.get('path', 'unknown'))}")
        
    print("\n=== 3. Execute Merge ===")
    resp = client.post('/api/merge/user1/dandannn22/merge', headers=headers, json={
        "base": "master",
        "head": "feature-test",
        "strategy": "ff",
        "message": "Merge feature-test into master"
    })
    print("Merge Status:", resp.status_code)
    print("Merge Response:", resp.get_json())
    
    print("\n=== 4. Verify Master Branch Commits ===")
    resp = client.get('/api/commits/user1/dandannn22?branch=master', headers=headers)
    commits = resp.get_json().get('commits', [])
    for c in commits:
        print(f"  - {c['short_hash']} {c['message']}")
