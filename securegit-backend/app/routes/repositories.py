"""Repository file browsing routes — /api/repos/*"""
import base64
import mimetypes
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required
from ..services import git_service
from ..utils.decorators import require_project_access

repos_bp = Blueprint("repos", __name__)


def _get_repo_path(project) -> str:
    if not project.repository:
        from flask import abort
        abort(404)
    return project.repository.repo_path


@repos_bp.get("/<username>/<project_name>/tree")
@jwt_required()
@require_project_access("read")
def tree(username, project_name, project, current_user):
    branch = request.args.get("branch", project.default_branch)
    path   = request.args.get("path", "")
    repo_path = _get_repo_path(project)
    try:
        entries = git_service.git_ls_tree(repo_path, branch, path)
        return jsonify(entries), 200
    except Exception as e:
        return jsonify({"error": "git_error", "message": str(e), "status": 500}), 500


@repos_bp.get("/<username>/<project_name>/blob")
@jwt_required()
@require_project_access("read")
def blob(username, project_name, project, current_user):
    branch   = request.args.get("branch", project.default_branch)
    filepath = request.args.get("path", "")
    if not filepath:
        return jsonify({"error": "validation_error", "message": "path parameter is required.", "status": 400}), 400

    repo_path = _get_repo_path(project)
    try:
        raw = git_service.git_show_file(repo_path, branch, filepath)
    except RuntimeError as e:
        return jsonify({"error": "not_found", "message": str(e), "status": 404}), 404

    # Detect if binary
    try:
        content_text = raw.decode("utf-8")
        is_binary = False
    except UnicodeDecodeError:
        content_text = None
        is_binary = True

    # Guess language from extension
    _, ext = filepath.rsplit(".", 1) if "." in filepath else (filepath, "")
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "jsx": "jsx", "tsx": "tsx", "html": "html", "css": "css",
        "json": "json", "yaml": "yaml", "yml": "yaml",
        "sh": "bash", "sql": "sql", "md": "markdown", "rs": "rust",
        "go": "go", "c": "c", "cpp": "cpp", "java": "java",
    }
    language = lang_map.get(ext.lower(), "text")

    if is_binary:
        return jsonify({
            "encoding": "base64",
            "content":  base64.b64encode(raw).decode("ascii"),
            "size":     len(raw),
            "language": "binary",
            "is_binary": True,
        }), 200
    else:
        return jsonify({
            "encoding": "utf-8",
            "content":  content_text,
            "size":     len(raw),
            "language": language,
            "is_binary": False,
        }), 200


@repos_bp.get("/<username>/<project_name>/raw")
@jwt_required()
@require_project_access("read")
def raw(username, project_name, project, current_user):
    branch   = request.args.get("branch", project.default_branch)
    filepath = request.args.get("path", "")
    if not filepath:
        return jsonify({"error": "validation_error", "message": "path is required.", "status": 400}), 400

    repo_path = _get_repo_path(project)

    from ..extensions import redis_client
    cache_key = f"raw:{project.project_id}:{branch}:{filepath}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            mime, _ = mimetypes.guess_type(filepath)
            res = Response(cached, mimetype=mime or "application/octet-stream")
            res.headers["Cache-Control"] = "public, max-age=60"
            return res, 200
    except Exception:
        pass

    try:
        content = git_service.git_show_file(repo_path, branch, filepath)
    except RuntimeError as e:
        return jsonify({"error": "not_found", "message": str(e), "status": 404}), 404

    try:
        redis_client.setex(cache_key, 60, content) # Cache for 60s to handle burst requests
    except Exception:
        pass

    mime, _ = mimetypes.guess_type(filepath)
    res = Response(content, mimetype=mime or "application/octet-stream")
    res.headers["Cache-Control"] = "public, max-age=60"
    return res, 200


@repos_bp.get("/<username>/<project_name>/readme")
@jwt_required()
@require_project_access("read")
def readme(username, project_name, project, current_user):
    branch = request.args.get("branch", project.default_branch)
    repo_path = _get_repo_path(project)
    content = git_service.git_readme(repo_path, branch)
    if content is None:
        return jsonify({"content": None}), 200
    return jsonify({"content": content}), 200
