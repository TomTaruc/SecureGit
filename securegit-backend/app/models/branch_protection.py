from datetime import datetime, timezone
from ..extensions import db


class BranchProtectionRule(db.Model):
    __tablename__ = "branch_protection_rules"

    rule_id               = db.Column(db.Integer, primary_key=True)
    repo_id               = db.Column(db.Integer, db.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    branch_pattern        = db.Column(db.String(255), nullable=False)
    disable_force_push    = db.Column(db.Boolean, nullable=False, default=True)
    disable_deletion      = db.Column(db.Boolean, nullable=False, default=True)
    restrict_push         = db.Column(db.Boolean, nullable=False, default=False)
    allowed_push_roles    = db.Column(db.JSON, nullable=False, default=lambda: ["admin"])
    require_admin_for_push= db.Column(db.Boolean, nullable=False, default=False)
    require_linear_history= db.Column(db.Boolean, nullable=False, default=False)
    created_at            = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at            = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("repo_id", "branch_pattern"),)

    repository = db.relationship("Repository", back_populates="protection_rules")

    def to_dict(self) -> dict:
        return {
            "rule_id":                self.rule_id,
            "repo_id":                self.repo_id,
            "branch_pattern":         self.branch_pattern,
            "disable_force_push":     self.disable_force_push,
            "disable_deletion":       self.disable_deletion,
            "restrict_push":          self.restrict_push,
            "allowed_push_roles":     self.allowed_push_roles,
            "require_admin_for_push": self.require_admin_for_push,
            "require_linear_history": self.require_linear_history,
            "created_at":             self.created_at.isoformat(),
            "updated_at":             self.updated_at.isoformat(),
        }
