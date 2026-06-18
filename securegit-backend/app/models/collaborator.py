from datetime import datetime, timezone
from ..extensions import db

# Default RBAC permissions (read-only collaborator)
DEFAULT_PERMISSIONS = {
    "read":                 True,
    "push":                 False,
    "create_branch":        False,
    "delete_branch":        False,
    "manage_collaborators": False,
    "manage_settings":      False,
    "admin":                False,
}

WRITE_PERMISSIONS = {
    "read": True, "push": True, "create_branch": True,
    "delete_branch": False, "manage_collaborators": False,
    "manage_settings": False, "admin": False,
}

ADMIN_PERMISSIONS = {
    "read": True, "push": True, "create_branch": True,
    "delete_branch": True, "manage_collaborators": True,
    "manage_settings": True, "admin": True,
}

PERMISSION_PRESETS = {
    "read":  DEFAULT_PERMISSIONS,
    "write": WRITE_PERMISSIONS,
    "admin": ADMIN_PERMISSIONS,
}


class Collaborator(db.Model):
    __tablename__ = "collaborators"

    collab_id            = db.Column(db.Integer, primary_key=True)
    project_id           = db.Column(db.Integer, db.ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    user_id              = db.Column(db.Integer, db.ForeignKey("users.user_id",       ondelete="CASCADE"), nullable=False)
    permission           = db.Column(db.String(20), nullable=False, default="read")  # legacy simple level
    permissions          = db.Column(db.JSON, nullable=False, default=lambda: dict(DEFAULT_PERMISSIONS))
    granted_at           = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    fs_collab_project_id = db.Column(db.Integer, db.ForeignKey("projects.project_id"))
    fs_collab_user_id    = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    __table_args__ = (db.UniqueConstraint("project_id", "user_id"),)

    project = db.relationship("Project",     back_populates="collaborators", foreign_keys=[project_id])
    user    = db.relationship("User",        back_populates="collaborations", foreign_keys=[user_id])

    def has_permission(self, perm: str) -> bool:
        """Check a single RBAC permission flag."""
        return bool(self.permissions.get(perm, False))

    def to_dict(self) -> dict:
        return {
            "collab_id":   self.collab_id,
            "project_id":  self.project_id,
            "user_id":     self.user_id,
            "username":    self.user.username if self.user else None,
            "email":       self.user.email if self.user else None,
            "permission":  self.permission,
            "permissions": self.permissions,
            "granted_at":  self.granted_at.isoformat(),
        }
