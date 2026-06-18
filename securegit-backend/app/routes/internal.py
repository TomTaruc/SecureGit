"""Internal hook routes — /internal/* (localhost only, not exposed via Nginx)"""
import os
import hmac
import hashlib
from flask import Blueprint, jsonify, request, abort
from ..extensions import db
from ..models.user import User
from ..models.project import Project
from ..models.repository import Repository
from ..models.branch import Branch
from ..models.commit import Commit
from ..models.audit_log import AuditLog
from ..services import git_service, webhook_service
from datetime import datetime, timezone

internal_bp = Blueprint("internal", __name__)

HOOK_SECRET = os.environ.get("INTERNAL_HOOK_SECRET", "")


def _verify_hook_secret() -> None:
    """Verify X-Hook-Secret header. Only allow calls from localhost."""
    remote = request.remote_addr or ""
    if remote not in ("127.0.0.1", "::1"):
        abort(403)
    secret = request.headers.get("X-Hook-Secret", "")
    if not HOOK_SECRET or not hmac.compare_digest(secret, HOOK_SECRET):
        abort(403)

@internal_bp.post("/ssh-auth")
def ssh_auth():
    _verify_hook_secret()
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    owner = data.get("owner")
    project_name = data.get("project_name")
    action = data.get("action")  # 'read' or 'write'

    if not all([user_id, owner, project_name, action]):
        return jsonify({"error": "missing_fields"}), 400

    user = User.query.get(user_id)
    if not user or user.is_suspended:
        return jsonify({"error": "User suspended or not found."}), 403

    owner_user = User.query.filter_by(username=owner).first()
    if not owner_user:
        return jsonify({"error": "Owner not found."}), 404

    project = Project.query.filter_by(owner_user_id=owner_user.user_id, project_name=project_name).first()
    if not project:
        return jsonify({"error": "Project not found."}), 404

    # Evaluate permissions via rbac module
    from ..utils.rbac import get_user_permission
    perm = get_user_permission(user.user_id, project.project_id)

    # For a write action, user needs 'write' or 'admin'
    if action == "write":
        if perm not in ("write", "admin"):
            return jsonify({"error": "Push access denied."}), 403
    elif action == "read":
        if not perm and project.visibility == "private":
            return jsonify({"error": "Pull access denied."}), 403

    repo = Repository.query.filter_by(project_id=project.project_id).first()
    if not repo:
        return jsonify({"error": "Repository not initialized."}), 404

    return jsonify({"repo_path": repo.repo_path}), 200


@internal_bp.post("/hook/post-receive")
def post_receive():
    _verify_hook_secret()
    data = request.get_json(silent=True) or {}

    repo_path = data.get("repo_path", "")
    oldrev    = data.get("oldrev", "")
    newrev    = data.get("newrev", "")
    ref       = data.get("ref", "")  # e.g. refs/heads/main

    if not repo_path or not newrev or not ref:
        return jsonify({"error": "missing_fields"}), 400

    # Extract branch name from ref
    if not ref.startswith("refs/heads/"):
        return jsonify({"message": "Non-branch ref, skipping."}), 200
    branch_name = ref[len("refs/heads/"):]

    # Find repository record by path
    repo = Repository.query.filter_by(repo_path=repo_path).first()
    if not repo:
        return jsonify({"error": "repo_not_found"}), 404

    project = repo.project
    repo.project.updated_at = datetime.now(timezone.utc)

    # Ensure branch record exists
    branch = Branch.query.filter_by(repo_id=repo.repo_id, branch_name=branch_name).first()
    if not branch:
        branch = Branch(
            repo_id=repo.repo_id,
            branch_name=branch_name,
            is_default=(branch_name == project.default_branch),
        )
        db.session.add(branch)
        db.session.flush()

    # Sync new commits
    try:
        if oldrev == "0" * 40:
            # New branch: get all commits on this branch
            commits = git_service.git_log(repo_path, branch_name, limit=100)
        else:
            # Incremental: get commits between oldrev..newrev
            raw = git_service._run(repo_path, "log",
                f"{oldrev}..{newrev}",
                f"--format={git_service.LOG_FORMAT}",
            )
            commits = []
            for line in raw.splitlines():
                parts = line.split("|", 6)
                if len(parts) >= 6:
                    commits.append({
                        "hash": parts[0], "short_hash": parts[1],
                        "author_name": parts[2], "author_email": parts[3],
                        "message": parts[4], "date": parts[5],
                        "parent_hash": parts[6] if len(parts) > 6 else None,
                    })
    except RuntimeError:
        commits = []

    synced = 0
    for c in commits:
        if Commit.query.filter_by(commit_hash=c["hash"]).first():
            continue
        author = User.query.filter_by(email=c["author_email"]).first()
        commit = Commit(
            branch_id=branch.branch_id,
            author_id=author.user_id if author else 1,
            commit_hash=c["hash"],
            short_hash=c["short_hash"],
            message=c["message"],
            committed_at=c["date"],
            parent_hash=c.get("parent_hash"),
        )
        db.session.add(commit)
        synced += 1

    db.session.commit()

    # Dispatch internal webhooks
    webhook_service.dispatch_event(project.project_id, "push", {
        "project": project.project_name,
        "branch": branch_name,
        "oldrev": oldrev,
        "newrev": newrev,
        "commits_synced": synced,
    })

    return jsonify({"message": f"Synced {synced} commits on {branch_name}."}), 200

@internal_bp.post("/hook/pre-receive")
def pre_receive():
    _verify_hook_secret()
    data = request.get_json(silent=True) or {}
    repo_path = data.get("repo_path")
    oldrev = data.get("oldrev")
    newrev = data.get("newrev")
    ref = data.get("ref")
    user_id_str = data.get("user_id")

    if not all([repo_path, oldrev, newrev, ref, user_id_str]):
        return jsonify({"error": "Invalid payload."}), 400

    from ..models.repository import Repository
    from ..models.branch_protection import BranchProtectionRule
    from ..models.user import User
    from ..models.project import Project
    
    repo = Repository.query.filter_by(repo_path=repo_path).first()
    if not repo:
        return jsonify({"error": "Repository not found."}), 404

    # Extract branch name from ref (e.g., refs/heads/main -> main)
    if not ref.startswith("refs/heads/"):
        return jsonify({"message": "OK"}), 200 # Allow non-branch pushes (e.g. tags)
    
    branch_name = ref[len("refs/heads/"):]
    
    # Check if branch matches any protection rule
    rules = BranchProtectionRule.query.filter_by(repo_id=repo.repo_id).all()
    import fnmatch
    matched_rule = None
    for rule in rules:
        if fnmatch.fnmatch(branch_name, rule.branch_pattern):
            matched_rule = rule
            break
            
    if not matched_rule:
        return jsonify({"message": "OK"}), 200

    # Retrieve user
    try:
        user_id = int(user_id_str)
        user = User.query.get(user_id)
    except ValueError:
        user = None

    if not user:
        return jsonify({"error": "User context missing."}), 403

    project = Project.query.get(repo.project_id)
    is_owner = (project.owner_user_id == user_id)
    is_admin = (user.role == "admin")

    # Determine user role in this repository
    from ..models.collaborator import Collaborator
    collab = Collaborator.query.filter_by(project_id=project.project_id, user_id=user_id).first()
    user_role = collab.permission if collab else ("owner" if is_owner else "dev")
    if is_admin:
        user_role = "admin"

    # Rule: Require admin for push
    if matched_rule.require_admin_for_push and user_role != "admin" and not is_owner:
        return jsonify({"error": f"Branch '{branch_name}' requires admin privileges to push."}), 403

    # Rule: Restrict push
    if matched_rule.restrict_push:
        if user_role not in matched_rule.allowed_push_roles and not is_owner:
            return jsonify({"error": f"Your role ({user_role}) is not allowed to push to '{branch_name}'."}), 403

    is_delete = (newrev == "0000000000000000000000000000000000000000")
    is_new = (oldrev == "0000000000000000000000000000000000000000")

    # Rule: Disable deletion
    if is_delete and matched_rule.disable_deletion:
        return jsonify({"error": f"Branch '{branch_name}' is protected against deletion."}), 403

    # Rule: Disable force push
    if not is_delete and not is_new and matched_rule.disable_force_push:
        # Check if oldrev is an ancestor of newrev
        import subprocess
        try:
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", oldrev, newrev],
                cwd=repo_path, check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            return jsonify({"error": f"Force pushing to '{branch_name}' is disabled."}), 403

    # Storage Quota Enforcement
    from ..models.enhancement_models import ServerConfig
    import os
    quota_config = ServerConfig.query.filter_by(key="storage_quota_mb").first()
    quota_mb = int(quota_config.value) if (quota_config and quota_config.value.isdigit()) else 1024
    if quota_mb > 0:
        try:
            total_size = 0
            for dirpath, _, filenames in os.walk(repo_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
            repo_size_mb = total_size / (1024 * 1024)
            if repo_size_mb > quota_mb:
                return jsonify({"error": f"Repository storage quota exceeded ({repo_size_mb:.1f}MB / {quota_mb}MB). Push rejected."}), 403
        except Exception:
            pass

    # Large File Detection (max 50MB)
    max_file_size_bytes = 50 * 1024 * 1024
    if not is_delete:
        try:
            # Get list of new objects
            rev_list_cmd = ["git", "rev-list", "--objects", f"{oldrev}..{newrev}"]
            if is_new:
                rev_list_cmd = ["git", "rev-list", "--objects", newrev]
            
            rev_list_out = subprocess.run(rev_list_cmd, cwd=repo_path, capture_output=True, text=True, check=True).stdout
            object_hashes = [line.split()[0] for line in rev_list_out.splitlines() if line.strip()]
            
            if object_hashes:
                # Check sizes using cat-file --batch-check
                cat_file_proc = subprocess.Popen(["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"], cwd=repo_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                out, _ = cat_file_proc.communicate(input="\n".join(object_hashes) + "\n")
                
                for line in out.splitlines():
                    if not line.strip(): continue
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == "blob":
                        size = int(parts[2])
                        if size > max_file_size_bytes:
                            return jsonify({"error": f"Push rejected: File exceeds the 50MB limit ({size / (1024*1024):.1f}MB)."}), 403
        except Exception:
            pass

    return jsonify({"message": "OK"}), 200

@internal_bp.post("/backup")
def internal_backup():
    _verify_hook_secret()
    data = request.get_json(silent=True) or {}
    backup_type = data.get("backup_type", "full")
    from ..services import backup_service
    destination = data.get("destination", os.environ.get("BACKUP_DEST_PATH", "/mnt/backup"))
    
    import threading
    def _run():
        backup_service.run_full_backup(destination, triggered_by=None)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"message": "Backup started.", "destination": destination}), 202
