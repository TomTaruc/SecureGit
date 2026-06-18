"""Project routes — /api/projects/*"""
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models.user import User
from ..models.project import Project
from ..models.repository import Repository
from ..models.collaborator import Collaborator, PERMISSION_PRESETS
from ..models.chroot_jail import ChrootJail
from ..services import git_service, chroot_service, audit_service
from ..utils.decorators import require_auth, require_project_access
from ..utils.validators import validate_project_name
from ..utils.rbac import check_manage_collaborators, check_manage_settings

projects_bp = Blueprint("projects", __name__)

INTERNAL_DOMAIN = os.environ.get("INTERNAL_DOMAIN", "securegit.local")


def _build_clone_url(username: str, project_name: str) -> str:
    return f"git@{INTERNAL_DOMAIN}:{username}/{project_name}.git"


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@projects_bp.get("")
@jwt_required()
def list_projects():
    user_id = get_jwt_identity()
    owned = Project.query.filter_by(owner_user_id=user_id).all()
    collaborated_ids = [
        c.project_id for c in Collaborator.query.filter_by(user_id=user_id).all()
    ]
    collaborated = Project.query.filter(
        Project.project_id.in_(collaborated_ids),
        Project.owner_user_id != user_id,
    ).all()
    all_projects = owned + collaborated
    return jsonify([p.to_dict() for p in all_projects]), 200


@projects_bp.post("")
@jwt_required()
def create_project():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    project_name   = (data.get("project_name") or "").strip()
    description    = data.get("description", "")
    visibility     = data.get("visibility", "private")
    default_branch = data.get("default_branch", "main")

    err = validate_project_name(project_name)
    if err:
        return jsonify({"error": "validation_error", "message": err, "status": 422}), 422

    if Project.query.filter_by(owner_user_id=user_id, project_name=project_name).first():
        return jsonify({"error": "conflict", "message": f"Project '{project_name}' already exists.", "status": 409}), 409

    repo_path = chroot_service.repo_path_for(user.username, project_name)
    clone_url = _build_clone_url(user.username, project_name)

    # Initialize bare git repo
    try:
        git_service.git_init_bare(repo_path)
    except Exception as e:
        return jsonify({"error": "git_error", "message": str(e), "status": 500}), 500

    project = Project(
        owner_user_id=user_id,
        project_name=project_name,
        description=description,
        visibility=visibility,
        default_branch=default_branch,
    )
    db.session.add(project)
    db.session.flush()  # Get project_id

    repo = Repository(
        project_id=project.project_id,
        repo_project_id=project.project_id,
        repo_path=repo_path,
        clone_url=clone_url,
        is_initialized=True,
    )
    db.session.add(repo)

    jail = ChrootJail(
        project_id=project.project_id,
        user_id=user_id,
        jail_path=chroot_service.jail_path_for(user.username),
        fs_jail_user=user.username,
    )
    db.session.add(jail)
    db.session.commit()

    chroot_service.provision_jail(user.username)
    audit_service.log(actor_id=user_id, action="project.create", target_type="project", target_id=project.project_id, detail=project_name)

    return jsonify(project.to_dict()), 201


@projects_bp.get("/<username>/<project_name>")
@jwt_required()
@require_project_access("read")
def get_project(username, project_name, project, current_user):
    return jsonify(project.to_dict()), 200


@projects_bp.patch("/<username>/<project_name>")
@jwt_required()
@require_project_access("manage_settings")
def update_project(username, project_name, project, current_user):
    data = request.get_json(silent=True) or {}
    if "description" in data:
        project.description = data["description"]
    if "visibility" in data and data["visibility"] in ("private", "internal"):
        project.visibility = data["visibility"]
    if "default_branch" in data:
        project.default_branch = data["default_branch"]
    project.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    audit_service.log(actor_id=current_user.user_id, action="project.update", target_type="project", target_id=project.project_id)
    return jsonify(project.to_dict()), 200


@projects_bp.delete("/<username>/<project_name>")
@jwt_required()
@require_project_access("admin")
def delete_project(username, project_name, project, current_user):
    repo = project.repository
    if repo and os.path.exists(repo.repo_path):
        import shutil
        shutil.rmtree(repo.repo_path, ignore_errors=True)
    audit_service.log(actor_id=current_user.user_id, action="project.delete", target_type="project", target_id=project.project_id, detail=project.project_name)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted."}), 200


# ---------------------------------------------------------------------------
# Collaborators (RBAC)
# ---------------------------------------------------------------------------

@projects_bp.get("/<username>/<project_name>/collaborators")
@jwt_required()
@require_project_access("read")
def list_collaborators(username, project_name, project, current_user):
    collabs = Collaborator.query.filter_by(project_id=project.project_id).all()
    return jsonify([c.to_dict() for c in collabs]), 200


@projects_bp.post("/<username>/<project_name>/collaborators")
@jwt_required()
@require_project_access("manage_collaborators")
def add_collaborator(username, project_name, project, current_user):
    data = request.get_json(silent=True) or {}
    target_user_id = data.get("user_id")
    permission_level = data.get("permission", "read")
    custom_permissions = data.get("permissions")

    target_user = User.query.get_or_404(target_user_id)

    if target_user.user_id == project.owner_user_id:
        return jsonify({"error": "conflict", "message": "Cannot add project owner as collaborator.", "status": 409}), 409

    if Collaborator.query.filter_by(project_id=project.project_id, user_id=target_user_id).first():
        return jsonify({"error": "conflict", "message": "User is already a collaborator.", "status": 409}), 409

    permissions = custom_permissions if custom_permissions else PERMISSION_PRESETS.get(permission_level, PERMISSION_PRESETS["read"])

    collab = Collaborator(
        project_id=project.project_id,
        user_id=target_user_id,
        permission=permission_level,
        permissions=permissions,
    )
    db.session.add(collab)
    db.session.commit()
    audit_service.log(actor_id=current_user.user_id, action="collaborator.add", target_type="user", target_id=target_user_id, detail=f"project:{project.project_name}")
    return jsonify(collab.to_dict()), 201


@projects_bp.patch("/<username>/<project_name>/collaborators/<int:uid>")
@jwt_required()
@require_project_access("manage_collaborators")
def update_collaborator(username, project_name, uid, project, current_user):
    collab = Collaborator.query.filter_by(project_id=project.project_id, user_id=uid).first_or_404()
    data = request.get_json(silent=True) or {}
    if "permission" in data:
        level = data["permission"]
        collab.permission = level
        collab.permissions = PERMISSION_PRESETS.get(level, PERMISSION_PRESETS["read"])
    if "permissions" in data:
        collab.permissions = data["permissions"]
    db.session.commit()
    audit_service.log(actor_id=current_user.user_id, action="collaborator.update", target_type="user", target_id=uid)
    return jsonify(collab.to_dict()), 200


@projects_bp.delete("/<username>/<project_name>/collaborators/<int:uid>")
@jwt_required()
@require_project_access("manage_collaborators")
def remove_collaborator(username, project_name, uid, project, current_user):
    collab = Collaborator.query.filter_by(project_id=project.project_id, user_id=uid).first_or_404()
    db.session.delete(collab)
    db.session.commit()
    audit_service.log(actor_id=current_user.user_id, action="collaborator.remove", target_type="user", target_id=uid)
    return jsonify({"message": "Collaborator removed."}), 200
