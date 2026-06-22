from datetime import datetime, timezone
from ..extensions import db


class RepoToken(db.Model):
    __tablename__ = "repo_tokens"

    token_id     = db.Column(db.Integer, primary_key=True)
    repo_id      = db.Column(db.Integer, db.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.user_id",        ondelete="CASCADE"), nullable=False)
    name         = db.Column(db.String(100), nullable=False)
    token_hash   = db.Column(db.String(255), nullable=False, unique=True)
    scopes       = db.Column(db.JSON, nullable=False, default=lambda: ["read"])
    expires_at   = db.Column(db.DateTime(timezone=True))
    last_used_at = db.Column(db.DateTime(timezone=True))
    created_at   = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    repository = db.relationship("Repository", back_populates="tokens")
    user       = db.relationship("User")

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> dict:
        return {
            "token_id":    self.token_id,
            "repo_id":     self.repo_id,
            "name":        self.name,
            "scopes":      self.scopes,
            "expires_at":  self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at":self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at":  self.created_at.isoformat(),
            "is_expired":  self.is_expired(),
        }


class BackupJob(db.Model):
    __tablename__ = "backup_jobs"

    job_id        = db.Column(db.Integer, primary_key=True)
    triggered_by  = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    status        = db.Column(db.String(20), nullable=False, default="pending")
    backup_type   = db.Column(db.String(20), nullable=False, default="full")
    destination   = db.Column(db.String(255), nullable=False)
    archive_path  = db.Column(db.String(255))
    size_bytes    = db.Column(db.BigInteger)
    error_message = db.Column(db.Text)
    started_at    = db.Column(db.DateTime(timezone=True))
    completed_at  = db.Column(db.DateTime(timezone=True))
    created_at    = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    triggered_by_user = db.relationship("User", foreign_keys=[triggered_by])

    def to_dict(self) -> dict:
        return {
            "job_id":         self.job_id,
            "triggered_by":   self.triggered_by_user.username if self.triggered_by_user else "scheduler",
            "status":         self.status,
            "backup_type":    self.backup_type,
            "destination":    self.destination,
            "archive_path":   self.archive_path,
            "size_bytes":     self.size_bytes,
            "error_message":  self.error_message,
            "started_at":     self.started_at.isoformat() if self.started_at else None,
            "completed_at":   self.completed_at.isoformat() if self.completed_at else None,
            "created_at":     self.created_at.isoformat(),
        }


class WebhookEndpoint(db.Model):
    __tablename__ = "webhook_endpoints"

    webhook_id            = db.Column(db.Integer, primary_key=True)
    project_id            = db.Column(db.Integer, db.ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    name                  = db.Column(db.String(100), nullable=False)
    target_url            = db.Column(db.String(512), nullable=False)
    events                = db.Column(db.JSON, nullable=False, default=lambda: ["push"])
    secret_hash           = db.Column(db.String(255))
    is_active             = db.Column(db.Boolean, nullable=False, default=True)
    last_delivery_at      = db.Column(db.DateTime(timezone=True))
    last_delivery_status  = db.Column(db.Integer)
    created_at            = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    project = db.relationship("Project", back_populates="webhooks")

    def to_dict(self) -> dict:
        return {
            "webhook_id":           self.webhook_id,
            "project_id":           self.project_id,
            "name":                 self.name,
            "target_url":           self.target_url,
            "events":               self.events,
            "is_active":            self.is_active,
            "secret":               "••••••••" if self.secret_hash else None,
            "last_delivery_at":     self.last_delivery_at.isoformat() if self.last_delivery_at else None,
            "last_delivery_status": self.last_delivery_status,
            "created_at":           self.created_at.isoformat(),
        }


class ServerConfig(db.Model):
    __tablename__ = "server_config"

    config_id   = db.Column(db.Integer, primary_key=True)
    key         = db.Column(db.String(100), nullable=False, unique=True)
    value       = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at  = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_by  = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    def to_dict(self) -> dict:
        return {
            "key":         self.key,
            "value":       self.value,
            "description": self.description,
            "updated_at":  self.updated_at.isoformat(),
        }
