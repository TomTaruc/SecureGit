from datetime import datetime, timezone
from ..extensions import db


class Commit(db.Model):
    __tablename__ = "commits"

    commit_id           = db.Column(db.Integer, primary_key=True)
    branch_id           = db.Column(db.Integer, db.ForeignKey("branches.branch_id", ondelete="CASCADE"), nullable=False)
    author_id           = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    commit_hash         = db.Column(db.String(40), nullable=False, unique=True)
    short_hash          = db.Column(db.String(7),  nullable=False)
    message             = db.Column(db.Text, nullable=False)
    committed_at        = db.Column(db.DateTime(timezone=True), nullable=False)
    parent_hash         = db.Column(db.String(40))
    fs_commit_author_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    branch       = db.relationship("Branch", back_populates="commits")
    author       = db.relationship("User",   foreign_keys=[author_id])
    commit_files = db.relationship("CommitFile", back_populates="commit", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "commit_id":    self.commit_id,
            "commit_hash":  self.commit_hash,
            "short_hash":   self.short_hash,
            "message":      self.message,
            "author":       self.author.username if self.author else None,
            "committed_at": self.committed_at.isoformat(),
            "parent_hash":  self.parent_hash,
        }


class CommitFile(db.Model):
    __tablename__ = "commit_files"

    cf_id         = db.Column(db.Integer, primary_key=True)
    commit_id     = db.Column(db.Integer, db.ForeignKey("commits.commit_id",  ondelete="CASCADE"), nullable=False)
    file_id       = db.Column(db.Integer, db.ForeignKey("files.file_id",      ondelete="CASCADE"), nullable=False)
    change_type   = db.Column(db.String(10), nullable=False)
    lines_added   = db.Column(db.Integer, nullable=False, default=0)
    lines_deleted = db.Column(db.Integer, nullable=False, default=0)
    diff_content  = db.Column(db.Text)

    __table_args__ = (db.UniqueConstraint("commit_id", "file_id"),)

    commit = db.relationship("Commit", back_populates="commit_files")
    file   = db.relationship("File",   back_populates="commit_files")

    def to_dict(self) -> dict:
        return {
            "file_path":     self.file.file_path if self.file else None,
            "change_type":   self.change_type,
            "lines_added":   self.lines_added,
            "lines_deleted": self.lines_deleted,
        }
