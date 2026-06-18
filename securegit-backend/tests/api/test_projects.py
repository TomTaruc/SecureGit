import pytest

def test_list_projects(client, auth_headers, project):
    resp = client.get("/api/projects", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json
    assert len(data) >= 1
    assert data[0]["project_name"] == "test-repo"

def test_get_project_cache(client, auth_headers, project):
    # First request
    resp1 = client.get(f"/api/projects/{project.owner.username}/{project.project_name}", headers=auth_headers)
    assert resp1.status_code == 200
    
    # Second request should hit cache
    resp2 = client.get(f"/api/projects/{project.owner.username}/{project.project_name}", headers=auth_headers)
    assert resp2.status_code == 200
    assert resp1.json["project_id"] == resp2.json["project_id"]

def test_soft_delete_project(client, auth_headers, project):
    resp = client.delete(f"/api/projects/{project.owner.username}/{project.project_name}", headers=auth_headers)
    assert resp.status_code == 200

    # Project should not be returned in listing
    resp_list = client.get("/api/projects", headers=auth_headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json) == 0

    # GET project should return 404 since it's deleted
    resp_get = client.get(f"/api/projects/{project.owner.username}/{project.project_name}", headers=auth_headers)
    assert resp_get.status_code == 404
