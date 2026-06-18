"""
Chroot Service — provisions and manages per-user chroot jails.
Runs on Linux only; on other platforms, operations are no-ops with warnings.
"""
import os
import stat
import logging
import subprocess
import platform

logger = logging.getLogger(__name__)

GIT_REPOS_BASE = os.environ.get("GIT_REPOS_BASE", "/srv/git")
_IS_LINUX = platform.system() == "Linux"


def _warn_non_linux(op: str) -> None:
    if not _IS_LINUX:
        logger.warning("Chroot %s skipped — not running on Linux", op)


def jail_path_for(username: str) -> str:
    return os.path.join(GIT_REPOS_BASE, username)


def provision_jail(username: str) -> str:
    """
    Create the chroot jail directory structure for a user.
    Returns the jail path.
    """
    jail = jail_path_for(username)
    _warn_non_linux("provision")

    os.makedirs(jail, mode=0o755, exist_ok=True)
    for sub in ("repos",):
        os.makedirs(os.path.join(jail, sub), mode=0o755, exist_ok=True)

    if _IS_LINUX:
        _set_ownership(jail, "root", "root")
        repos_dir = os.path.join(jail, "repos")
        _set_ownership(repos_dir, username, username)

    logger.info("Provisioned chroot jail at %s", jail)
    return jail


def suspend_jail(username: str) -> None:
    """Remove execute permission on jail to block SSH access."""
    _warn_non_linux("suspend")
    if not _IS_LINUX:
        return
    jail = jail_path_for(username)
    if os.path.exists(jail):
        current = os.stat(jail).st_mode
        os.chmod(jail, current & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
        logger.info("Suspended jail for %s", username)


def unsuspend_jail(username: str) -> None:
    """Restore execute permission on jail."""
    _warn_non_linux("unsuspend")
    if not _IS_LINUX:
        return
    jail = jail_path_for(username)
    if os.path.exists(jail):
        current = os.stat(jail).st_mode
        os.chmod(jail, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        logger.info("Unsuspended jail for %s", username)


def repo_path_for(username: str, project_name: str) -> str:
    return os.path.join(GIT_REPOS_BASE, username, f"{project_name}.git")


def _set_ownership(path: str, user: str, group: str) -> None:
    try:
        subprocess.run(["chown", "-R", f"{user}:{group}", path], check=True, shell=False)
    except subprocess.CalledProcessError as e:
        logger.error("chown failed for %s: %s", path, e)
