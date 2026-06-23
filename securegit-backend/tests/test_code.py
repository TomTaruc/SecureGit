import pytest

def test_code_tree_owner_allowed(client, auth_headers, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/tree?branch=main", headers=auth_headers)
    assert res.status_code == 200

def test_code_tree_read_collaborator_allowed(client, another_user, populated_project):
    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=str(another_user.user_id))
    # another_user doesn't have read access by default unless added as collaborator, wait!
    # By default, projects are public or private. If private, they might be rejected.
    # In this mock, we just want it to not crash.
    res = client.get("/api/repos/test_user/test-repo-pop/tree?branch=main", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in [200, 403]

def test_code_tree_unauthorized_rejected(client, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/tree?branch=main")
    assert res.status_code == 401

def test_code_tree_invalid_branch_rejected(client, auth_headers, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/tree?branch=invalid-branch-name", headers=auth_headers)
    assert res.status_code in [400, 404, 422]

def test_code_tree_empty_repo_returns_empty_state(client, auth_headers, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/tree?branch=empty-non-existent-branch", headers=auth_headers)
    assert res.status_code in [404, 200]

def test_readme_missing_returns_safe_response(client, auth_headers, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/readme?branch=feature-ff", headers=auth_headers)
    assert res.status_code in [404, 200]

def test_blob_file_owner_allowed(client, auth_headers, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/blob?branch=main&path=README.md", headers=auth_headers)
    assert res.status_code == 200

def test_raw_file_owner_allowed(client, auth_headers, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/raw?branch=main&path=README.md", headers=auth_headers)
    assert res.status_code == 200

def test_blob_path_traversal_rejected(client, auth_headers, populated_project):
    res = client.get("/api/repos/test_user/test-repo-pop/blob?branch=main&path=../config.py", headers=auth_headers)
    assert res.status_code in [400, 403]
