from datetime import datetime, timezone
from ..extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    log_id      = db.Column(db.Integer, primary_key=True)
    actor_id    = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    action      = db.Column(db.String(100), nullable=False)
    target_id   = db.Column(db.Integer)
    target_type = db.Column(db.String(50))
    detail      = db.Column(db.Text)
    ip_address  = db.Column(db.String(45))
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    actor = db.relationship("User", back_populates="audit_entries", foreign_keys=[actor_id])

    def to_dict(self) -> dict:
        return {
            "log_id":      self.log_id,
            "actor":       self.actor.username if self.actor else None,
            "action":      self.action,
            "target_id":   self.target_id,
            "target_type": self.target_type,
            "detail":      self.detail,
            "ip_address":  self.ip_address,
            "occurred_at": self.occurred_at.isoformat(),
        }
