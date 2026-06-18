from datetime import datetime, timezone
from ..extensions import db


class SSHKey(db.Model):
    __tablename__ = "ssh_keys"

    key_id       = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title        = db.Column(db.String(100), nullable=False)
    key_type     = db.Column(db.String(20),  nullable=False)
    public_key   = db.Column(db.Text,        nullable=False, unique=True)
    fingerprint  = db.Column(db.String(255), nullable=False, unique=True)
    added_at     = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", back_populates="ssh_keys")

    def to_dict(self) -> dict:
        return {
            "key_id":       self.key_id,
            "user_id":      self.user_id,
            "title":        self.title,
            "key_type":     self.key_type,
            "fingerprint":  self.fingerprint,
            "added_at":     self.added_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
