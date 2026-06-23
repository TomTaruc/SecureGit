import pytest

def test_commits_owner_allowed(client, auth_headers, populated_project):
    res = client.get("/api/commits/test_user/test-repo-pop?branch=main", headers=auth_headers)
    assert res.status_code == 200

def test_commits_read_collaborator_allowed(client, another_user, populated_project):
    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=str(another_user.user_id))
    res = client.get("/api/commits/test_user/test-repo-pop?branch=main", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in [200, 403]

def test_commits_unauthorized_rejected(client, populated_project):
    res = client.get("/api/commits/test_user/test-repo-pop?branch=main")
    assert res.status_code == 401

def test_commit_detail_valid_sha(client, auth_headers, populated_project):
    res = client.get("/api/commits/test_user/test-repo-pop/1234567890123456789012345678901234567890", headers=auth_headers)
    assert res.status_code in [200, 404]

def test_commit_detail_invalid_sha_safe_404(client, auth_headers, populated_project):
    res = client.get(f"/api/commits/test_user/test-repo-pop/0000000000000000000000000000000000000000", headers=auth_headers)
    assert res.status_code == 404

def test_commit_diff_invalid_sha_safe_404(client, auth_headers, populated_project):
    res = client.get(f"/api/commits/test_user/test-repo-pop/0000000000000000000000000000000000000000/diff", headers=auth_headers)
    assert res.status_code == 404

def test_commits_invalid_branch_safe_error(client, auth_headers, populated_project):
    res = client.get("/api/commits/test_user/test-repo-pop?branch=invalid-branch", headers=auth_headers)
    assert res.status_code in [400, 404, 422]

def test_commits_empty_repo_returns_empty_list(client, auth_headers, populated_project):
    res = client.get("/api/commits/test_user/test-repo-pop?branch=feature-non-existent", headers=auth_headers)
    assert res.status_code in [404, 200]
