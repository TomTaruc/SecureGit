import os, time, subprocess, requests, tempfile, shutil

BASE_URL = "http://localhost:5000/api"

def run_cmd(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)

print("Setting up SSH verification environment...")

owner = f"owner_{int(time.time())}"
reader = f"reader_{int(time.time())}"
writer = f"writer_{int(time.time())}"
admin = f"admin_{int(time.time())}"
pwd = "SecurePass123"

owner_session = requests.Session()
reader_session = requests.Session()
writer_session = requests.Session()
admin_session = requests.Session()

print("Creating users...")
for u, s in [(owner, owner_session), (reader, reader_session), (writer, writer_session), (admin, admin_session)]:
    s.post(f"{BASE_URL}/auth/register", json={"username": u, "email": f"{u}@test.com", "password": pwd}).raise_for_status()
    s.post(f"{BASE_URL}/auth/login", json={"username": u, "password": pwd}).raise_for_status()

print("Generating keys...")
key_dir = tempfile.mkdtemp()
keys = {"owner": owner, "readonly": reader, "write": writer, "admin": admin, "unknown": "unknown"}
key_paths = {}

for role, user in keys.items():
    kp = os.path.join(key_dir, f"{role}_key")
    key_paths[role] = kp
    run_cmd(["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", kp, "-N", ""])
    if role != "unknown":
        with open(f"{kp}.pub", "r") as f:
            pub_key = f.read().strip()
        if role == "owner": s = owner_session
        elif role == "readonly": s = reader_session
        elif role == "write": s = writer_session
        elif role == "admin": s = admin_session
        
        s.post(f"{BASE_URL}/ssh-keys", json={"title": f"{role}_key", "public_key": pub_key}).raise_for_status()

print("Creating repo...")
repo_name = "test-repo"
owner_session.post(f"{BASE_URL}/projects", json={"project_name": repo_name, "description": "Test", "visibility": "public"}).raise_for_status()

print("Adding collaborators...")
for u, perm in [(reader, "read"), (writer, "write"), (admin, "admin")]:
    uid = owner_session.get(f"{BASE_URL}/users/search?q={u}").json()[0]["user_id"]
    owner_session.post(f"{BASE_URL}/projects/{owner}/{repo_name}/collaborators", json={"user_id": uid, "permission": perm}).raise_for_status()

print("Initializing git repo and pushing initial commit...")
repo_dir = os.path.join(key_dir, "repo")
os.makedirs(repo_dir)
run_cmd(["git", "init"], cwd=repo_dir)
run_cmd(["git", "config", "user.email", "test@test.com"], cwd=repo_dir)
run_cmd(["git", "config", "user.name", "Test"], cwd=repo_dir)
with open(os.path.join(repo_dir, "test.txt"), "w") as f: f.write("Hello")
run_cmd(["git", "add", "."], cwd=repo_dir)
run_cmd(["git", "commit", "-m", "init"], cwd=repo_dir)
run_cmd(["git", "branch", "-M", "main"], cwd=repo_dir)

env = os.environ.copy()
env["GIT_SSH_COMMAND"] = f"ssh -i {key_paths['owner'].replace(chr(92), '/')} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -p 2222"

time.sleep(2) # let SSH sync
push_res = run_cmd(["git", "push", f"ssh://git@127.0.0.1:2222/{owner}/{repo_name}.git", "main"], cwd=repo_dir, env=env)
if push_res.returncode != 0:
    print("Initial push failed!", push_res.stderr)

print("Setting branch protection on main...")
owner_session.post(f"{BASE_URL}/branches/{owner}/{repo_name}/protection", json={
    "branch_pattern": "main",
    "require_admin_for_push": True
}).raise_for_status()

print("Writing wrapper ps1...")
ps1_path = os.path.join(key_dir, "run_test.ps1")
with open(ps1_path, "w") as f:
    f.write(f"""
$RepoUrl = "ssh://git@localhost:2222/{owner}/{repo_name}.git"
$OwnerKey = "{key_paths['owner'].replace(chr(92), '/')}"
$ReadOnlyKey = "{key_paths['readonly'].replace(chr(92), '/')}"
$WriteKey = "{key_paths['write'].replace(chr(92), '/')}"
$AdminKey = "{key_paths['admin'].replace(chr(92), '/')}"
$UnknownKey = "{key_paths['unknown'].replace(chr(92), '/')}"
$WorkDir = "{key_dir.replace(chr(92), '/')}/ssh_work"

""")
    with open("manual_ssh_verification.ps1", "r") as original:
        content = original.read()
        # Remove variable definitions at top since we injected them
        content = content[content.find('Write-Host "======='):]
        # inject strict host key checking
        content = content.replace('IdentitiesOnly=yes', 'IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222')
        f.write(content)

print("Executing powershell script...")
ps1_res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps1_path], capture_output=True, text=True)
print(ps1_res.stdout)
print(ps1_res.stderr)

shutil.rmtree(key_dir, ignore_errors=True)
