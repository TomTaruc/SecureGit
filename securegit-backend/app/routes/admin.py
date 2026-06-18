"""Admin routes — /api/admin/* (requires role='admin')"""
import subprocess
from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db, bcrypt
from ..models.user import User
from ..models.project import Project
from ..models.ssh_key import SSHKey
from ..models.audit_log import AuditLog
from ..models.chroot_jail import ChrootJail
from ..models.enhancement_models import ServerConfig
from ..services import audit_service, chroot_service
from ..utils.decorators import require_admin
from ..utils.validators import validate_username, validate_email, validate_password
import json, time

admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@admin_bp.get("/users")
@require_admin
def list_users():
    from sqlalchemy import func
    users = User.query.order_by(User.created_at.desc()).all()
    
    project_counts = dict(
        db.session.query(Project.owner_user_id, func.count(Project.project_id))
        .group_by(Project.owner_user_id).all()
    )
    
    ssh_key_counts = dict(
        db.session.query(SSHKey.user_id, func.count(SSHKey.key_id))
        .group_by(SSHKey.user_id).all()
    )

    result = []
    for u in users:
        d = u.to_dict()
        d["project_count"]  = project_counts.get(u.user_id, 0)
        d["ssh_keys_count"] = ssh_key_counts.get(u.user_id, 0)
        result.append(d)
    return jsonify(result), 200


@admin_bp.post("/users")
@require_admin
def create_user():
    actor_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email    = (data.get("email") or "").strip()
    password = data.get("password", "")
    role     = data.get("role", "dev")

    for validator, value in [(validate_username, username), (validate_email, email), (validate_password, password)]:
        err = validator(value)
        if err:
            return jsonify({"error": "validation_error", "message": err, "status": 422}), 422

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "conflict", "message": "Username already taken.", "status": 409}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "conflict", "message": "Email already in use.", "status": 409}), 409

    user = User(
        username=username,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    audit_service.log(actor_id=actor_id, action="admin.user.create", target_type="user", target_id=user.user_id, detail=username)
    return jsonify(user.to_dict()), 201


@admin_bp.patch("/users/<int:user_id>")
@require_admin
def update_user(user_id: int):
    actor_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "role" in data and data["role"] in ("admin", "dev", "read"):
        user.role = data["role"]
    if "is_suspended" in data:
        user.is_suspended = bool(data["is_suspended"])
        # Sync chroot jail status
        action = "admin.user.suspend" if user.is_suspended else "admin.user.unsuspend"
        if user.is_suspended:
            chroot_service.suspend_jail(user.username)
        else:
            chroot_service.unsuspend_jail(user.username)
        audit_service.log(actor_id=actor_id, action=action, target_type="user", target_id=user_id)

    db.session.commit()
    return jsonify(user.to_dict()), 200


@admin_bp.delete("/users/<int:user_id>")
@require_admin
def delete_user(user_id: int):
    actor_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.user_id == actor_id:
        return jsonify({"error": "forbidden", "message": "Cannot delete your own account.", "status": 403}), 403
    audit_service.log(actor_id=actor_id, action="admin.user.delete", target_type="user", target_id=user_id, detail=user.username)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted."}), 200


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------

def _check_service(service_name: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True, text=True, timeout=5, shell=False,
        )
        return "running" if result.stdout.strip() == "active" else "stopped"
    except FileNotFoundError:
        return "unknown"  # Not on Linux


@admin_bp.get("/system/health")
@require_admin
def system_health():
    services = [
        {"name": "sshd",       "status": _check_service("sshd")},
        {"name": "postgresql", "status": _check_service("postgresql")},
        {"name": "nginx",      "status": _check_service("nginx")},
        {"name": "flask",      "status": "running"},  # If this runs, Flask is up
    ]
    # DB connection check
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"
    services.append({"name": "database", "status": db_status})
    return jsonify({"services": services}), 200


# ---------------------------------------------------------------------------
# Admin project and SSH key views
# ---------------------------------------------------------------------------

@admin_bp.get("/projects")
@require_admin
def admin_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return jsonify([p.to_dict() for p in projects]), 200


@admin_bp.get("/ssh-keys")
@require_admin
def admin_ssh_keys():
    keys = SSHKey.query.join(User).order_by(SSHKey.added_at.desc()).all()
    result = []
    for k in keys:
        d = k.to_dict()
        d["username"] = k.user.username
        result.append(d)
    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Audit log (paginated + SSE stream)
# ---------------------------------------------------------------------------

@admin_bp.get("/audit-log")
@require_admin
def audit_log():
    page     = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    entries  = AuditLog.query.order_by(AuditLog.occurred_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "entries":     [e.to_dict() for e in entries.items],
        "page":        page,
        "total":       entries.total,
        "total_pages": entries.pages,
    }), 200


@admin_bp.get("/audit-log/stream")
@require_admin
def audit_log_stream():
    """Server-Sent Events — poll for new audit entries every 5s."""
    last_id = request.args.get("last_id", 0, type=int)

    def generate():
        nonlocal last_id
        while True:
            new_entries = (
                AuditLog.query
                .filter(AuditLog.log_id > last_id)
                .order_by(AuditLog.log_id.asc())
                .limit(20)
                .all()
            )
            for entry in new_entries:
                last_id = entry.log_id
                data = json.dumps(entry.to_dict())
                yield f"id: {entry.log_id}\ndata: {data}\n\n"
            time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Chroot jails
# ---------------------------------------------------------------------------

@admin_bp.get("/chroot-jails")
@require_admin
def chroot_jails():
    jails = ChrootJail.query.all()
    return jsonify([j.to_dict() for j in jails]), 200


# ---------------------------------------------------------------------------
# Server config
# ---------------------------------------------------------------------------

@admin_bp.get("/config")
@require_admin
def get_config():
    configs = ServerConfig.query.order_by(ServerConfig.key).all()
    return jsonify([c.to_dict() for c in configs]), 200


@admin_bp.patch("/config")
@require_admin
def update_config():
    actor_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    updated = []
    for key, value in data.items():
        cfg = ServerConfig.query.filter_by(key=key).first()
        if cfg:
            cfg.value = str(value)
            cfg.updated_by = actor_id
            from datetime import datetime, timezone
            cfg.updated_at = datetime.now(timezone.utc)
            updated.append(cfg.to_dict())
    db.session.commit()
    audit_service.log(actor_id=actor_id, action="admin.config.update", detail=str(list(data.keys())))
    return jsonify(updated), 200
