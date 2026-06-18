from datetime import datetime, timezone
from ..extensions import db


class File(db.Model):
    __tablename__ = "files"

    file_id    = db.Column(db.Integer, primary_key=True)
    repo_id    = db.Column(db.Integer, db.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    file_path  = db.Column(db.String(4096), nullable=False)
    file_name  = db.Column(db.String(255),  nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("repo_id", "file_path"),)

    repository   = db.relationship("Repository", back_populates="files")
    commit_files = db.relationship("CommitFile",  back_populates="file", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "file_id":   self.file_id,
            "repo_id":   self.repo_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
        }
