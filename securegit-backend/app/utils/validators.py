"""Input validation helpers."""
import re
import os
from pathlib import Path

PROJECT_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,98}[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
USERNAME_RE     = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-]{1,48}[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
BRANCH_RE       = re.compile(r'^[a-zA-Z0-9._\-/]{1,255}$')
EMAIL_RE        = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class SecurityError(Exception):
    pass

def ensure_repo_path_safe(repo_path: str, repo_root: str) -> Path:
    if not repo_root:
        from ..config import config
        repo_root = config["default"].GIT_REPOS_BASE

    root = Path(repo_root).resolve()
    candidate = Path(repo_path).resolve()

    if candidate != root and root not in candidate.parents:
        raise SecurityError("Repository path escapes configured repository root")

    return candidate


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
    
    # Strict git branch naming rules
    if name.startswith("/") or name.endswith("/"):
        return "Branch name cannot start or end with a slash."
    if "//" in name or ".." in name or "@{" in name or "\\" in name:
        return "Branch name contains invalid character sequences."
    if name.endswith(".lock"):
        return "Branch name cannot end with .lock."
    if "refs/" in name or "refs/heads/" in name:
        return "Branch name cannot contain refs/."
    for char in ["~", "^", ":", "?", "*", "[", "\\"]:
        if char in name:
            return f"Branch name contains invalid character '{char}'."
            
    if not BRANCH_RE.match(name):
        return "Branch name contains invalid characters."
        
    import subprocess
    try:
        res = subprocess.run(["git", "check-ref-format", "--branch", name], capture_output=True)
        if res.returncode != 0:
            return "Invalid branch name."
    except Exception:
        pass

    return None


def validate_email(email: str) -> str | None:
    if not email:
        return "Email is required."
    if not EMAIL_RE.match(email):
        return "Invalid email format."
    return None


COMMON_PASSWORDS = {"password", "123456", "12345678", "qwerty", "password123"}

def validate_password(password: str) -> str | None:
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 72:
        return "Password cannot exceed 72 characters."
        
    if password.lower() in COMMON_PASSWORDS:
        return "This password is too common."
        
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_spec = any(not c.isalnum() for c in password)
    
    if not (has_upper and has_lower and has_digit and has_spec):
        return "Password must contain uppercase, lowercase, digit, and special character."
        
    return None
