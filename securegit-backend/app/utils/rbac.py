"""
RBAC permission checking utilities.
"""
from typing import Optional
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
