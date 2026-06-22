"""
Merge Service — safe merge, compare, and conflict detection.
All git operations run via subprocess (no shell=True).
"""
import logging
import tempfile
import os
import shutil
import subprocess
import uuid
import fcntl
import json
from contextlib import contextmanager
from typing import Optional
from .git_service import (
    _safe_ref, _run, git_rev_list_count, git_merge_base,
    git_diff_branches, git_is_ancestor,
)

logger = logging.getLogger(__name__)

def _worktree_dir(repo_path: str) -> str:
    base = os.path.join(os.path.dirname(repo_path), ".worktrees")
    os.makedirs(base, exist_ok=True)
    try:
        import pwd
        git_pwd = pwd.getpwnam("git")
        os.chown(base, git_pwd.pw_uid, git_pwd.pw_gid)
    except Exception:
        pass
    try:
        os.chmod(base, 0o777)
    except Exception:
        pass
    return os.path.join(base, f"wt-{uuid.uuid4().hex}")


@contextmanager
def branch_lock(repo_path: str, target: str):
    """File-based lock for a specific target branch in a repository."""
    base = os.path.join(os.path.dirname(repo_path), ".locks")
    os.makedirs(base, exist_ok=True)
    # create a safe filename for the lock
    safe_target = target.replace('/', '_')
    repo_id = os.path.basename(repo_path.rstrip('/'))
    lock_file = os.path.join(base, f"merge-{repo_id}-{safe_target}.lock")
    
    fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _get_branch_sha(repo_path: str, branch: str) -> str:
    try:
        out = _run(repo_path, "rev-parse", _safe_ref(f"refs/heads/{branch}"))
        return out.strip()
    except RuntimeError:
        return ""

def _cleanup_worktree(repo_path: str, tmp_dir: str):
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", tmp_dir],
            cwd=repo_path, capture_output=True, shell=False,
            user="git", group="git"
        )
    except Exception:
        pass
    try:
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=repo_path, capture_output=True, shell=False,
            user="git", group="git"
        )
    except Exception:
        pass
    shutil.rmtree(tmp_dir, ignore_errors=True)

def compare_branches(repo_path: str, base: str, head: str) -> dict:
    """
    Compare two branches. Returns ahead/behind counts, merge base,
    and the list of commits in head that are not in base.
    """
    ahead, behind = git_rev_list_count(repo_path, head, base)
    try:
        merge_base = git_merge_base(repo_path, base, head)
    except RuntimeError:
        merge_base = None

    ff_possible = git_is_ancestor(repo_path, base, head)
    
    base_sha = _get_branch_sha(repo_path, base)
    head_sha = _get_branch_sha(repo_path, head)

    # Commits in head not in base
    try:
        out = _run(
            repo_path,
            "log", f"{_safe_ref(base)}..{_safe_ref(head)}",
            "--format=%H|%h|%s|%an|%ci",
        )
        commits = []
        for line in out.splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0], "short_hash": parts[1],
                    "message": parts[2], "author": parts[3], "date": parts[4],
                })
    except RuntimeError:
        commits = []

    return {
        "base":       base,
        "head":       head,
        "base_sha":   base_sha,
        "head_sha":   head_sha,
        "ahead":      ahead,
        "behind":     behind,
        "merge_base_sha": merge_base,
        "commits":    commits,
        "diff":       git_diff_branches(repo_path, base, head),
        "fast_forward": {
            "available": ff_possible,
            "reason": None if ff_possible else "branches have diverged"
        },
        "squash": {
            "available": True,
            "reason": None
        },
        "rebase": {
            "available": True,
            "reason": None
        },
        "merge_commit": {
            "available": True,
            "reason": None
        },
        "ff_possible": ff_possible, # legacy
    }


def branch_divergence(repo_path: str, base: str, head: str) -> dict:
    ahead, behind = git_rev_list_count(repo_path, head, base)
    return {"base": base, "head": head, "ahead": ahead, "behind": behind}


def detect_conflicts(repo_path: str, base: str, head: str) -> list[dict]:
    """
    Attempt a dry-run merge in a temporary worktree to detect conflicts.
    Returns list of conflicting file paths (empty = no conflicts).
    """
    base_sha = _get_branch_sha(repo_path, base)
    head_sha = _get_branch_sha(repo_path, head)
    if not base_sha or not head_sha:
        return []

    tmp_dir = _worktree_dir(repo_path)
    conflicts = []
    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", tmp_dir, base_sha],
            cwd=repo_path, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        result = subprocess.run(
            ["git", "merge", "--no-commit", "--no-ff", head_sha],
            cwd=tmp_dir, capture_output=True, text=True, shell=False,
            user="git", group="git"
        )
        if result.returncode != 0:
            status = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=tmp_dir, capture_output=True, text=True, shell=False,
                user="git", group="git"
            )
            for fname in status.stdout.splitlines():
                fname = fname.strip()
                file_path = os.path.join(tmp_dir, fname)
                content = ""
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                except Exception:
                    pass
                conflicts.append({"file": fname, "type": "content", "content": content})
        subprocess.run(
            ["git", "merge", "--abort"],
            cwd=tmp_dir, capture_output=True, shell=False,
            user="git", group="git"
        )
    except Exception as e:
        logger.error("Conflict detection failed: %s", e)
    finally:
        _cleanup_worktree(repo_path, tmp_dir)
    return conflicts


def fast_forward_merge(repo_path: str, target: str, source: str, user_id: int) -> dict:
    """
    Attempt a fast-forward merge of source into target.
    Does not use a worktree. Updates refs atomically.
    """
    with branch_lock(repo_path, target):
        target_sha = _get_branch_sha(repo_path, target)
        source_sha = _get_branch_sha(repo_path, source)
        
        if not target_sha or not source_sha:
            return {"success": False, "ok": False, "error": "Invalid branch references"}

        if not git_is_ancestor(repo_path, target_sha, source_sha):
            return {
                "success": False, "ok": False, 
                "code": "FAST_FORWARD_NOT_POSSIBLE",
                "error": "Cannot fast-forward because the target branch is not an ancestor of the source branch.",
                "message": "Cannot fast-forward because the target branch is not an ancestor of the source branch.",
                "details": {"target": target, "source": source, "target_sha": target_sha, "source_sha": source_sha}
            }

        try:
            # Atomic update
            _run(repo_path, "update-ref", f"refs/heads/{target}", source_sha, target_sha)
            return {
                "success": True, "ok": True, "strategy": "fast-forward",
                "target": target, "source": source, "old_target_sha": target_sha,
                "source_sha": source_sha, "new_target_sha": source_sha,
                "message": "Fast-forward merge completed successfully."
            }
        except RuntimeError as e:
            return {"success": False, "ok": False, "error": str(e)}


def squash_merge(repo_path: str, target: str, source: str, message: str, user_id: int) -> dict:
    """Squash all commits from source and create a single merge commit on target."""
    tmp_dir = _worktree_dir(repo_path)
    
    with branch_lock(repo_path, target):
        target_sha = _get_branch_sha(repo_path, target)
        source_sha = _get_branch_sha(repo_path, source)
        
        if not target_sha or not source_sha:
            return {"success": False, "ok": False, "error": "Invalid branch references"}
            
        try:
            subprocess.run(
                ["git", "worktree", "add", "--detach", tmp_dir, target_sha],
                cwd=repo_path, check=True, capture_output=True, shell=False,
                user="git", group="git"
            )
            subprocess.run(["git", "config", "user.name", "SecureGit"], cwd=tmp_dir, check=True, user="git", group="git")
            subprocess.run(["git", "config", "user.email", "securegit@local"], cwd=tmp_dir, check=True, user="git", group="git")
            
            result = subprocess.run(
                ["git", "merge", "--squash", source_sha],
                cwd=tmp_dir, capture_output=True, text=True, shell=False,
                user="git", group="git"
            )
            if result.returncode != 0:
                status = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=U"],
                    cwd=tmp_dir, capture_output=True, text=True, shell=False,
                    user="git", group="git"
                )
                conflicting_files = [f.strip() for f in status.stdout.splitlines() if f.strip()]
                return {
                    "success": False, "ok": False, "code": "MERGE_CONFLICT",
                    "message": "Merge conflict detected.", "strategy": "squash",
                    "target": target, "source": source, "files": conflicting_files
                }
                
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=tmp_dir, check=True, capture_output=True, shell=False,
                user="git", group="git"
            )
            
            new_sha = _run(tmp_dir, "rev-parse", "HEAD").strip()
            
            # Atomic ref update
            _run(repo_path, "update-ref", f"refs/heads/{target}", new_sha, target_sha)
            
            return {
                "success": True, "ok": True, "strategy": "squash",
                "target": target, "source": source, "old_target_sha": target_sha,
                "source_sha": source_sha, "new_target_sha": new_sha,
                "message": "Squash merge completed successfully."
            }
        except Exception as e:
            return {"success": False, "ok": False, "error": str(e)}
        finally:
            _cleanup_worktree(repo_path, tmp_dir)


def rebase_merge(repo_path: str, target: str, source: str, user_id: int) -> dict:
    """Rebase source onto target and fast-forward target."""
    tmp_dir = _worktree_dir(repo_path)
    branch_name = f"securegit-rebase-{uuid.uuid4().hex}"
    
    with branch_lock(repo_path, target):
        target_sha = _get_branch_sha(repo_path, target)
        source_sha = _get_branch_sha(repo_path, source)
        merge_base_sha = git_merge_base(repo_path, target_sha, source_sha)
        
        if not target_sha or not source_sha or not merge_base_sha:
            return {"success": False, "ok": False, "error": "Invalid branch references"}

        try:
            subprocess.run(
                ["git", "worktree", "add", "--detach", tmp_dir, source_sha],
                cwd=repo_path, check=True, capture_output=True, shell=False,
                user="git", group="git"
            )
            subprocess.run(["git", "config", "user.name", "SecureGit"], cwd=tmp_dir, check=True, user="git", group="git")
            subprocess.run(["git", "config", "user.email", "securegit@local"], cwd=tmp_dir, check=True, user="git", group="git")
            
            subprocess.run(
                ["git", "checkout", "-B", branch_name, source_sha],
                cwd=tmp_dir, check=True, capture_output=True, shell=False,
                user="git", group="git"
            )
            
            result = subprocess.run(
                ["git", "rebase", "--onto", target_sha, merge_base_sha, branch_name],
                cwd=tmp_dir, capture_output=True, text=True, shell=False,
                user="git", group="git"
            )
            
            if result.returncode != 0:
                subprocess.run(["git", "rebase", "--abort"], cwd=tmp_dir, capture_output=True, shell=False, user="git", group="git")
                return {
                    "success": False, "ok": False, "code": "MERGE_CONFLICT",
                    "message": "Rebase conflict detected.", "strategy": "rebase",
                    "target": target, "source": source, "files": []
                }
                
            new_sha = _run(tmp_dir, "rev-parse", "HEAD").strip()
            
            # Atomic ref update
            _run(repo_path, "update-ref", f"refs/heads/{target}", new_sha, target_sha)
            
            return {
                "success": True, "ok": True, "strategy": "rebase",
                "target": target, "source": source, "old_target_sha": target_sha,
                "source_sha": source_sha, "new_target_sha": new_sha,
                "message": "Rebase merge completed successfully."
            }
        except Exception as e:
            return {"success": False, "ok": False, "error": str(e)}
        finally:
            try:
                subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, capture_output=True, shell=False, user="git", group="git")
            except Exception:
                pass
            _cleanup_worktree(repo_path, tmp_dir)
