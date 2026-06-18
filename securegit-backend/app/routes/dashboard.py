"""Dashboard routes — /api/dashboard/*"""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models.user import User
from ..models.project import Project
from ..models.repository import Repository
from ..models.branch import Branch
from ..models.commit import Commit
from ..models.ssh_key import SSHKey
from ..models.audit_log import AuditLog

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/stats")
@jwt_required()
def stats():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    total_projects = Project.query.filter_by(owner_user_id=user_id).count()
    
    commits_today = db.session.query(Commit).join(Commit.branch).join(Branch.repository).join(Repository.project).filter(
        Project.owner_user_id == user_id,
        Commit.committed_at >= today_start
    ).count()

    active_users = 0
    if user and user.role == 'admin':
        active_users = db.session.query(db.func.count(db.distinct(AuditLog.actor_id))).filter(
            AuditLog.occurred_at >= week_ago
        ).scalar() or 0

    ssh_keys_count = SSHKey.query.filter_by(user_id=user_id).count()

    return jsonify({
        "total_projects": total_projects,
        "commits_today":  commits_today,
        "active_users":   active_users,
        "ssh_keys_count": ssh_keys_count,
    }), 200


@dashboard_bp.get("/activity")
@jwt_required()
def activity():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    limit = min(int(request.args.get("limit", 20)), 100)
    
    query = AuditLog.query
    if not user or user.role != 'admin':
        query = query.filter_by(actor_id=user_id)
        
    entries = (
        query
        .order_by(AuditLog.occurred_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([e.to_dict() for e in entries]), 200
