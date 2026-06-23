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

    user = db.session.get(User, user_id)
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

    from ..services.sync_service import handle_post_receive
    try:
        result = handle_post_receive(repo_path, oldrev, newrev, ref)
        return jsonify({"message": result.get("message")}), 200
    except ValueError as e:
        if str(e) == "invalid_path":
            return jsonify({"error": "invalid_path"}), 400
        elif str(e) == "repo_not_found":
            return jsonify({"error": "repo_not_found"}), 404
        from flask import current_app
        current_app.logger.exception("Internal error in post_receive")
        return jsonify({"error": "INTERNAL_ERROR"}), 500

@internal_bp.post("/hook/pre-receive")
def pre_receive():
    _verify_hook_secret()
    data = request.get_json(silent=True) or {}
    repo_path = data.get("repo_path")
    oldrev = data.get("oldrev")
    newrev = data.get("newrev")
    ref = data.get("ref")
    user_id_str = data.get("user_id")
    git_env = data.get("git_env", {})

    if not all([repo_path, oldrev, newrev, ref, user_id_str]):
        return jsonify({"error": "Invalid payload."}), 400

    from ..services.hook_policy_engine import HookPolicyEngine
    resp, status_code = HookPolicyEngine.validate_pre_receive(repo_path, oldrev, newrev, ref, user_id_str, git_env)
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
