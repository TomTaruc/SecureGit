from datetime import datetime, timezone
from ..extensions import db


class Project(db.Model):
    __tablename__ = "projects"

    project_id     = db.Column(db.Integer, primary_key=True)
    owner_user_id  = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_name   = db.Column(db.String(100), nullable=False)
    description    = db.Column(db.Text)
    visibility     = db.Column(db.String(10),  nullable=False, default="private")
    default_branch = db.Column(db.String(100), nullable=False, default="main")
    updated_at     = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at     = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    deleted_at     = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (db.UniqueConstraint("owner_user_id", "project_name"),)

    owner           = db.relationship("User",         back_populates="projects", foreign_keys=[owner_user_id])
    repository      = db.relationship("Repository",   back_populates="project",  uselist=False, cascade="all, delete-orphan", foreign_keys="Repository.project_id")
    collaborators   = db.relationship("Collaborator", back_populates="project",  cascade="all, delete-orphan", foreign_keys="Collaborator.project_id")
    chroot_jails    = db.relationship("ChrootJail",   back_populates="project",  cascade="all, delete-orphan")
    webhooks        = db.relationship("WebhookEndpoint", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self, with_stats: bool = False) -> dict:
        data = {
            "project_id":     self.project_id,
            "owner":          self.owner.username if self.owner else None,
            "project_name":   self.project_name,
            "description":    self.description,
            "visibility":     self.visibility,
            "default_branch": self.default_branch,
            "clone_url":      self.repository.clone_url if self.repository else None,
            "updated_at":     self.updated_at.isoformat(),
            "created_at":     self.created_at.isoformat(),
        }
        return data

from sqlalchemy import event
from ..extensions import redis_client

@event.listens_for(Project, 'after_update')
def clear_project_cache_on_update(mapper, connection, target):
    try:
        redis_client.delete(f"project:{target.project_id}")
    except Exception:
        pass

@event.listens_for(Project, 'after_delete')
def clear_project_cache_on_delete(mapper, connection, target):
    try:
        redis_client.delete(f"project:{target.project_id}")
    except Exception:
        pass
