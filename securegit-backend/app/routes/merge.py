"""Merge routes — /api/merge/*"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..services import merge_service
from ..utils.decorators import require_project_access
from ..utils.rbac import check_push_permission

merge_bp = Blueprint("merge", __name__)


@merge_bp.get("/<username>/<project_name>/compare")
@jwt_required()
@require_project_access("read")
def compare(username, project_name, project, current_user):
    base = request.args.get("base", project.default_branch)
    head = request.args.get("head", "")
    if not head:
        return jsonify({"error": "validation_error", "message": "'head' parameter required.", "status": 400}), 400
    repo_path = project.repository.repo_path
    result = merge_service.compare_branches(repo_path, base, head)
    return jsonify(result), 200


@merge_bp.get("/<username>/<project_name>/divergence")
@jwt_required()
@require_project_access("read")
def divergence(username, project_name, project, current_user):
    base = request.args.get("base", project.default_branch)
    head = request.args.get("head", "")
    if not head:
        return jsonify({"error": "validation_error", "message": "'head' parameter required.", "status": 400}), 400
    result = merge_service.branch_divergence(project.repository.repo_path, base, head)
    return jsonify(result), 200


@merge_bp.get("/<username>/<project_name>/conflicts")
@jwt_required()
@require_project_access("read")
def check_conflicts(username, project_name, project, current_user):
    base = request.args.get("base", project.default_branch)
    head = request.args.get("head", "")
    if not head:
        return jsonify({"error": "validation_error", "message": "'head' parameter required.", "status": 400}), 400
    conflicts = merge_service.detect_conflicts(project.repository.repo_path, base, head)
    return jsonify({"conflicts": conflicts, "has_conflicts": len(conflicts) > 0}), 200


@merge_bp.post("/<username>/<project_name>/merge")
@jwt_required()
@require_project_access("push")
def do_merge(username, project_name, project, current_user):
    if not check_push_permission(current_user, project):
        return jsonify({"error": "forbidden", "message": "Push permission required.", "status": 403}), 403

    data = request.get_json(silent=True) or {}
    strategy = data.get("strategy", "ff")   # 'ff', 'squash', 'rebase'
    base = data.get("base", project.default_branch)
    head = data.get("head", "")
    message = data.get("message", f"Merge '{head}' into '{base}'")

    if not head:
        return jsonify({"error": "validation_error", "message": "'head' is required.", "status": 400}), 400

    repo_path = project.repository.repo_path
    if strategy == "squash":
        result = merge_service.squash_merge(repo_path, base, head, message, current_user.user_id)
    elif strategy == "rebase":
        result = merge_service.rebase_merge(repo_path, base, head, current_user.user_id)
    else:
        result = merge_service.fast_forward_merge(repo_path, base, head, current_user.user_id)

    status = 200 if result["success"] else 400
    return jsonify(result), status
