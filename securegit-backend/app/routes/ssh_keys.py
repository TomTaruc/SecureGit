"""SSH key routes — /api/ssh-keys/*"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db, limiter
from ..models.user import User
from ..models.ssh_key import SSHKey
from ..services import ssh_service, audit_service

ssh_keys_bp = Blueprint("ssh_keys", __name__)


@ssh_keys_bp.get("")
@jwt_required()
def list_keys():
    user_id = get_jwt_identity()
    keys = SSHKey.query.filter_by(user_id=user_id).order_by(SSHKey.added_at.desc()).all()
    return jsonify([k.to_dict() for k in keys]), 200


@ssh_keys_bp.post("")
@jwt_required()
@limiter.limit("10 per hour", key_func=get_jwt_identity)
def add_key():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    title      = (data.get("title") or "").strip()
    public_key = (data.get("public_key") or "").strip()

    if not title:
        return jsonify({"error": "validation_error", "message": "Key title is required.", "status": 422}), 422
    if not public_key:
        return jsonify({"error": "validation_error", "message": "Public key is required.", "status": 422}), 422

    # Detect key type
    key_parts = public_key.split()
    if len(key_parts) < 2:
        return jsonify({"error": "validation_error", "message": "Invalid public key format.", "status": 422}), 422

    key_type = key_parts[0]
    valid_types = ("ssh-ed25519", "ssh-rsa", "ecdsa-sha2-nistp256")
    if key_type not in valid_types:
        return jsonify({"error": "validation_error", "message": f"Key type must be one of: {', '.join(valid_types)}.", "status": 422}), 422

    # Validate format and get fingerprint
    fingerprint = ssh_service.validate_key_format(public_key)
    if not fingerprint:
        return jsonify({"error": "validation_error", "message": "Invalid SSH public key format.", "status": 422}), 422

    # Check for duplicate
    if SSHKey.query.filter_by(fingerprint=fingerprint).first():
        return jsonify({"error": "conflict", "message": "This SSH key is already registered.", "status": 409}), 409

    key = SSHKey(
        user_id=user_id,
        title=title,
        key_type=key_type,
        public_key=public_key,
        fingerprint=fingerprint,
    )
    db.session.add(key)

    # Update authorized_keys
    try:
        ssh_service.add_key(user_id, public_key)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "ssh_error", "message": f"Failed to register SSH key: {e}", "status": 500}), 500

    db.session.commit()
    audit_service.log(actor_id=user_id, action="ssh_key.add", target_type="ssh_key", target_id=key.key_id)
    return jsonify(key.to_dict()), 201


@ssh_keys_bp.delete("/<int:key_id>")
@jwt_required()
def revoke_key(key_id: int):
    user_id = get_jwt_identity()
    key = SSHKey.query.filter_by(key_id=key_id, user_id=user_id).first_or_404()

    try:
        ssh_service.remove_key(user_id, key.fingerprint)
    except Exception as e:
        return jsonify({"error": "ssh_error", "message": str(e), "status": 500}), 500

    audit_service.log(actor_id=user_id, action="ssh_key.revoke", target_type="ssh_key", target_id=key_id)
    db.session.delete(key)
    db.session.commit()
    return jsonify({"message": "SSH key revoked."}), 200
