"""Authentication routes — /api/auth/*"""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    get_jwt_identity, jwt_required,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies,
)
from ..extensions import db, bcrypt, limiter
from ..models.user import User
from ..services import audit_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
@limiter.limit("5 per minute")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "missing_credentials", "message": "Username and password are required.", "status": 400}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid_credentials", "message": "Invalid username or password.", "status": 401}), 401

    if user.is_suspended:
        return jsonify({"error": "account_suspended", "message": "Your account has been suspended.", "status": 403}), 403

    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    access_token  = create_access_token(identity=user.user_id)
    refresh_token = create_refresh_token(identity=user.user_id)

    audit_service.log(actor_id=user.user_id, action="auth.login", target_type="user", target_id=user.user_id)

    response = jsonify({"user": user.to_dict(), "message": "Login successful."})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 200


@auth_bp.post("/logout")
@jwt_required()
def logout():
    user_id = get_jwt_identity()
    from flask_jwt_extended import get_jwt
    from datetime import datetime, timezone
    
    # Revoke access token
    jti = get_jwt()["jti"]
    exp = get_jwt()["exp"]
    now = datetime.now(timezone.utc).timestamp()
    ttl = max(int(exp - now), 10)
    
    from ..extensions import redis_client
    redis_client.setex(jti, ttl, "true")

    audit_service.log(actor_id=user_id, action="auth.logout", target_type="user", target_id=user_id)
    response = jsonify({"message": "Logged out."})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    response = jsonify({"message": "Token refreshed."})
    set_access_cookies(response, access_token)
    return response, 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict(include_sensitive=True)), 200
