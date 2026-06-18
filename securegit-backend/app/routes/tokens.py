"""Repository token routes — /api/tokens/*"""
import os
import secrets
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db, bcrypt
from ..models.enhancement_models import RepoToken
from ..utils.decorators import require_project_access
from ..utils.rbac import check_manage_settings

tokens_bp = Blueprint("tokens", __name__)

DEFAULT_TTL_DAYS = 90


@tokens_bp.get("/<username>/<project_name>")
@jwt_required()
@require_project_access("manage_settings")
def list_tokens(username, project_name, project, current_user):
    tokens = RepoToken.query.filter_by(repo_id=project.repository.repo_id).all()
    return jsonify([t.to_dict() for t in tokens]), 200


@tokens_bp.post("/<username>/<project_name>")
@jwt_required()
@require_project_access("manage_settings")
def create_token(username, project_name, project, current_user):
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    name   = (data.get("name") or "").strip()
    scopes = data.get("scopes", ["read"])
    ttl    = data.get("ttl_days", DEFAULT_TTL_DAYS)

    if not name:
        return jsonify({"error": "validation_error", "message": "Token name is required.", "status": 422}), 422

    valid_scopes = {"read", "push"}
    if not all(s in valid_scopes for s in scopes):
        return jsonify({"error": "validation_error", "message": f"Invalid scope. Valid: {valid_scopes}", "status": 422}), 422

    # Generate raw token (shown once)
    raw_token = secrets.token_urlsafe(48)
    token_hash = bcrypt.generate_password_hash(raw_token).decode("utf-8")

    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl) if ttl else None

    token = RepoToken(
        repo_id=project.repository.repo_id,
        user_id=user_id,
        name=name,
        token_hash=token_hash,
        scopes=scopes,
        expires_at=expires_at,
    )
    db.session.add(token)
    db.session.commit()

    d = token.to_dict()
    d["token"] = raw_token  # Only returned once
    return jsonify(d), 201


@tokens_bp.delete("/<username>/<project_name>/<int:token_id>")
@jwt_required()
@require_project_access("manage_settings")
def revoke_token(username, project_name, token_id, project, current_user):
    token = RepoToken.query.filter_by(
        token_id=token_id, repo_id=project.repository.repo_id
    ).first_or_404()
    db.session.delete(token)
    db.session.commit()
    return jsonify({"message": "Token revoked."}), 200
