"""System metrics routes — /api/admin/metrics"""
import os
import shutil
from flask import Blueprint, jsonify
from ..extensions import db
from ..models.project import Project
from ..models.commit import Commit
from ..utils.decorators import require_admin

metrics_bp = Blueprint("metrics", __name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@metrics_bp.get("")
@require_admin
def system_metrics():
    data = {}
    if PSUTIL_AVAILABLE:
        data["cpu_percent"]  = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        data["memory"] = {
            "total_gb":    round(mem.total / 1e9, 2),
            "used_gb":     round(mem.used  / 1e9, 2),
            "percent":     mem.percent,
        }
        disk = shutil.disk_usage("/")
        data["disk"] = {
            "total_gb": round(disk.total / 1e9, 2),
            "used_gb":  round(disk.used  / 1e9, 2),
            "free_gb":  round(disk.free  / 1e9, 2),
            "percent":  round(disk.used / disk.total * 100, 1),
        }
        try:
            net = psutil.net_io_counters()
            data["network"] = {
                "bytes_sent_mb": round(net.bytes_sent / 1e6, 2),
                "bytes_recv_mb": round(net.bytes_recv / 1e6, 2),
            }
        except Exception:
            data["network"] = None
    else:
        data["note"] = "psutil not available; install it for system metrics."

    return jsonify(data), 200


@metrics_bp.get("/git")
@require_admin
def git_metrics():
    git_base = os.environ.get("GIT_REPOS_BASE", "/srv/git")
    total_repos   = Project.query.count()
    total_commits = Commit.query.count()

    # Disk usage for repos dir
    repo_size_gb = 0.0
    if os.path.exists(git_base):
        total = sum(
            os.path.getsize(os.path.join(dirpath, f))
            for dirpath, _, files in os.walk(git_base)
            for f in files
        )
        repo_size_gb = round(total / 1e9, 3)

    return jsonify({
        "total_repositories": total_repos,
        "total_commits":      total_commits,
        "repos_dir_size_gb":  repo_size_gb,
    }), 200
