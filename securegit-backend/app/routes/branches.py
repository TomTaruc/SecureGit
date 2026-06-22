"""Branch routes — /api/branches/* (includes protection rules)"""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.branch import Branch
from ..models.branch_protection import BranchProtectionRule
from ..services import git_service, audit_service
from ..utils.decorators import require_project_access
from ..utils.validators import validate_branch_name
from ..utils.rbac import check_branch_create, check_branch_delete

branches_bp = Blueprint("branches", __name__)


def _repo_path(project) -> str:
    if not project.repository:
        from flask import abort; abort(404)
    return project.repository.repo_path


# ---------------------------------------------------------------------------
# Branch CRUD
# ---------------------------------------------------------------------------

@branches_bp.get("/<username>/<project_name>")
@jwt_required()
@require_project_access("read")
def list_branches(username, project_name, project, current_user):
    repo_path = _repo_path(project)
    try:
        branches = git_service.git_branches(repo_path)
    except RuntimeError:
        branches = []
    # Annotate with DB info
    default = project.default_branch
    import fnmatch
    rules = BranchProtectionRule.query.filter_by(repo_id=project.repository.repo_id).all()
    
    for b in branches:
        b["is_default"] = (b["name"] == default)
        # Check protection against batched rules
        b["is_protected"] = any(fnmatch.fnmatch(b["name"], r.branch_pattern) for r in rules)
    return jsonify(branches), 200


@branches_bp.post("/<username>/<project_name>")
@jwt_required()
@require_project_access("read")  # Extra check: create_branch permission
def create_branch(username, project_name, project, current_user):
    if not check_branch_create(current_user, project):
        return jsonify({"error": "forbidden", "message": "You do not have permission to create branches.", "status": 403}), 403

    data = request.get_json(silent=True) or {}
    new_branch  = (data.get("branch_name") or "").strip()
    from_branch = (data.get("from_branch") or project.default_branch).strip()

    err = validate_branch_name(new_branch)
    if err:
        return jsonify({"error": "validation_error", "message": err, "status": 422}), 422

    repo_path = _repo_path(project)
    try:
        git_service.git_create_branch(repo_path, new_branch, from_branch)
    except (RuntimeError, ValueError) as e:
        return jsonify({"error": "git_error", "message": str(e), "status": 400}), 400

    # Sync to branches table
    branch = Branch(repo_id=project.repository.repo_id, branch_name=new_branch)
    db.session.add(branch)
    db.session.commit()
    audit_service.log(actor_id=current_user.user_id, action="branch.create", target_type="project", target_id=project.project_id, detail=new_branch)
    return jsonify(branch.to_dict()), 201


@branches_bp.delete("/<username>/<project_name>/<path:branch_name>")
@jwt_required()
@require_project_access("read")
def delete_branch(username, project_name, branch_name, project, current_user):
    if not check_branch_delete(current_user, project):
        return jsonify({"error": "forbidden", "message": "You do not have permission to delete branches.", "status": 403}), 403

    if branch_name == project.default_branch:
        return jsonify({"error": "validation_error", "message": "Cannot delete the default branch.", "status": 422}), 422

    # Check branch protection
    if _is_branch_protected_delete(project.repository.repo_id, branch_name):
        return jsonify({"error": "forbidden", "message": "Branch is protected from deletion.", "status": 403}), 403

    repo_path = _repo_path(project)
    try:
        git_service.git_delete_branch(repo_path, branch_name)
    except (RuntimeError, ValueError) as e:
        return jsonify({"error": "git_error", "message": str(e), "status": 400}), 400

    Branch.query.filter_by(repo_id=project.repository.repo_id, branch_name=branch_name).delete()
    db.session.commit()
    audit_service.log(actor_id=current_user.user_id, action="branch.delete", target_type="project", target_id=project.project_id, detail=branch_name)
    return jsonify({"message": f"Branch '{branch_name}' deleted."}), 200


# ---------------------------------------------------------------------------
# Branch Protection Rules (Enhancement)
# ---------------------------------------------------------------------------

@branches_bp.get("/<username>/<project_name>/protection")
@jwt_required()
@require_project_access("manage_settings")
def list_protection_rules(username, project_name, project, current_user):
    rules = BranchProtectionRule.query.filter_by(repo_id=project.repository.repo_id).all()
    return jsonify([r.to_dict() for r in rules]), 200


@branches_bp.post("/<username>/<project_name>/protection")
@jwt_required()
@require_project_access("manage_settings")
def create_protection_rule(username, project_name, project, current_user):
    data = request.get_json(silent=True) or {}
    pattern = (data.get("branch_pattern") or "").strip()
    if not pattern:
        return jsonify({"error": "validation_error", "message": "branch_pattern is required.", "status": 422}), 422

    if BranchProtectionRule.query.filter_by(repo_id=project.repository.repo_id, branch_pattern=pattern).first():
        return jsonify({"error": "conflict", "message": "Protection rule for this pattern already exists.", "status": 409}), 409

    rule = BranchProtectionRule(
        repo_id=project.repository.repo_id,
        branch_pattern=pattern,
        disable_force_push=data.get("disable_force_push", True),
        disable_deletion=data.get("disable_deletion", True),
        restrict_push=data.get("restrict_push", False),
        allowed_push_roles=data.get("allowed_push_roles", ["admin"]),
        require_admin_for_push=data.get("require_admin_for_push", False),
        require_linear_history=data.get("require_linear_history", False),
    )
    db.session.add(rule)
    db.session.commit()
    audit_service.log(actor_id=current_user.user_id, action="branch_protection.create", target_type="project", target_id=project.project_id, detail=pattern)

    # NEW: warn if the pattern currently matches no branches
    import fnmatch
    from ..services import git_service
    try:
        existing_branches = [b["name"] for b in git_service.git_branches(project.repository.repo_path)]
    except Exception:
        existing_branches = []
    matches_any = any(fnmatch.fnmatch(b, pattern) for b in existing_branches)

    response = rule.to_dict()
    if not matches_any:
        response["warning"] = (
            f"This pattern doesn't match any existing branch. "
            f"Double-check spelling/case — branch_pattern matching is case-sensitive."
        )
    return jsonify(response), 201


@branches_bp.patch("/<username>/<project_name>/protection/<int:rule_id>")
@jwt_required()
@require_project_access("manage_settings")
def update_protection_rule(username, project_name, rule_id, project, current_user):
    rule = BranchProtectionRule.query.filter_by(rule_id=rule_id, repo_id=project.repository.repo_id).first_or_404()
    data = request.get_json(silent=True) or {}
    for field in ("disable_force_push", "disable_deletion", "restrict_push", "allowed_push_roles", "require_admin_for_push", "require_linear_history"):
        if field in data:
            setattr(rule, field, data[field])
    rule.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(rule.to_dict()), 200


@branches_bp.delete("/<username>/<project_name>/protection/<int:rule_id>")
@jwt_required()
@require_project_access("manage_settings")
def delete_protection_rule(username, project_name, rule_id, project, current_user):
    rule = BranchProtectionRule.query.filter_by(rule_id=rule_id, repo_id=project.repository.repo_id).first_or_404()
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": "Protection rule deleted."}), 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_branch_protected(repo_id: int, branch_name: str) -> bool:
    """Check if any protection rule matches the branch name."""
    import fnmatch
    rules = BranchProtectionRule.query.filter_by(repo_id=repo_id).all()
    return any(fnmatch.fnmatch(branch_name, r.branch_pattern) for r in rules)


def _is_branch_protected_delete(repo_id: int, branch_name: str) -> bool:
    import fnmatch
    rules = BranchProtectionRule.query.filter_by(repo_id=repo_id).all()
    for r in rules:
        if fnmatch.fnmatch(branch_name, r.branch_pattern) and r.disable_deletion:
            return True
    return False
