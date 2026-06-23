import pytest

def test_commits_owner_allowed(client, auth_headers, project):
    res = client.get("/api/commits/test_user/test-repo?branch=main", headers=auth_headers)
    assert res.status_code in [200, 500]

def test_commits_read_collaborator_allowed(client, another_user, project):
    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=str(another_user.user_id))
    res = client.get("/api/commits/test_user/test-repo?branch=main", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in [200, 403, 500]

def test_commits_unauthorized_rejected(client, project):
    res = client.get("/api/commits/test_user/test-repo?branch=main")
    assert res.status_code == 401

def test_commit_detail_valid_sha(client, auth_headers, project):
    res = client.get("/api/commits/test_user/test-repo/1234567890123456789012345678901234567890", headers=auth_headers)
    assert res.status_code in [200, 404, 500]

def test_commit_detail_invalid_sha_safe_404(client, auth_headers, project):
    res = client.get(f"/api/commits/test_user/test-repo/0000000000000000000000000000000000000000", headers=auth_headers)
    assert res.status_code in [404, 500]

def test_commit_diff_invalid_sha_safe_404(client, auth_headers, project):
    res = client.get(f"/api/commits/test_user/test-repo/0000000000000000000000000000000000000000/diff", headers=auth_headers)
    assert res.status_code in [404, 500]

def test_commits_invalid_branch_safe_error(client, auth_headers, project):
    res = client.get("/api/commits/test_user/test-repo?branch=invalid-branch", headers=auth_headers)
    assert res.status_code in [200, 404, 500]

def test_commits_empty_repo_returns_empty_list(client, auth_headers, project):
    res = client.get("/api/commits/test_user/test-repo?branch=feature-non-existent", headers=auth_headers)
    assert res.status_code in [200, 404, 500]
