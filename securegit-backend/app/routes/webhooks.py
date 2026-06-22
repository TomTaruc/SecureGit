"""Webhook routes — /api/webhooks/*"""
import re
import hashlib
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..extensions import db, bcrypt
from ..models.enhancement_models import WebhookEndpoint
from ..services import webhook_service
from ..utils.decorators import require_project_access
from ..utils.rbac import check_manage_settings

webhooks_bp = Blueprint("webhooks", __name__)

VALID_EVENTS = {"push", "create_branch", "delete_branch", "collaborator_add"}


@webhooks_bp.get("/<username>/<project_name>")
@jwt_required()
@require_project_access("manage_settings")
def list_webhooks(username, project_name, project, current_user):
    hooks = WebhookEndpoint.query.filter_by(project_id=project.project_id).all()
    return jsonify([h.to_dict() for h in hooks]), 200


@webhooks_bp.post("/<username>/<project_name>")
@jwt_required()
@require_project_access("manage_settings")
def create_webhook(username, project_name, project, current_user):
    data = request.get_json(silent=True) or {}
    name       = (data.get("name") or "").strip()
    target_url = (data.get("target_url") or "").strip()
    events     = data.get("events", ["push"])
    secret     = data.get("secret")

    if not name:
        return jsonify({"error": "validation_error", "message": "Webhook name is required.", "status": 422}), 422
    if not target_url:
        return jsonify({"error": "validation_error", "message": "target_url is required.", "status": 422}), 422
    if not webhook_service._is_internal_url(target_url):
        return jsonify({"error": "validation_error", "message": "Only internal (LAN/localhost) URLs are allowed.", "status": 422}), 422

    invalid_events = set(events) - VALID_EVENTS
    if invalid_events:
        return jsonify({"error": "validation_error", "message": f"Invalid events: {invalid_events}. Valid: {VALID_EVENTS}", "status": 422}), 422

    secret_hash = secret if secret else None

    hook = WebhookEndpoint(
        project_id=project.project_id,
        name=name,
        target_url=target_url,
        events=events,
        secret_hash=secret_hash,
    )
    db.session.add(hook)
    db.session.commit()
    return jsonify(hook.to_dict()), 201


@webhooks_bp.patch("/<username>/<project_name>/<int:webhook_id>")
@jwt_required()
@require_project_access("manage_settings")
def update_webhook(username, project_name, webhook_id, project, current_user):
    hook = WebhookEndpoint.query.filter_by(webhook_id=webhook_id, project_id=project.project_id).first_or_404()
    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        hook.is_active = bool(data["is_active"])
    if "events" in data:
        hook.events = data["events"]
    if "name" in data:
        hook.name = data["name"]
    db.session.commit()
    return jsonify(hook.to_dict()), 200


@webhooks_bp.delete("/<username>/<project_name>/<int:webhook_id>")
@jwt_required()
@require_project_access("manage_settings")
def delete_webhook(username, project_name, webhook_id, project, current_user):
    hook = WebhookEndpoint.query.filter_by(webhook_id=webhook_id, project_id=project.project_id).first_or_404()
    db.session.delete(hook)
    db.session.commit()
    return jsonify({"message": "Webhook deleted."}), 200


@webhooks_bp.post("/<username>/<project_name>/<int:webhook_id>/test")
@jwt_required()
@require_project_access("manage_settings")
def test_webhook(username, project_name, webhook_id, project, current_user):
    hook = WebhookEndpoint.query.filter_by(webhook_id=webhook_id, project_id=project.project_id).first_or_404()
    status, error_code, error_msg = webhook_service.dispatch(hook, "push", {"test": True, "project": project.project_name}, return_error=True)
    if status != 0 and 200 <= status < 300:
        return jsonify({
            "ok": True,
            "message": "Webhook test successful.",
            "target_url": hook.target_url
        }), 200
    
    return jsonify({
        "ok": False,
        "code": error_code or "HTTP_ERROR",
        "message": error_msg or f"HTTP status {status}",
        "target_url": hook.target_url
    }), 400
