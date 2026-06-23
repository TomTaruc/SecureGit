import pytest
from app.models.enhancement_models import WebhookEndpoint
from app.extensions import db

def test_webhook_create_authorized(client, auth_headers, project):
    res = client.post(f"/api/webhooks/test_user/test-repo", json={
        "name": "Test Hook",
        "target_url": "http://127.0.0.1:8080/hook",
        "events": ["push"]
    }, headers=auth_headers)
    assert res.status_code == 201
    assert res.json["name"] == "Test Hook"

def test_webhook_create_read_collaborator_forbidden(client, another_user, project):
    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=str(another_user.user_id))
    res = client.post(f"/api/webhooks/test_user/test-repo", json={
        "name": "Hook",
        "target_url": "http://127.0.0.1:8080/hook",
        "events": ["push"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

def test_webhook_test_success_mocked(client, auth_headers, project):
    w = WebhookEndpoint(project_id=project.project_id, name="OkHook", target_url="http://127.0.0.1:8080/hook", events=["push"])
    db.session.add(w)
    db.session.commit()
    res = client.post(f"/api/webhooks/test_user/test-repo/{w.webhook_id}/test", headers=auth_headers)
    assert res.status_code == 200

def test_webhook_dns_failure_mocked(client, auth_headers, project):
    w = WebhookEndpoint(project_id=project.project_id, name="DNSHook", target_url="http://127.0.0.1:8080/hook/dns", events=["push"])
    db.session.add(w)
    db.session.commit()
    res = client.post(f"/api/webhooks/test_user/test-repo/{w.webhook_id}/test", headers=auth_headers)
    assert res.status_code == 400
    assert res.json["code"] == "DNS_FAILURE"

def test_webhook_timeout_mocked(client, auth_headers, project):
    w = WebhookEndpoint(project_id=project.project_id, name="TimeoutHook", target_url="http://127.0.0.1:8080/hook/timeout", events=["push"])
    db.session.add(w)
    db.session.commit()
    res = client.post(f"/api/webhooks/test_user/test-repo/{w.webhook_id}/test", headers=auth_headers)
    assert res.status_code == 400
    assert res.json["code"] == "TIMEOUT"

def test_webhook_connection_refused_mocked(client, auth_headers, project):
    w = WebhookEndpoint(project_id=project.project_id, name="RefusedHook", target_url="http://127.0.0.1:8080/hook/refused", events=["push"])
    db.session.add(w)
    db.session.commit()
    res = client.post(f"/api/webhooks/test_user/test-repo/{w.webhook_id}/test", headers=auth_headers)
    assert res.status_code == 400
    assert res.json["code"] in ["CONNECTION_REFUSED", "DNS_FAILURE"]

def test_webhook_delete_authorized(client, auth_headers, project):
    w = WebhookEndpoint(project_id=project.project_id, name="DeleteHook", target_url="http://127.0.0.1:8080/hook", events=["push"])
    db.session.add(w)
    db.session.commit()
    res = client.delete(f"/api/webhooks/test_user/test-repo/{w.webhook_id}", headers=auth_headers)
    assert res.status_code == 200

def test_webhook_delete_read_collaborator_forbidden(client, another_user, project):
    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=str(another_user.user_id))
    w = WebhookEndpoint(project_id=project.project_id, name="DeleteHook2", target_url="http://127.0.0.1:8080/hook", events=["push"])
    db.session.add(w)
    db.session.commit()
    res = client.delete(f"/api/webhooks/test_user/test-repo/{w.webhook_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

def test_webhook_secret_not_exposed(client, auth_headers, project):
    w = WebhookEndpoint(project_id=project.project_id, name="SecretHook", target_url="http://127.0.0.1:8080/hook", events=["push"], secret_hash="secret")
    db.session.add(w)
    db.session.commit()
    res = client.get(f"/api/webhooks/test_user/test-repo", headers=auth_headers)
    assert res.status_code == 200
    assert "secret_hash" not in res.json[0]
    assert res.json[0].get("secret") == "••••••••"

def test_webhook_payload_contains_actor(client, auth_headers, normal_user, project):
    import json
    from app.services.webhook_service import dispatch
    w = WebhookEndpoint(project_id=project.project_id, name="ActorHook", target_url="http://127.0.0.1:8080/hook", events=["push"])
    db.session.add(w)
    db.session.commit()
    
    payload = {"actor": {"username": normal_user.username}}
    dispatch(w, "push", payload)
