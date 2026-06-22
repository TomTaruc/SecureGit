"""Post-Receive Synchronization Service"""
import os
from datetime import datetime, timezone
from ..extensions import db
from ..models.user import User
from ..models.repository import Repository
from ..models.branch import Branch
from ..models.commit import Commit
from ..services import git_service

def handle_post_receive(repo_path: str, oldrev: str, newrev: str, ref: str) -> dict:
    if not ref.startswith("refs/heads/"):
        return {"success": True, "message": "Non-branch ref, skipping.", "synced": 0}
    branch_name = ref[len("refs/heads/"):]

    if not os.path.isabs(repo_path) or ".." in repo_path:
        raise ValueError("invalid_path")

    repo = Repository.query.filter_by(repo_path=repo_path).first()
    if not repo:
        raise ValueError("repo_not_found")

    project = repo.project
    project.updated_at = datetime.now(timezone.utc)

    is_first_branch = Branch.query.filter_by(repo_id=repo.repo_id).count() == 0
    branch = Branch.query.filter_by(repo_id=repo.repo_id, branch_name=branch_name).first()
    if not branch:
        is_default = is_first_branch or (branch_name == project.default_branch)
        branch = Branch(
            repo_id=repo.repo_id,
            branch_name=branch_name,
            is_default=is_default,
        )
        db.session.add(branch)
        db.session.flush()

        if is_first_branch:
            project.default_branch = branch_name
            try:
                git_service.git_set_default_branch(repo_path, branch_name)
            except Exception:
                pass

    try:
        if oldrev == "0" * 40:
            commits = git_service.git_log(repo_path, branch_name, limit=100)
        else:
            raw = git_service._run(repo_path, "log",
                f"{oldrev}..{newrev}",
                f"--format={git_service.LOG_FORMAT}",
            )
            commits = []
            for line in raw.splitlines():
                parts = line.split("|", 6)
                if len(parts) >= 6:
                    commits.append({
                        "hash": parts[0], "short_hash": parts[1],
                        "author_name": parts[2], "author_email": parts[3],
                        "message": parts[4], "date": parts[5],
                        "parent_hash": parts[6] if len(parts) > 6 else None,
                    })
    except RuntimeError:
        commits = []

    synced = 0
    for c in commits:
        if Commit.query.filter_by(commit_hash=c["hash"]).first():
            continue
        author = User.query.filter_by(email=c["author_email"]).first()
        commit = Commit(
            branch_id=branch.branch_id,
            author_id=author.user_id if author else project.owner_user_id,
            commit_hash=c["hash"],
            short_hash=c["short_hash"],
            message=c["message"],
            committed_at=c["date"],
            parent_hash=c.get("parent_hash"),
        )
        db.session.add(commit)
        synced += 1

    db.session.commit()

    from ..tasks import async_post_receive_task
    payload = {
        "project_id": project.project_id,
        "username": "unknown", 
        "refs": [{
            "ref_name": ref,
            "old_sha": oldrev,
            "new_sha": newrev
        }]
    }
    async_post_receive_task.delay(payload)

    return {"success": True, "message": f"Synced {synced} commits on {branch_name}.", "synced": synced}
