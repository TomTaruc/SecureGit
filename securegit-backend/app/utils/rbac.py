"""
RBAC permission checking utilities.
"""
from typing import Optional
from ..extensions import db
from ..models.collaborator import Collaborator
from ..models.project import Project
from ..models.user import User


VALID_PERMISSIONS = frozenset([
    "read", "push", "create_branch", "delete_branch",
    "manage_collaborators", "manage_settings", "admin",
])


def get_actor_permission(user: User, project: Project) -> Optional[Collaborator]:
    """
    Return the Collaborator entry for user on project, or None if not a collaborator.
    Project owner implicitly has all permissions.
    """
    if project.owner_user_id == user.user_id:
        return None  # Owner: no collab entry needed
    return Collaborator.query.filter_by(
        project_id=project.project_id, user_id=user.user_id
    ).first()


def check_permission(user: User, project: Project, perm: str) -> bool:
    """
    Return True if user has the given RBAC permission on the project.
    - Admin users always have all permissions.
    - Project owners always have all permissions.
    - Otherwise check the collaborators.permissions JSONB.
    """
    if user.role == "admin":
        return True
    if project.owner_user_id == user.user_id:
        return True

    collab = get_actor_permission(user, project)
    if collab is None:
        return False  # Not a collaborator
    return collab.has_permission(perm)


def check_push_permission(user: User, project: Project) -> bool:
    return check_permission(user, project, "push")


def check_branch_create(user: User, project: Project) -> bool:
    return check_permission(user, project, "create_branch")


def check_branch_delete(user: User, project: Project) -> bool:
    return check_permission(user, project, "delete_branch")


def check_manage_collaborators(user: User, project: Project) -> bool:
    return check_permission(user, project, "manage_collaborators")


def check_manage_settings(user: User, project: Project) -> bool:
    return check_permission(user, project, "manage_settings")


def check_admin_on_project(user: User, project: Project) -> bool:
    return check_permission(user, project, "admin")


def get_user_permission(user_id: int, project_id: int) -> Optional[str]:
    """
    Return the effective permission level for a user on a project,
    using IDs rather than ORM objects. Used by internal/SSH-auth endpoints.
    Returns 'admin', 'write', 'read', or None.
    """
    user = db.session.get(User, user_id)
    project = db.session.get(Project, project_id)
    if not user or not project:
        return None

    # Site admins have full access
    if user.role == "admin":
        return "admin"

    # Project owner has full access
    if project.owner_user_id == user_id:
        return "admin"

    # Check collaborator record
    collab = Collaborator.query.filter_by(
        project_id=project_id, user_id=user_id
    ).first()
    if collab is None:
        return None

    # Map RBAC permissions to legacy levels for SSH auth
    if collab.has_permission("admin"):
        return "admin"
    if collab.has_permission("push"):
        return "write"
    if collab.has_permission("read"):
        return "read"

    # Fall back to legacy permission column
    return collab.permission
