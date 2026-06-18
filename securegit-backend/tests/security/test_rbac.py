import pytest
from flask import json
from app.models.collaborator import Collaborator
from app.routes.projects import _get_role_weight

def test_role_weights():
    assert _get_role_weight("owner") == 100
    assert _get_role_weight("admin") == 50
    assert _get_role_weight("write") == 20
    assert _get_role_weight("read") == 10
    assert _get_role_weight("invalid") == 0

def test_escalation_prevent_add_owner(client, auth_headers, project, another_user):
    # Try to add owner as a collaborator
    resp = client.post(
        f"/api/projects/{project.owner.username}/{project.project_name}/collaborators",
        headers=auth_headers,
        json={"user_id": project.owner_user_id, "permission": "read"}
    )
    # The normal_user owns the project, so auth_headers corresponds to the owner!
    assert resp.status_code == 409
    assert b"Cannot add project owner" in resp.data

def test_escalation_prevent_elevate_self(client, db_session, app, project, another_user):
    # another_user has manage_collaborators
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(another_user.user_id))
    headers = {"Authorization": f"Bearer {token}"}

    collab = Collaborator(
        project_id=project.project_id,
        user_id=another_user.user_id,
        permission="read",
        permissions={"manage_collaborators": True, "read": True}
    )
    db_session.add(collab)
    db_session.commit()

    # Try to elevate self to admin
    resp = client.patch(
        f"/api/projects/{project.owner.username}/{project.project_name}/collaborators/{another_user.user_id}",
        headers=headers,
        json={"permission": "admin"}
    )
    assert resp.status_code == 403
    assert b"Cannot modify your own permissions" in resp.data

def test_escalation_prevent_grant_higher_role(client, db_session, app, project, another_user):
    # another_user has manage_collaborators and is "write"
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(another_user.user_id))
    headers = {"Authorization": f"Bearer {token}"}

    collab = Collaborator(
        project_id=project.project_id,
        user_id=another_user.user_id,
        permission="write",
        permissions={"manage_collaborators": True, "read": True}
    )
    db_session.add(collab)
    
    # Third user to modify
    from app.models.user import User
    from app.extensions import bcrypt
    pw_hash = bcrypt.generate_password_hash("password").decode("utf-8")
    third = User(username="third", email="third@example.com", password_hash=pw_hash)
    db_session.add(third)
    db_session.commit()

    # Try to add third user as admin
    resp = client.post(
        f"/api/projects/{project.owner.username}/{project.project_name}/collaborators",
        headers=headers,
        json={"user_id": third.user_id, "permission": "admin"}
    )
    assert resp.status_code == 403
    assert b"Cannot grant a role equal to or higher than your own" in resp.data

def test_escalation_prevent_modify_owner(client, db_session, app, project, another_user):
    # another_user has manage_collaborators and is "admin"
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(another_user.user_id))
    headers = {"Authorization": f"Bearer {token}"}

    collab = Collaborator(
        project_id=project.project_id,
        user_id=another_user.user_id,
        permission="admin",
        permissions={"manage_collaborators": True, "read": True}
    )
    db_session.add(collab)
    db_session.commit()

    resp = client.patch(
        f"/api/projects/{project.owner.username}/{project.project_name}/collaborators/{project.owner_user_id}",
        headers=headers,
        json={"permission": "read"}
    )
    assert resp.status_code == 403
    assert b"Cannot modify project owner" in resp.data

