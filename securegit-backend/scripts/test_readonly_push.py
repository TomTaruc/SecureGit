import os
import subprocess
import requests
import tempfile
import time
import shutil

BASE_URL = "http://localhost:5000/api"

def run_cmd(cmd, cwd=None, env=None):
    res = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    return res

def main():
    print("Running read-only SSH push test...")

    # 1. Setup users
    owner = f"owner_{int(time.time())}"
    reader = f"reader_{int(time.time())}"
    pwd = "SecurePass123"

    owner_session = requests.Session()
    reader_session = requests.Session()

    print(f"Creating users: {owner}, {reader}")
    owner_session.post(f"{BASE_URL}/auth/register", json={"username": owner, "email": f"{owner}@test.com", "password": pwd}).raise_for_status()
    reader_session.post(f"{BASE_URL}/auth/register", json={"username": reader, "email": f"{reader}@test.com", "password": pwd}).raise_for_status()

    # 2. Login
    owner_login = owner_session.post(f"{BASE_URL}/auth/login", json={"username": owner, "password": pwd}).json()
    reader_login = reader_session.post(f"{BASE_URL}/auth/login", json={"username": reader, "password": pwd}).json()

    # 3. Add SSH key for reader
    key_dir = tempfile.mkdtemp()
    key_path = os.path.join(key_dir, "id_rsa")
    run_cmd(["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", key_path, "-N", ""])
    with open(f"{key_path}.pub", "r") as f:
        pub_key = f.read().strip()
    
    reader_session.post(f"{BASE_URL}/ssh-keys", json={"title": "reader_key", "public_key": pub_key}).raise_for_status()

    # 4. Create repo
    repo_name = "test-repo"
    owner_session.post(f"{BASE_URL}/projects", json={"project_name": repo_name, "description": "Test", "visibility": "public"}).raise_for_status()

    # 5. Add reader as collaborator (read-only)
    reader_id = owner_session.get(f"{BASE_URL}/users/search?q={reader}").json()[0]["user_id"]
    owner_session.post(f"{BASE_URL}/projects/{owner}/{repo_name}/collaborators", json={"user_id": reader_id, "permission": "read"}).raise_for_status()

    # 6. Local Git Repo setup
    repo_dir = os.path.join(key_dir, "repo")
    os.makedirs(repo_dir)
    run_cmd(["git", "init"], cwd=repo_dir)
    run_cmd(["git", "config", "user.email", "test@test.com"], cwd=repo_dir)
    run_cmd(["git", "config", "user.name", "Test"], cwd=repo_dir)
    
    with open(os.path.join(repo_dir, "test.txt"), "w") as f:
        f.write("Hello")
    run_cmd(["git", "add", "."], cwd=repo_dir)
    run_cmd(["git", "commit", "-m", "init"], cwd=repo_dir)
    run_cmd(["git", "branch", "-M", "main"], cwd=repo_dir)
    
    # 7. Push attempt using reader's SSH key
    # Wait a few seconds for SSH keys to sync inside Docker
    time.sleep(2)
    
    # Use powershell equivalent escaping for SSH command if we are using string
    env = os.environ.copy()
    key_path_fw = key_path.replace("\\", "/") # Git bash needs forward slashes
    env["GIT_SSH_COMMAND"] = f"ssh -i {key_path_fw} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -p 2222"
    
    print("Attempting to push...")
    push_res = run_cmd(["git", "push", "ssh://git@127.0.0.1:2222/" + owner + "/" + repo_name + ".git", "main"], cwd=repo_dir, env=env)
    
    print("Push Return Code:", push_res.returncode)
    print("STDOUT:", push_res.stdout)
    print("STDERR:", push_res.stderr)
    
    if "rejected" in push_res.stderr.lower() or "denied" in push_res.stderr.lower() or push_res.returncode != 0:
        print("SUCCESS: Push was rejected as expected.")
    else:
        print("FAIL: Push succeeded when it should have been rejected.")

    shutil.rmtree(key_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
