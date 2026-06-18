#!/usr/bin/env python3
import os
import sys
import shlex
import urllib.request
import urllib.parse
import json

def fail(message):
    print(f"fatal: {message}", file=sys.stderr)
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        fail("No user ID provided.")

    user_id = sys.argv[1]
    
    # Read the original SSH command
    original_cmd = os.environ.get("SSH_ORIGINAL_COMMAND")
    if not original_cmd:
        fail("Interactive SSH sessions are not allowed.")

    # Parse the command
    try:
        parts = shlex.split(original_cmd)
    except ValueError:
        fail("Invalid command syntax.")

    if not parts:
        fail("Empty command.")

    git_cmd = parts[0]
    allowed_cmds = ["git-receive-pack", "git-upload-pack", "git-upload-archive"]
    
    if git_cmd not in allowed_cmds:
        fail(f"Command '{git_cmd}' is not allowed.")

    if len(parts) < 2:
        fail("Repository path not provided.")

    repo_path = parts[1]
    # Remove leading slashes and .git
    clean_path = repo_path.strip("/")
    if clean_path.endswith(".git"):
        clean_path = clean_path[:-4]

    # Parse owner and repo name
    path_parts = clean_path.split("/")
    if len(path_parts) != 2:
        fail("Invalid repository path format. Expected owner/repo.")

    owner, project_name = path_parts

    action = "write" if git_cmd == "git-receive-pack" else "read"

    # Authorize via internal API
    hook_secret = os.environ.get("INTERNAL_HOOK_SECRET", "")
    if not hook_secret:
        # Try to read from .env if running from source tree
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("INTERNAL_HOOK_SECRET="):
                        hook_secret = line.strip().split("=", 1)[1]
                        break

    if not hook_secret:
        fail("Server configuration error: INTERNAL_HOOK_SECRET missing.")

    # We make a request to the backend to check authorization
    # If the user is authorized, the backend returns 200 OK.
    # Otherwise it returns 403.
    req_data = json.dumps({
        "user_id": int(user_id),
        "owner": owner,
        "project_name": project_name,
        "action": action
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:5000/api/internal/ssh-auth",
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "X-Hook-Secret": hook_secret
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                fail("Access denied.")
            # The backend will return the absolute path to the repository
            resp_data = json.loads(response.read().decode())
            absolute_repo_path = resp_data.get("repo_path")
    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 403:
            # We can try to read the error message
            try:
                msg = json.loads(e.read().decode()).get("error", "Access denied.")
                fail(msg)
            except Exception:
                fail("Access denied.")
        elif e.code == 404:
            fail("Repository not found.")
        else:
            fail(f"Internal server error: {e.code}")
    except Exception as e:
        fail(f"Server communication failed: {e}")

    if not absolute_repo_path:
        fail("Repository path not resolved.")

    # Execute the requested git command
    # e.g., git-receive-pack /srv/git/owner/repo.git
    # Use os.execvp to replace the current process
    # We must ensure no other arguments are passed to prevent injection
    cmd_to_exec = [git_cmd, absolute_repo_path]
    os.environ["SECUREGIT_USER_ID"] = str(user_id)
    os.execvp(git_cmd, cmd_to_exec)

if __name__ == "__main__":
    main()
