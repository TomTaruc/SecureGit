"""
Route decorators for authentication, admin access, and project permission checks.
"""
from functools import wraps
from flask import jsonify, abort
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from ..models.user import User
from ..models.project import Project
from ..utils.rbac import check_permission


def require_auth(fn):
    """Verify JWT and ensure user is active (not suspended)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            abort(401)
        if user.is_suspended:
            return jsonify({"error": "account_suspended", "message": "Your account has been suspended.", "status": 403}), 403
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    """Verify JWT and ensure user has role='admin'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.is_suspended:
            abort(401)
        if user.role != "admin":
            return jsonify({"error": "forbidden", "message": "Admin access required.", "status": 403}), 403
        return fn(*args, **kwargs)
    return wrapper


def require_project_access(permission: str = "read"):
    """
    Decorator factory. Looks up project from URL kwargs (username, project_name).
    Checks RBAC permission. Injects `project` and `current_user` into kwargs.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or user.is_suspended:
                abort(401)

            username = kwargs.get("username")
            project_name = kwargs.get("project_name")

            owner = User.query.filter_by(username=username).first()
            if not owner:
                abort(404)

            project = Project.query.filter_by(
                owner_user_id=owner.user_id, project_name=project_name
            ).first()
            if not project or project.deleted_at is not None:
                abort(404)

            if not check_permission(user, project, permission):
                return jsonify({"error": "forbidden", "message": "Insufficient permissions.", "status": 403}), 403

            kwargs["project"] = project
            kwargs["current_user"] = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator
