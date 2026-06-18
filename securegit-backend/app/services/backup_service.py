"""
Backup Service — automated backup of repositories and PostgreSQL database.
"""
import os
import subprocess
import tarfile
import logging
from datetime import datetime, timezone
from typing import Optional
from ..extensions import db
from ..models.enhancement_models import BackupJob

logger = logging.getLogger(__name__)

GIT_REPOS_BASE = os.environ.get("GIT_REPOS_BASE", "/srv/git")
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_repos(dest_dir: str, job: BackupJob) -> str:
    """Tar+gz all bare repositories to destination. Returns archive path."""
    os.makedirs(dest_dir, exist_ok=True)
    archive_name = f"securegit_repos_{_timestamp()}.tar.gz"
    archive_path = os.path.join(dest_dir, archive_name)

    with tarfile.open(archive_path, "w:gz") as tar:
        if os.path.exists(GIT_REPOS_BASE):
            tar.add(GIT_REPOS_BASE, arcname="repos")

    size = os.path.getsize(archive_path)
    logger.info("Repo backup completed: %s (%d bytes)", archive_path, size)
    return archive_path, size


def backup_database(dest_dir: str) -> tuple[str, int]:
    """Run pg_dump and save to destination. Returns (archive_path, size_bytes)."""
    os.makedirs(dest_dir, exist_ok=True)
    dump_name = f"securegit_db_{_timestamp()}.sql.gz"
    dump_path = os.path.join(dest_dir, dump_name)

    import urllib.parse
    import gzip
    
    parsed = urllib.parse.urlparse(DATABASE_URL)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = ["pg_dump", "--format=custom"]
    if parsed.username:
        cmd.extend(["--username", parsed.username])
    if parsed.hostname:
        cmd.extend(["--host", parsed.hostname])
    if parsed.port:
        cmd.extend(["--port", str(parsed.port)])
    if parsed.path:
        cmd.extend(["--dbname", parsed.path.lstrip("/")])

    try:
        result = subprocess.run(
            cmd, capture_output=True, shell=False, env=env, timeout=300
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("pg_dump timed out after 300 seconds")

    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr.decode()}")
    with gzip.open(dump_path, "wb") as f:
        f.write(result.stdout)

    size = os.path.getsize(dump_path)
    logger.info("DB backup completed: %s (%d bytes)", dump_path, size)
    return dump_path, size


def run_full_backup(dest_dir: str, triggered_by: Optional[int] = None) -> BackupJob:
    """Execute a full backup (repos + DB) and record in backup_jobs table."""
    job = BackupJob(
        triggered_by=triggered_by,
        status="running",
        backup_type="full",
        destination=dest_dir,
        started_at=datetime.now(timezone.utc),
    )
    db.session.add(job)
    db.session.commit()

    try:
        repo_archive, repo_size = backup_repos(dest_dir, job)
        try:
            db_archive, db_size = backup_database(dest_dir)
            total_size = repo_size + db_size
        except Exception as e:
            logger.warning("DB backup failed (repos backup succeeded): %s", e)
            db_archive = None
            total_size = repo_size

        job.status = "completed"
        job.archive_path = repo_archive
        job.size_bytes = total_size
        job.completed_at = datetime.now(timezone.utc)
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        logger.error("Backup failed: %s", e)

    db.session.commit()
    return job


def list_backups(dest_dir: str) -> list[dict]:
    """Enumerate backup archives in destination directory."""
    if not os.path.exists(dest_dir):
        return []
    entries = []
    for fname in sorted(os.listdir(dest_dir), reverse=True):
        if fname.endswith((".tar.gz", ".sql.gz")):
            path = os.path.join(dest_dir, fname)
            entries.append({
                "filename":   fname,
                "path":       path,
                "size_bytes": os.path.getsize(path),
                "modified_at": datetime.fromtimestamp(
                    os.path.getmtime(path), tz=timezone.utc
                ).isoformat(),
            })
    return entries

def restore_backup(filename: str, dest_dir: str) -> None:
    """Restore a backup (DB or repos)."""
    path = os.path.join(dest_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Backup file not found: {path}")

    if filename.endswith(".tar.gz"):
        logger.info(f"Restoring repository backup: {path}")
        with tarfile.open(path, "r:gz") as tar:
            # We assume it contains 'repos' at the root
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
                tar.extractall(path, members, numeric_owner=numeric_owner)
            
            parent_dir = os.path.dirname(GIT_REPOS_BASE)
            safe_extract(tar, path=parent_dir)
        logger.info("Repository restore completed.")

    elif filename.endswith(".sql.gz"):
        logger.info(f"Restoring database backup: {path}")
        import urllib.parse
        import gzip
        
        parsed = urllib.parse.urlparse(DATABASE_URL)
        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password

        cmd = ["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges", "--format=custom", "--dbname", DATABASE_URL]
        
        try:
            with gzip.open(path, "rb") as f:
                result = subprocess.run(
                    cmd, input=f.read(), capture_output=True, shell=False, env=env, timeout=600
                )
        except subprocess.TimeoutExpired:
            raise RuntimeError("pg_restore timed out after 600 seconds")

        if result.returncode != 0:
            raise RuntimeError(f"pg_restore failed: {result.stderr.decode()}")
        
        logger.info("Database restore completed.")
    else:
        raise ValueError("Unsupported backup format")
