"""Authentication routes — /api/auth/*"""
import logging
import re
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    get_jwt_identity, jwt_required,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies,
)
from sqlalchemy import or_
from ..extensions import db, bcrypt, limiter
from ..models.user import User
from ..services import audit_service

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.post("/login")
@limiter.limit("20 per minute")
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "missing_credentials", "message": "Username/email and password are required.", "status": 400}), 400

    try:
        user = User.query.filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()
    except Exception:
        logger.exception("Database error during login lookup")
        return jsonify({"error": "internal_error", "message": "An unexpected error occurred. Please try again.", "status": 500}), 500

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid_credentials", "message": "Invalid username or password.", "status": 401}), 401

    if user.is_suspended:
        return jsonify({"error": "account_suspended", "message": "Your account has been suspended.", "status": 403}), 403

    try:
        user.last_login = datetime.now(timezone.utc)
        audit_service.log(actor_id=user.user_id, action="auth.login", target_type="user", target_id=user.user_id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Database error during login commit")

    access_token  = create_access_token(identity=str(user.user_id))
    refresh_token = create_refresh_token(identity=str(user.user_id))

    response = jsonify({"user": user.to_dict(), "message": "Login successful."})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 200


@auth_bp.post("/register")
@limiter.limit("10 per minute")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # --- Validation ---
    errors = []
    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif len(username) > 50:
        errors.append("Username must be 50 characters or fewer.")
    elif not re.match(r"^[a-zA-Z0-9_-]+$", username):
        errors.append("Username may only contain letters, numbers, hyphens, and underscores.")

    if not email:
        errors.append("Email is required.")
    elif not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")

    if errors:
        return jsonify({"error": "validation_error", "message": errors[0], "errors": errors, "status": 400}), 400

    # --- Duplicate checks ---
    try:
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "duplicate_username", "message": "Username is already taken.", "status": 409}), 409

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "duplicate_email", "message": "Email is already registered.", "status": 409}), 409
    except Exception:
        logger.exception("Database error during duplicate check")
        return jsonify({"error": "internal_error", "message": "An unexpected error occurred. Please try again.", "status": 500}), 500

    # --- Create user ---
    try:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role="dev",
            last_login=datetime.now(timezone.utc)
        )
        db.session.add(new_user)
        db.session.flush()  # Assign user_id for audit log

        audit_service.log(actor_id=new_user.user_id, action="auth.register", target_type="user", target_id=new_user.user_id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Database error during registration")
        return jsonify({"error": "internal_error", "message": "An unexpected error occurred. Please try again.", "status": 500}), 500

    access_token  = create_access_token(identity=str(new_user.user_id))
    refresh_token = create_refresh_token(identity=str(new_user.user_id))

    response = jsonify({"user": new_user.to_dict(), "message": "Registration successful."})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 201


@auth_bp.post("/logout")
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())
    from flask_jwt_extended import get_jwt, decode_token
    from datetime import datetime, timezone
    from flask import current_app
    from ..extensions import redis_client
    
    now = datetime.now(timezone.utc).timestamp()
    
    # Revoke access token
    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    exp = jwt_data.get("exp")
    ttl = max(int(exp - now), 10) if exp else 30 * 24 * 3600
    
    redis_client.setex(jti, ttl, "true")

    # Revoke refresh token
    refresh_cookie_name = current_app.config.get("JWT_REFRESH_COOKIE_NAME", "refresh_token_cookie")
    refresh_token = request.cookies.get(refresh_cookie_name)
    if refresh_token:
        try:
            refresh_data = decode_token(refresh_token)
            r_jti = refresh_data["jti"]
            r_exp = refresh_data.get("exp")
            r_ttl = max(int(r_exp - now), 10) if r_exp else 30 * 24 * 3600
            redis_client.setex(r_jti, r_ttl, "true")
        except Exception:
            pass

    audit_service.log(actor_id=user_id, action="auth.logout", target_type="user", target_id=user_id)
    response = jsonify({"message": "Logged out."})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = int(get_jwt_identity())
    access_token = create_access_token(identity=str(user_id))
    response = jsonify({"message": "Token refreshed."})
    set_access_cookies(response, access_token)
    return response, 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = db.get_or_404(User, user_id)
    return jsonify(user.to_dict(include_sensitive=True)), 200
