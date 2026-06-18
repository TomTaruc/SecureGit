"""Input validation helpers."""
import re

PROJECT_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,98}[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
USERNAME_RE     = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-]{1,48}[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
BRANCH_RE       = re.compile(r'^[a-zA-Z0-9._\-/]{1,255}$')
EMAIL_RE        = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def validate_project_name(name: str) -> str | None:
    """Return None if valid, error message if invalid."""
    if not name:
        return "Project name is required."
    if not PROJECT_NAME_RE.match(name):
        return "Project name must be alphanumeric with hyphens (no spaces, no leading/trailing hyphens)."
    return None


def validate_username(username: str) -> str | None:
    if not username:
        return "Username is required."
    if not USERNAME_RE.match(username):
        return "Username must be 1–50 alphanumeric characters (hyphens and underscores allowed)."
    return None


def validate_branch_name(name: str) -> str | None:
    if not name:
        return "Branch name is required."
    if not BRANCH_RE.match(name):
        return "Branch name contains invalid characters."
    return None


def validate_email(email: str) -> str | None:
    if not email:
        return "Email is required."
    if not EMAIL_RE.match(email):
        return "Invalid email format."
    return None


def validate_password(password: str) -> str | None:
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None
