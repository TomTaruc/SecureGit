"""Commit routes — /api/commits/*"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models.user import User
from ..models.branch import Branch
from ..models.commit import Commit, CommitFile
from ..models.file import File
from ..services import git_service
from ..utils.decorators import require_project_access

commits_bp = Blueprint("commits", __name__)


def _repo_path(project) -> str:
    if not project.repository:
        from flask import abort; abort(404)
    return project.repository.repo_path


def _sync_commit(project, commit_data: dict) -> Commit:
    """Sync a git log entry into the commits table if not already present."""
    existing = Commit.query.filter_by(commit_hash=commit_data["hash"]).first()
    if existing:
        return existing

    # Resolve or create branch record
    repo = project.repository
    branch_name = request.args.get("branch", project.default_branch)
    branch = Branch.query.filter_by(repo_id=repo.repo_id, branch_name=branch_name).first()
    if not branch:
        branch = Branch(repo_id=repo.repo_id, branch_name=branch_name, is_default=(branch_name == project.default_branch))
        db.session.add(branch)
        db.session.flush()

    # Try to match author by email
    author = User.query.filter_by(email=commit_data["author_email"]).first()
    author_id = author.user_id if author else 1  # fallback to first admin

    commit = Commit(
        branch_id=branch.branch_id,
        author_id=author_id,
        commit_hash=commit_data["hash"],
        short_hash=commit_data["short_hash"],
        message=commit_data["message"],
        committed_at=commit_data["date"],
        parent_hash=commit_data.get("parent_hash"),
    )
    db.session.add(commit)
    return commit


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@commits_bp.get("/<username>/<project_name>")
@jwt_required()
@require_project_access("read")
def list_commits(username, project_name, project, current_user):
    branch  = request.args.get("branch", project.default_branch)
    author  = request.args.get("author")
    since   = request.args.get("since")
    until   = request.args.get("until")
    query   = request.args.get("query")
    page    = int(request.args.get("page", 1))
    per_page= min(int(request.args.get("per_page", 30)), 100)

    repo_path = _repo_path(project)
    skip = (page - 1) * per_page

    try:
        commits = git_service.git_log(repo_path, branch, author, since, until, skip, per_page, query)
        total   = git_service.git_log_count(repo_path, branch, query)
    except RuntimeError as e:
        return jsonify({"error": "git_error", "message": str(e), "status": 500}), 500

    # Async sync to DB (non-blocking)
    try:
        for c in commits:
            _sync_commit(project, c)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({
        "commits":     commits,
        "page":        page,
        "per_page":    per_page,
        "total":       total,
        "total_pages": max(1, -(-total // per_page)),
    }), 200


@commits_bp.get("/<username>/<project_name>/<commit_hash>")
@jwt_required()
@require_project_access("read")
def commit_detail(username, project_name, commit_hash, project, current_user):
    repo_path = _repo_path(project)
    try:
        detail = git_service.git_show_stat(repo_path, commit_hash)
    except (RuntimeError, ValueError) as e:
        return jsonify({"error": "git_error", "message": str(e), "status": 404}), 404
    return jsonify(detail), 200


@commits_bp.get("/<username>/<project_name>/<commit_hash>/diff")
@jwt_required()
@require_project_access("read")
def commit_diff(username, project_name, commit_hash, project, current_user):
    repo_path = _repo_path(project)
    try:
        diff = git_service.git_diff(repo_path, commit_hash)
    except (RuntimeError, ValueError) as e:
        return jsonify({"error": "git_error", "message": str(e), "status": 404}), 404
    return jsonify(diff), 200
