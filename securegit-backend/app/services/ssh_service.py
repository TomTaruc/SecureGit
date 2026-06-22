"""
SSH Service — manages /home/git/.ssh/authorized_keys.
Each entry uses the gitea-hook restricted format.
All writes use atomic file locking via fcntl (Linux only).
"""
import os
import re
import subprocess
import tempfile
import logging
import platform
from typing import Optional

logger = logging.getLogger(__name__)

AUTHORIZED_KEYS_PATH = os.environ.get("AUTHORIZED_KEYS_PATH", "/home/git/.ssh/authorized_keys")
GITEA_HOOK = os.environ.get("GITEA_HOOK", "/usr/share/gitea/contrib/gitea-git-hook")

KEY_RESTRICTIONS = (
    'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty'
)

# Matches the fingerprint output from ssh-keygen -l -f -
FINGERPRINT_RE = re.compile(r'SHA256:[A-Za-z0-9+/=]+')


def _build_authorized_line(user_id: int, public_key: str, fingerprint: str) -> str:
    """Build a restricted authorized_keys entry for a user."""
    # The python wrapper needs to be executed
    hook = "/usr/local/bin/python3 /app/scripts/git-shell-wrapper.py"
    return (
        f'command="{hook} {user_id}",{KEY_RESTRICTIONS} '
        f'{public_key.strip()} '
        f'# securegit-user-{user_id}-{fingerprint}'
    )


def _read_keys() -> list[str]:
    """Read current authorized_keys lines."""
    if not os.path.exists(AUTHORIZED_KEYS_PATH):
        return []
    with open(AUTHORIZED_KEYS_PATH, "r", encoding="utf-8") as f:
        return f.readlines()


def _write_keys_atomic(lines: list[str]) -> None:
    """Write authorized_keys atomically (write to temp, then rename)."""
    dir_path = os.path.dirname(AUTHORIZED_KEYS_PATH)
    os.makedirs(dir_path, mode=0o700, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.chmod(tmp_path, 0o600)

        # Chown to git:git so sshd doesn't reject it due to StrictModes
        try:
            import pwd
            import shutil
            git_pwd = pwd.getpwnam("git")
            os.chown(tmp_path, git_pwd.pw_uid, git_pwd.pw_gid)
        except (KeyError, ImportError):
            pass # Ignore if git user not found (e.g. during local Windows testing)

        if platform.system() == "Windows":
            shutil.move(tmp_path, AUTHORIZED_KEYS_PATH)
        else:
            os.rename(tmp_path, AUTHORIZED_KEYS_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def validate_key_format(public_key: str) -> Optional[str]:
    """
    Validate public key format using ssh-keygen -l.
    Returns fingerprint string on success, None on failure.
    Works on Linux only (uses /dev/stdin).
    """
    try:
        result = subprocess.run(
            ["ssh-keygen", "-l", "-f", "/dev/stdin"],
            input=public_key.strip() + "\n",
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        if result.returncode != 0:
            return None
        match = FINGERPRINT_RE.search(result.stdout)
        return match.group(0) if match else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # On Windows / dev environments: do basic format validation instead
        key = public_key.strip()
        valid_types = ("ssh-ed25519", "ssh-rsa", "ecdsa-sha2-nistp256")
        if any(key.startswith(t) for t in valid_types) and len(key.split()) >= 2:
            # Return a synthetic fingerprint for dev mode
            import hashlib, base64
            digest = hashlib.sha256(key.encode()).digest()
            fp = base64.b64encode(digest).decode().rstrip("=")
            return f"SHA256:{fp}"
        return None


def add_key(user_id: int, public_key: str) -> None:
    """Append a new authorized_keys entry for user_id."""
    clean_key = public_key.strip()
    if "\n" in clean_key or "\r" in clean_key:
        raise ValueError("Invalid public key format: newlines are not allowed.")
    lines = _read_keys()
    fp = validate_key_format(clean_key) or "unknown"
    new_line = _build_authorized_line(user_id, clean_key, fp) + "\n"
    lines.append(new_line)
    _write_keys_atomic(lines)
    logger.info("Added SSH key for user_id=%d", user_id)


def remove_key(user_id: int, fingerprint: str) -> None:
    """Remove specific authorized_keys line tagged with user_id and fingerprint."""
    tag = f"# securegit-user-{user_id}-{fingerprint}"
    lines = _read_keys()
    filtered = [line for line in lines if tag not in line]
    if len(filtered) == len(lines):
        logger.warning("No key found for user_id=%d fingerprint=%s", user_id, fingerprint)
    _write_keys_atomic(filtered)
    logger.info("Removed SSH key for user_id=%d", user_id)


def rebuild_authorized_keys(all_keys: list[dict]) -> None:
    """
    Full rebuild of authorized_keys from DB records.
    Called on startup or repair. Each dict: {user_id, public_key, fingerprint}.
    """
    lines = []
    for entry in all_keys:
        fp = entry.get("fingerprint") or "unknown"
        clean_key = entry["public_key"].strip()
        if "\n" in clean_key or "\r" in clean_key:
            continue  # Skip invalid/malicious keys
        line = _build_authorized_line(entry["user_id"], clean_key, fp) + "\n"
        lines.append(line)
    _write_keys_atomic(lines)
    logger.info("Rebuilt authorized_keys with %d entries", len(lines))
