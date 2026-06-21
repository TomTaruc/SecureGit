import os
import pwd
from app import create_app
from app.extensions import db
from app.models.repository import Repository

app = create_app()

def fix_hooks():
    with app.app_context():
        repos = Repository.query.all()
        for repo in repos:
            path = repo.repo_path
            hooks_dir = os.path.join(path, "hooks")
            if not os.path.exists(hooks_dir):
                continue
            
            try:
                git_pwd = pwd.getpwnam("git")
            except Exception:
                git_pwd = None
            
            pre_receive_path = os.path.join(hooks_dir, "pre-receive")
            with open(pre_receive_path, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("while read oldrev newrev refname; do\n")
                f.write("    resp=$(curl -s -w \"\\n%{http_code}\" -X POST http://127.0.0.1:5000/api/internal/hook/pre-receive \\\n")
                f.write("      -H \"Content-Type: application/json\" \\\n")
                f.write("      -H \"X-Hook-Secret: $INTERNAL_HOOK_SECRET\" \\\n")
                f.write("      -d \"{\\\"repo_path\\\": \\\"$PWD\\\", \\\"oldrev\\\": \\\"$oldrev\\\", \\\"newrev\\\": \\\"$newrev\\\", \\\"ref\\\": \\\"$refname\\\", \\\"user_id\\\": \\\"$SECUREGIT_USER_ID\\\", \\\"git_env\\\": {\\\"GIT_QUARANTINE_PATH\\\": \\\"$GIT_QUARANTINE_PATH\\\", \\\"GIT_OBJECT_DIRECTORY\\\": \\\"$GIT_OBJECT_DIRECTORY\\\", \\\"GIT_ALTERNATE_OBJECT_DIRECTORIES\\\": \\\"$GIT_ALTERNATE_OBJECT_DIRECTORIES\\\"}}\")\n")
                f.write("    http_code=$(echo \"$resp\" | tail -n1)\n")
                f.write("    body=$(echo \"$resp\" | sed '$d')\n")
                f.write("    if [ \"$http_code\" -ne 200 ]; then\n")
                f.write("        echo \"$body\" >&2\n")
                f.write("        exit 1\n")
                f.write("    fi\n")
                f.write("done\n")
                f.write("exit 0\n")
            os.chmod(pre_receive_path, 0o755)
            if git_pwd:
                try:
                    os.chown(pre_receive_path, git_pwd.pw_uid, git_pwd.pw_gid)
                except Exception:
                    pass
            print(f"Fixed hooks for {repo.project.project_name}")

if __name__ == "__main__":
    fix_hooks()
