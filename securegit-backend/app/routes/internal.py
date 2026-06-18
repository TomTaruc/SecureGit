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

    import os
    if not os.path.isabs(repo_path) or ".." in repo_path:
        return jsonify({"error": "invalid_path"}), 400

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

    # Dispatch internal webhooks via Celery
    from ..tasks import async_post_receive_task
    payload = {
        "project_id": project.project_id,
        "username": "unknown", # Could be fetched from db if user_id was passed
        "refs": [{
            "ref_name": ref,
            "old_sha": oldrev,
            "new_sha": newrev
        }]
    }
    async_post_receive_task.delay(payload)

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

    from ..services.hook_policy_engine import HookPolicyEngine
    resp, status_code = HookPolicyEngine.validate_pre_receive(repo_path, oldrev, newrev, ref, user_id_str)
    return jsonify(resp), status_code

@internal_bp.post("/backup")
def internal_backup():
    _verify_hook_secret()
    data = request.get_json(silent=True) or {}
    backup_type = data.get("backup_type", "full")
    from ..services import backup_service
    destination = data.get("destination", os.environ.get("BACKUP_DEST_PATH", "/mnt/backup"))
    
    from ..tasks import run_full_backup_task
    run_full_backup_task.delay(destination, None)
    return jsonify({"message": "Backup started.", "destination": destination}), 202
