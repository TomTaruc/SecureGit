from datetime import datetime, timezone
from ..extensions import db


class Repository(db.Model):
    __tablename__ = "repositories"

    repo_id         = db.Column(db.Integer, primary_key=True)
    project_id      = db.Column(db.Integer, db.ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    repo_project_id = db.Column(db.Integer, db.ForeignKey("projects.project_id"), nullable=False)
    repo_path       = db.Column(db.String(255), nullable=False, unique=True)
    clone_url       = db.Column(db.String(255), nullable=False)
    is_initialized  = db.Column(db.Boolean, nullable=False, default=False)
    created_at      = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    project          = db.relationship("Project",  back_populates="repository", foreign_keys=[project_id])
    branches         = db.relationship("Branch",   back_populates="repository", cascade="all, delete-orphan")
    files            = db.relationship("File",     back_populates="repository", cascade="all, delete-orphan")
    protection_rules = db.relationship("BranchProtectionRule", back_populates="repository", cascade="all, delete-orphan")
    tokens           = db.relationship("RepoToken", back_populates="repository", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "repo_id":        self.repo_id,
            "project_id":     self.project_id,
            "repo_path":      self.repo_path,
            "clone_url":      self.clone_url,
            "is_initialized": self.is_initialized,
            "created_at":     self.created_at.isoformat(),
        }
