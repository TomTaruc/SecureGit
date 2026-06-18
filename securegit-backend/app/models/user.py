from datetime import datetime, timezone
from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    user_id       = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="dev")
    is_suspended  = db.Column(db.Boolean, nullable=False, default=False)
    fingerprint   = db.Column(db.String(255))
    last_login    = db.Column(db.DateTime(timezone=True))
    created_at    = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    ssh_keys      = db.relationship("SSHKey",      back_populates="user", cascade="all, delete-orphan")
    projects      = db.relationship("Project",     back_populates="owner", cascade="all, delete-orphan", foreign_keys="Project.owner_user_id")
    collaborations = db.relationship("Collaborator", back_populates="user", cascade="all, delete-orphan", foreign_keys="Collaborator.user_id")
    audit_entries = db.relationship("AuditLog",    back_populates="actor", foreign_keys="AuditLog.actor_id")

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "user_id":      self.user_id,
            "username":     self.username,
            "email":        self.email,
            "role":         self.role,
            "is_suspended": self.is_suspended,
            "last_login":   self.last_login.isoformat() if self.last_login else None,
            "created_at":   self.created_at.isoformat(),
        }
        if include_sensitive:
            data["fingerprint"] = self.fingerprint
        return data

    def __repr__(self) -> str:
        return f"<User {self.username}>"
