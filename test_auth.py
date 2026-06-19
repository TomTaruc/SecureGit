import urllib.request
import json

req = urllib.request.Request("http://localhost:5000/internal/ssh-auth", 
    data=json.dumps({"user_id": 1, "owner": "testuser", "project_name": "sshtest-449119798", "action": "write"}).encode(),
    headers={"X-Hook-Secret": "hook-secret-change", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(e.read().decode())
