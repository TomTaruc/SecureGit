"""
Git Service — subprocess wrappers for all git operations.
All inputs are sanitized before being passed to subprocess.
Never uses shell=True.
"""
import os
import re
import subprocess
from typing import Optional

SAFE_REF = re.compile(r'^[a-zA-Z0-9._\-/]+$')
SAFE_HASH = re.compile(r'^[a-fA-F0-9]{4,64}$')
SAFE_PATH = re.compile(r'^[a-zA-Z0-9._\-/]+$')


def _safe_ref(value: str, allow_empty: bool = False) -> str:
    if allow_empty and not value:
        return value
    if not SAFE_REF.match(value):
        raise ValueError(f"Unsafe git ref: {value!r}")
    return value


def _safe_hash(value: str) -> str:
    if not SAFE_HASH.match(value):
        raise ValueError(f"Unsafe commit hash: {value!r}")
    return value


def _safe_path(value: str) -> str:
    if value == "":
        return value
    if ".." in value or "//" in value:
        raise ValueError(f"Unsafe file path (traversal blocked): {value!r}")
    if not SAFE_PATH.match(value):
        raise ValueError(f"Unsafe file path: {value!r}")
    return value


def _run(repo_path: str, *args, timeout: int = 30) -> str:
    """Execute a git command inside repo_path, return stdout on success."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        user="git",
        group="git",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


# ---------------------------------------------------------------------------
# Repository lifecycle
# ---------------------------------------------------------------------------

def git_init_bare(path: str) -> None:
    """Initialize a bare repository at the given path."""
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", path],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
        user="git",
        group="git",
    )
    
    # Install hooks
    hooks_dir = os.path.join(path, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    import pwd
    git_pwd = pwd.getpwnam("git")
    os.chown(hooks_dir, git_pwd.pw_uid, git_pwd.pw_gid)
    
    pre_receive_path = os.path.join(hooks_dir, "pre-receive")
    with open(pre_receive_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("while read oldrev newrev refname; do\n")
        f.write("    resp=$(curl -s -w \"\\n%{http_code}\" -X POST http://127.0.0.1:5000/api/internal/hook/pre-receive \\\n")
        f.write("      -H \"Content-Type: application/json\" \\\n")
        f.write("      -H \"X-Hook-Secret: $INTERNAL_HOOK_SECRET\" \\\n")
        f.write("      -d \"{\\\"repo_path\\\": \\\"$PWD\\\", \\\"oldrev\\\": \\\"$oldrev\\\", \\\"newrev\\\": \\\"$newrev\\\", \\\"ref\\\": \\\"$refname\\\", \\\"user_id\\\": \\\"$SECUREGIT_USER_ID\\\", \\\"git_env\\\": {\\\"GIT_QUARANTINE_PATH\\\": \\\"$GIT_QUARANTINE_PATH\\\", \\\"GIT_OBJECT_DIRECTORY\\\": \\\"$GIT_OBJECT_DIRECTORY\\\", \\\"GIT_ALTERNATE_OBJECT_DIRECTORIES\\\": \\\"$GIT_ALTERNATE_OBJECT_DIRECTORIES\\\"}}\")\n")
        f.write("    http_code=$(echo \"$resp\" | tail -n1)\n")
        f.write("    body=$(echo \"$resp\" | sed '$d')\n")
        f.write("    if [ \"$http_code\" -ne 200 ]; then\n")
        f.write("        echo \"$body\" >&2\n")
        f.write("        exit 1\n")
        f.write("    fi\n")
        f.write("done\n")
        f.write("exit 0\n")
    os.chmod(pre_receive_path, 0o755)
    os.chown(pre_receive_path, git_pwd.pw_uid, git_pwd.pw_gid)
    
    post_receive_path = os.path.join(hooks_dir, "post-receive")
    with open(post_receive_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("while read oldrev newrev refname; do\n")
        f.write("    curl -s -f -X POST http://127.0.0.1:5000/api/internal/hook/post-receive \\\n")
        f.write("      -H \"Content-Type: application/json\" \\\n")
        f.write("      -H \"X-Hook-Secret: $INTERNAL_HOOK_SECRET\" \\\n")
        f.write("      -d \"{\\\"repo_path\\\": \\\"$PWD\\\", \\\"oldrev\\\": \\\"$oldrev\\\", \\\"newrev\\\": \\\"$newrev\\\", \\\"ref\\\": \\\"$refname\\\"}\" > /dev/null\n")
        f.write("done\n")
    os.chmod(post_receive_path, 0o755)
    os.chown(post_receive_path, git_pwd.pw_uid, git_pwd.pw_gid)


def git_count_objects(repo_path: str) -> dict:
    """Return repository size stats."""
    out = _run(repo_path, "count-objects", "-vH")
    stats = {}
    for line in out.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            stats[k.strip()] = v.strip()
    return stats


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

def git_branches(repo_path: str) -> list[dict]:
    """List all branches with their tip commit hash."""
    fmt = "%(refname:short)|%(objectname:short)|%(objectname)|%(committerdate:iso8601)"
    out = _run(repo_path, "for-each-ref", f"--format={fmt}", "refs/heads/")
    branches = []
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) == 4:
            branches.append({
                "name":       parts[0],
                "short_hash": parts[1],
                "hash":       parts[2],
                "date":       parts[3],
            })
    return branches


def git_create_branch(repo_path: str, new_branch: str, from_branch: str) -> None:
    _run(repo_path, "branch", _safe_ref(new_branch), _safe_ref(from_branch))


def git_delete_branch(repo_path: str, branch: str) -> None:
    _run(repo_path, "branch", "-D", _safe_ref(branch))


def git_default_branch(repo_path: str) -> str:
    """Return the current HEAD branch name."""
    try:
        out = _run(repo_path, "symbolic-ref", "--short", "HEAD")
        return out.strip()
    except RuntimeError:
        return "main"


def git_set_default_branch(repo_path: str, branch_name: str) -> None:
    """Set the HEAD reference to the specified branch."""
    _run(repo_path, "symbolic-ref", "HEAD", f"refs/heads/{_safe_ref(branch_name)}")


# ---------------------------------------------------------------------------
# Commit log
# ---------------------------------------------------------------------------

LOG_FORMAT = "%H|%h|%an|%ae|%s|%cI|%P"


def git_log(
    repo_path: str,
    branch: str,
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    skip: int = 0,
    limit: int = 30,
    query: Optional[str] = None,
) -> list[dict]:
    """Return parsed commit log for a branch."""
    args = [
        "log",
        _safe_ref(branch),
        f"--format={LOG_FORMAT}",
        f"--skip={skip}",
        f"--max-count={limit}",
    ]
    if author:
        args += [f"--author={author}"]
    if since:
        args += [f"--since={since}"]
    if until:
        args += [f"--until={until}"]
    if query:
        args += [f"--grep={query}", "-i"]

    out = _run(repo_path, *args)
    commits = []
    for line in out.splitlines():
        parts = line.split("|", 6)
        if len(parts) >= 6:
            commits.append({
                "hash":         parts[0],
                "short_hash":   parts[1],
                "author_name":  parts[2],
                "author_email": parts[3],
                "message":      parts[4],
                "date":         parts[5],
                "parent_hash":  parts[6] if len(parts) > 6 else None,
            })
    return commits


def git_log_count(repo_path: str, branch: str, query: Optional[str] = None) -> int:
    """Return total commit count on a branch."""
    args = ["rev-list", "--count", _safe_ref(branch)]
    if query:
        args += [f"--grep={query}", "-i"]
    try:
        out = _run(repo_path, *args)
        return int(out.strip())
    except (RuntimeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Commit detail and diff
# ---------------------------------------------------------------------------

def git_show_stat(repo_path: str, commit_hash: str) -> dict:
    """Return commit metadata + changed files summary."""
    h = _safe_hash(commit_hash)
    # Metadata line
    meta_out = _run(repo_path, "show", "--no-patch", f"--format={LOG_FORMAT}", h)
    meta_line = meta_out.splitlines()[0] if meta_out.strip() else ""
    parts = meta_line.split("|", 6)

    # Stat
    try:
        parent_out = _run(repo_path, "log", "-1", "--format=%P", h).strip()
        parents = parent_out.split()
        if not parents:
            # Initial commit: diff against empty tree hash
            stat_out = _run(repo_path, "diff", "--numstat", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", h)
        else:
            # Diff against first parent (handles normal and merge commits predictably)
            stat_out = _run(repo_path, "diff", "--numstat", parents[0], h)
    except RuntimeError:
        stat_out = ""

    files_changed = []
    total_add = 0
    total_del = 0
    for line in stat_out.splitlines():
        line = line.strip()
        if not line: continue
        parts_stat = line.split("\t")
        if len(parts_stat) == 3:
            add_str, del_str, fname = parts_stat
            add = int(add_str) if add_str != "-" else 0
            delete = int(del_str) if del_str != "-" else 0
            files_changed.append({"file": fname, "added": add, "deleted": delete})
            total_add += add
            total_del += delete

    return {
        "hash":         parts[0] if parts else h,
        "short_hash":   parts[1] if len(parts) > 1 else h[:7],
        "author_name":  parts[2] if len(parts) > 2 else "",
        "author_email": parts[3] if len(parts) > 3 else "",
        "message":      parts[4] if len(parts) > 4 else "",
        "date":         parts[5] if len(parts) > 5 else "",
        "parent_hash":  parts[6] if len(parts) > 6 else None,
        "files_changed":files_changed,
        "total_added":  total_add,
        "total_deleted":total_del,
    }


def git_diff(repo_path: str, commit_hash: str) -> list[dict]:
    """Parse unified diff for a commit into structured JSON."""
    h = _safe_hash(commit_hash)
    try:
        raw = _run(repo_path, "show", h, "--no-color", "--unified=3", "--format=")
    except RuntimeError:
        # Initial commit: diff against empty tree
        raw = _run(repo_path, "diff-tree", "--no-color", "--no-commit-id", "-r", "--unified=3", "--format=", h)

    return _parse_unified_diff(raw)


def git_diff_branches(repo_path: str, base: str, head: str) -> list[dict]:
    """Parse unified diff between two branches."""
    raw = _run(
        repo_path, "diff", "--no-color",
        _safe_ref(base), _safe_ref(head),
        "--unified=3",
    )
    return _parse_unified_diff(raw)


def _parse_unified_diff(raw: str) -> list[dict]:
    """Parse a unified diff string into structured file diffs."""
    files = []
    current_file: Optional[dict] = None
    current_hunk: Optional[dict] = None

    for line in raw.splitlines():
        if line.startswith("diff --git "):
            if current_file:
                if current_hunk:
                    current_file["hunks"].append(current_hunk)
                files.append(current_file)
            current_file = {
                "filename":      "",
                "change_type":   "modified",
                "lines_added":   0,
                "lines_deleted": 0,
                "hunks":         [],
            }
            current_hunk = None
        elif line.startswith("Binary files") and current_file:
            current_file["change_type"] = "binary"
        elif line.startswith("--- "):
            pass  # handled by +++ line
        elif line.startswith("+++ ") and current_file:
            fname = line[4:].lstrip("b/")
            if fname == "/dev/null":
                current_file["change_type"] = "deleted"
            else:
                current_file["filename"] = fname
        elif line.startswith("new file") and current_file:
            current_file["change_type"] = "added"
        elif line.startswith("deleted file") and current_file:
            current_file["change_type"] = "deleted"
        elif line.startswith("rename") and current_file:
            current_file["change_type"] = "renamed"
        elif line.startswith("\\ No newline"):
            continue
        elif line.startswith("@@") and current_file:
            if current_hunk:
                current_file["hunks"].append(current_hunk)
            current_hunk = {"header": line, "lines": []}
        elif current_hunk is not None:
            if line.startswith("+"):
                current_hunk["lines"].append({"type": "add", "content": line[1:]})
                if current_file is not None:
                    current_file["lines_added"] += 1
            elif line.startswith("-"):
                current_hunk["lines"].append({"type": "del", "content": line[1:]})
                if current_file is not None:
                    current_file["lines_deleted"] += 1
            else:
                current_hunk["lines"].append({"type": "ctx", "content": line[1:] if line.startswith(" ") else line})

    if current_file:
        if current_hunk:
            current_file["hunks"].append(current_hunk)
        files.append(current_file)

    return files


# ---------------------------------------------------------------------------
# File tree and blob
# ---------------------------------------------------------------------------

def git_ls_tree(repo_path: str, ref: str, path: str = "") -> list[dict]:
    """List directory contents at a ref/path."""
    args = ["ls-tree", "--long"]
    if path:
        args.append(f"{_safe_ref(ref)}:{_safe_path(path)}")
    else:
        args.append(_safe_ref(ref))

    try:
        out = _run(repo_path, *args)
    except RuntimeError:
        return []

    entries = []
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4:
            mode, obj_type, obj_hash, size_or_dash, *name_parts = parts
            name = name_parts[0] if name_parts else size_or_dash
            entries.append({
                "mode":  mode,
                "type":  "tree" if obj_type == "tree" else "blob",
                "hash":  obj_hash,
                "size":  None if size_or_dash == "-" else int(size_or_dash),
                "name":  name,
            })
    # Folders before files
    entries.sort(key=lambda e: (0 if e["type"] == "tree" else 1, e["name"]))
    return entries


def git_show_file(repo_path: str, ref: str, filepath: str) -> bytes:
    """Retrieve raw file content at a ref."""
    spec = f"{_safe_ref(ref)}:{_safe_path(filepath)}"
    result = subprocess.run(
        ["git", "show", spec],
        cwd=repo_path,
        capture_output=True,
        timeout=30,
        shell=False,
        user="git",
        group="git",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode().strip())
    return result.stdout


def decode_file_content(raw: bytes) -> tuple[Optional[str], bool]:
    """Decodes raw bytes into a string, returning (text, is_binary)."""
    if not raw:
        return "", False

    if raw.startswith(b'\xff\xfe'):
        try:
            return raw[2:].decode('utf-16le'), False
        except UnicodeDecodeError:
            pass
    elif raw.startswith(b'\xfe\xff'):
        try:
            return raw[2:].decode('utf-16be'), False
        except UnicodeDecodeError:
            pass
    elif raw.startswith(b'\xef\xbb\xbf'):
        try:
            return raw[3:].decode('utf-8'), False
        except UnicodeDecodeError:
            pass

    try:
        text = raw.decode('utf-8')
        if '\x00' in text:
            return None, True
        return text, False
    except UnicodeDecodeError:
        pass

    import charset_normalizer
    match = charset_normalizer.from_bytes(raw).best()
    if match and match.encoding:
        try:
            text = str(match)
            if '\x00' in text:
                return None, True
            return text, False
        except Exception:
            pass

    return None, True


def git_readme(repo_path: str, ref: str) -> Optional[str]:
    """Try to find and return README content."""
    for name in ("README.md", "README.txt", "README.rst", "README"):
        try:
            raw = git_show_file(repo_path, ref, name)
            text, is_binary = decode_file_content(raw)
            if not is_binary and text is not None:
                return text
        except RuntimeError:
            continue
    return None


# ---------------------------------------------------------------------------
# Divergence / merge-base
# ---------------------------------------------------------------------------

def git_merge_base(repo_path: str, base: str, head: str) -> str:
    """Return the common ancestor commit hash of two branches."""
    out = _run(repo_path, "merge-base", _safe_ref(base), _safe_ref(head))
    return out.strip()


def git_rev_list_count(repo_path: str, ref_a: str, ref_b: str) -> tuple[int, int]:
    """Return (ahead, behind) counts of ref_a relative to ref_b."""
    try:
        out = _run(
            repo_path, "rev-list", "--left-right", "--count",
            f"{_safe_ref(ref_a)}...{_safe_ref(ref_b)}"
        )
        a, b = out.strip().split()
        return int(a), int(b)
    except (RuntimeError, ValueError):
        return 0, 0


def git_is_ancestor(repo_path: str, ancestor: str, descendant: str) -> bool:
    """Return True if ancestor is a strict ancestor of descendant."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", _safe_ref(ancestor), _safe_ref(descendant)],
        cwd=repo_path,
        capture_output=True,
        shell=False,
        user="git",
        group="git",
    )
    return result.returncode == 0
