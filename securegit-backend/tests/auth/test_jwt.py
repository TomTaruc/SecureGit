import pytest
from flask import json
from flask_jwt_extended import create_access_token
from app.extensions import redis_client

def test_login(client, app, normal_user):
    resp = client.post("/api/auth/login", json={"username": "test_user", "password": "password"})
    assert resp.status_code == 200
    assert "access_token_cookie" in resp.headers.get("Set-Cookie", "")

def test_logout_revokes_token(client, app, auth_headers):
    # Access a protected route
    resp_protected = client.get("/api/auth/me", headers=auth_headers)
    if resp_protected.status_code != 200:
        print(resp_protected.data)
    assert resp_protected.status_code == 200

    # Logout
    resp_logout = client.post("/api/auth/logout", headers=auth_headers)
    assert resp_logout.status_code == 200

    # Access protected route again
    resp_protected_again = client.get("/api/auth/me", headers=auth_headers)
    assert resp_protected_again.status_code == 401
    assert b"revoked" in resp_protected_again.data or b"Token has been revoked" in resp_protected_again.data or resp_protected_again.status_code == 401

