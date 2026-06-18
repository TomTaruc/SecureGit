"""Backup routes — /api/backups/*"""
import threading
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models.enhancement_models import BackupJob
from ..services import backup_service
from ..utils.decorators import require_admin

backups_bp = Blueprint("backups", __name__)


@backups_bp.get("")
@require_admin
def list_jobs():
    jobs = BackupJob.query.order_by(BackupJob.created_at.desc()).limit(50).all()
    return jsonify([j.to_dict() for j in jobs]), 200


import os

@backups_bp.post("")
@require_admin
def trigger_backup():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    backup_type = data.get("backup_type", "full")
    destination = data.get("destination", os.environ.get("BACKUP_DEST_PATH", "/mnt/backup"))

    # Run backup in background thread so endpoint returns immediately
    def _run():
        backup_service.run_full_backup(destination, triggered_by=user_id)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return jsonify({"message": "Backup started.", "destination": destination}), 202


@backups_bp.get("/files")
@require_admin
def list_files():
    dest = request.args.get("dest", os.environ.get("BACKUP_DEST_PATH", "/mnt/backup"))
    files = backup_service.list_backups(dest)
    return jsonify(files), 200
