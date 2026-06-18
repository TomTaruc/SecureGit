from datetime import datetime, timezone
from ..extensions import db


class ChrootJail(db.Model):
    __tablename__ = "chroot_jails"

    jail_id      = db.Column(db.Integer, primary_key=True)
    project_id   = db.Column(db.Integer, db.ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.user_id",       ondelete="CASCADE"), nullable=False)
    jail_path    = db.Column(db.String(255), nullable=False, unique=True)
    fs_jail_user = db.Column(db.String(50),  nullable=False)
    status       = db.Column(db.String(20),  nullable=False, default="active")
    created_at   = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    project = db.relationship("Project", back_populates="chroot_jails")
    user    = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "jail_id":      self.jail_id,
            "user":         self.user.username if self.user else None,
            "jail_path":    self.jail_path,
            "fs_jail_user": self.fs_jail_user,
            "status":       self.status,
            "created_at":   self.created_at.isoformat(),
        }
