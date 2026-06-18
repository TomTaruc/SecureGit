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
    # Block non-localhost IPs
    remote = request.remote_addr or ""
    if remote not in ("127.0.0.1", "::1"):
        abort(403)
    # Verify secret
    secret = request.headers.get("X-Hook-Secret", "")
    if HOOK_SECRET and not hmac.compare_digest(secret, HOOK_SECRET):
        abort(403)


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
