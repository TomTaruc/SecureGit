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

    # Run backup via Celery task
    from ..tasks import run_full_backup_task
    run_full_backup_task.delay(destination, user_id)

    return jsonify({"message": "Backup started.", "destination": destination}), 202


@backups_bp.get("/files")
@require_admin
def list_files():
    dest = request.args.get("dest", os.environ.get("BACKUP_DEST_PATH", "/mnt/backup"))
    files = backup_service.list_backups(dest)
    return jsonify(files), 200


@backups_bp.post("/restore")
@require_admin
def restore_backup():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    dest = data.get("destination", os.environ.get("BACKUP_DEST_PATH", "/mnt/backup"))
    
    if not filename:
        return jsonify({"error": "validation_error", "message": "filename is required.", "status": 422}), 422
    
    # Run restore via Celery task
    from ..tasks import restore_backup_task
    restore_backup_task.delay(filename, dest)

    return jsonify({"message": f"Restore started for {filename}."}), 202
