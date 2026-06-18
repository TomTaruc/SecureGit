"""User profile routes — /api/users/*"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db, bcrypt
from ..models.user import User
from ..utils.validators import validate_email, validate_password

users_bp = Blueprint("users", __name__)


@users_bp.get("/profile")
@jwt_required()
def get_profile():
    user = User.query.get_or_404(get_jwt_identity())
    return jsonify(user.to_dict(include_sensitive=True)), 200


@users_bp.patch("/profile")
@jwt_required()
def update_profile():
    user = User.query.get_or_404(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    if "email" in data:
        err = validate_email(data["email"])
        if err:
            return jsonify({"error": "validation_error", "message": err, "status": 422}), 422
        # Check uniqueness
        existing = User.query.filter_by(email=data["email"]).first()
        if existing and existing.user_id != user.user_id:
            return jsonify({"error": "conflict", "message": "Email already in use.", "status": 409}), 409
        user.email = data["email"]

    db.session.commit()
    return jsonify(user.to_dict()), 200


@users_bp.patch("/profile/password")
@jwt_required()
def change_password():
    user = User.query.get_or_404(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    current_password = data.get("current_password", "")
    new_password     = data.get("new_password", "")

    if not bcrypt.check_password_hash(user.password_hash, current_password):
        return jsonify({"error": "invalid_credentials", "message": "Current password is incorrect.", "status": 401}), 401

    err = validate_password(new_password)
    if err:
        return jsonify({"error": "validation_error", "message": err, "status": 422}), 422

    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    return jsonify({"message": "Password changed successfully."}), 200


@users_bp.get("/search")
@jwt_required()
def search_users():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([]), 200
    users = User.query.filter(
        User.username.ilike(f"%{q}%"),
        User.is_suspended == False,
    ).limit(20).all()
    return jsonify([u.to_dict() for u in users]), 200
