"""
Merge Service — safe merge, compare, and conflict detection.
All git operations run via subprocess (no shell=True).
"""
import logging
import tempfile
import os
import shutil
import subprocess
from typing import Optional
from .git_service import (
    _safe_ref, _run, git_rev_list_count, git_merge_base,
    git_diff_branches, git_is_ancestor,
)

logger = logging.getLogger(__name__)


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
        "ahead":      ahead,
        "behind":     behind,
        "merge_base": merge_base,
        "commits":    commits,
        "diff":       git_diff_branches(repo_path, base, head),
    }


def branch_divergence(repo_path: str, base: str, head: str) -> dict:
    ahead, behind = git_rev_list_count(repo_path, head, base)
    return {"base": base, "head": head, "ahead": ahead, "behind": behind}


def detect_conflicts(repo_path: str, base: str, head: str) -> list[dict]:
    """
    Attempt a dry-run merge in a temporary worktree to detect conflicts.
    Returns list of conflicting file paths (empty = no conflicts).
    """
    tmp_dir = tempfile.mkdtemp(prefix="securegit-merge-")
    conflicts = []
    try:
        subprocess.run(
            ["git", "worktree", "add", tmp_dir, _safe_ref(base)],
            cwd=repo_path, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        result = subprocess.run(
            ["git", "merge", "--no-commit", "--no-ff", _safe_ref(head)],
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
        subprocess.run(
            ["git", "worktree", "remove", "--force", tmp_dir],
            cwd=repo_path, capture_output=True, shell=False,
            user="git", group="git"
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return conflicts


def fast_forward_merge(repo_path: str, target: str, source: str) -> dict:
    """
    Attempt a fast-forward merge of source into target.
    Only succeeds if target is an ancestor of source.
    """
    if not git_is_ancestor(repo_path, target, source):
        return {"success": False, "error": "Cannot fast-forward: branches have diverged."}

    tmp_dir = tempfile.mkdtemp(prefix="securegit-ff-")
    try:
        subprocess.run(
            ["git", "worktree", "add", tmp_dir, _safe_ref(target)],
            cwd=repo_path, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        result = subprocess.run(
            ["git", "merge", "--ff-only", _safe_ref(source)],
            cwd=tmp_dir, capture_output=True, text=True, shell=False,
            user="git", group="git"
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}
        # Push the result back to the bare repo
        subprocess.run(
            ["git", "push", repo_path, _safe_ref(target)],
            cwd=tmp_dir, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        return {"success": True, "strategy": "fast-forward"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", tmp_dir],
            cwd=repo_path, capture_output=True, shell=False,
            user="git", group="git"
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)


def squash_merge(repo_path: str, target: str, source: str, message: str) -> dict:
    """Squash all commits from source and create a single merge commit on target."""
    tmp_dir = tempfile.mkdtemp(prefix="securegit-squash-")
    try:
        subprocess.run(
            ["git", "worktree", "add", tmp_dir, _safe_ref(target)],
            cwd=repo_path, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        result = subprocess.run(
            ["git", "merge", "--squash", _safe_ref(source)],
            cwd=tmp_dir, capture_output=True, text=True, shell=False,
            user="git", group="git"
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=tmp_dir, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        subprocess.run(
            ["git", "push", repo_path, _safe_ref(target)],
            cwd=tmp_dir, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        return {"success": True, "strategy": "squash"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", tmp_dir],
            cwd=repo_path, capture_output=True, shell=False,
            user="git", group="git"
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)


def rebase_merge(repo_path: str, target: str, source: str) -> dict:
    """Rebase source onto target and fast-forward target."""
    tmp_dir = tempfile.mkdtemp(prefix="securegit-rebase-")
    try:
        subprocess.run(
            ["git", "worktree", "add", tmp_dir, _safe_ref(source)],
            cwd=repo_path, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        result = subprocess.run(
            ["git", "rebase", _safe_ref(target)],
            cwd=tmp_dir, capture_output=True, text=True, shell=False,
            user="git", group="git"
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip() or "Rebase conflict detected."}
        subprocess.run(
            ["git", "checkout", _safe_ref(target)],
            cwd=tmp_dir, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        subprocess.run(
            ["git", "merge", "--ff-only", _safe_ref(source)],
            cwd=tmp_dir, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        subprocess.run(
            ["git", "push", repo_path, _safe_ref(target)],
            cwd=tmp_dir, check=True, capture_output=True, shell=False,
            user="git", group="git"
        )
        return {"success": True, "strategy": "rebase"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", tmp_dir],
            cwd=repo_path, capture_output=True, shell=False,
            user="git", group="git"
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)
