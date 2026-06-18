from datetime import datetime, timezone
from ..extensions import db


class Branch(db.Model):
    __tablename__ = "branches"

    branch_id   = db.Column(db.Integer, primary_key=True)
    repo_id     = db.Column(db.Integer, db.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    branch_name = db.Column(db.String(255), nullable=False)
    is_default  = db.Column(db.Boolean, nullable=False, default=False)
    is_locked   = db.Column(db.Boolean, nullable=False, default=False)
    created_at  = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("repo_id", "branch_name"),)

    repository = db.relationship("Repository", back_populates="branches")
    commits    = db.relationship("Commit",     back_populates="branch", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "branch_id":   self.branch_id,
            "repo_id":     self.repo_id,
            "branch_name": self.branch_name,
            "is_default":  self.is_default,
            "is_locked":   self.is_locked,
            "created_at":  self.created_at.isoformat(),
        }
