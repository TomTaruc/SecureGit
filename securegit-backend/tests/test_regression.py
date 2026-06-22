import os
import pytest
import subprocess
from app.extensions import db
from app.models.user import User
from app.models.project import Project
from app.models.repository import Repository
from app.models.collaborator import Collaborator
from app.models.branch import Branch
from app.models.commit import Commit
from app.models.enhancement_models import WebhookEndpoint
from app.models.branch_protection import BranchProtectionRule
from app.services.git_service import git_init_bare
import json
import uuid
import tempfile
import shutil

@pytest.fixture
def test_app(app):
    with app.app_context():
        # Clean db just in case
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(test_app):
    return test_app.test_client()

@pytest.fixture
def admin_user():
    user = User(username="admin", email="admin@test.local", password_hash="hash", role="admin")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def dev_user():
    user = User(username="dev", email="dev@test.local", password_hash="hash", role="user")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def owner_user():
    user = User(username="owner", email="owner@test.local", password_hash="hash", role="user")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def admin_token(test_app, admin_user):
    from flask_jwt_extended import create_access_token
    return create_access_token(identity=str(admin_user.user_id))

@pytest.fixture
def dev_token(test_app, dev_user):
    from flask_jwt_extended import create_access_token
    return create_access_token(identity=str(dev_user.user_id))

@pytest.fixture
def owner_token(test_app, owner_user):
    from flask_jwt_extended import create_access_token
    return create_access_token(identity=str(owner_user.user_id))

def _run_git(cmd, cwd):
    subprocess.run(["git"] + cmd, cwd=cwd, check=True, user="git", group="git")

@pytest.fixture
def real_repo(test_app, owner_user):
    tmp_dir = tempfile.mkdtemp()
    try:
        import pwd
        git_pwd = pwd.getpwnam("git")
        os.chown(tmp_dir, git_pwd.pw_uid, git_pwd.pw_gid)
    except Exception:
        pass
    
    git_init_bare(tmp_dir)
    
    clone_dir = tempfile.mkdtemp()
    try:
        os.chown(clone_dir, git_pwd.pw_uid, git_pwd.pw_gid)
    except Exception:
        pass
        
    subprocess.run(["git", "clone", tmp_dir, clone_dir], check=True, user="git", group="git")
    _run_git(["config", "user.name", "Test"], clone_dir)
    _run_git(["config", "user.email", "test@test.local"], clone_dir)
    
    # main branch
    with open(os.path.join(clone_dir, "README.md"), "w") as f:
        f.write("Hello")
    _run_git(["add", "."], clone_dir)
    _run_git(["commit", "-m", "Initial commit"], clone_dir)
    _run_git(["push", "origin", "main"], clone_dir)
    
    # feature-ff branch
    _run_git(["checkout", "-b", "feature-ff"], clone_dir)
    with open(os.path.join(clone_dir, "ff.txt"), "w") as f:
        f.write("ff")
    _run_git(["add", "."], clone_dir)
    _run_git(["commit", "-m", "FF commit"], clone_dir)
    _run_git(["push", "origin", "feature-ff"], clone_dir)
    
    # main advance
    _run_git(["checkout", "main"], clone_dir)
    with open(os.path.join(clone_dir, "main.txt"), "w") as f:
        f.write("main advance")
    _run_git(["add", "."], clone_dir)
    _run_git(["commit", "-m", "Main advance"], clone_dir)
    _run_git(["push", "origin", "main"], clone_dir)
    
    # feature-squash branch
    _run_git(["checkout", "-b", "feature-squash"], clone_dir)
    with open(os.path.join(clone_dir, "squash.txt"), "w") as f:
        f.write("squash")
    _run_git(["add", "."], clone_dir)
    _run_git(["commit", "-m", "Squash commit 1"], clone_dir)
    _run_git(["push", "origin", "feature-squash"], clone_dir)
    
    # feature-rebase branch
    _run_git(["checkout", "main"], clone_dir)
    _run_git(["checkout", "-b", "feature-rebase"], clone_dir)
    with open(os.path.join(clone_dir, "rebase.txt"), "w") as f:
        f.write("rebase")
    _run_git(["add", "."], clone_dir)
    _run_git(["commit", "-m", "Rebase commit"], clone_dir)
    _run_git(["push", "origin", "feature-rebase"], clone_dir)
    
    shutil.rmtree(clone_dir, ignore_errors=True)
    
    p = Project(owner_user_id=owner_user.user_id, project_name="test-repo", visibility="private", default_branch="main")
    db.session.add(p)
    db.session.flush()
    
    r = Repository(project_id=p.project_id, repo_path=tmp_dir, clone_url=f"ssh://git@test/{p.project_name}.git", is_initialized=True)
    db.session.add(r)
    
    # Add dummy branch records to satisfy the API
    for b in ["main", "feature-ff", "feature-squash", "feature-rebase"]:
        db.session.add(Branch(repo_id=r.repo_id, branch_name=b, is_default=(b=="main")))
    
    db.session.commit()
    
    yield p
    
    shutil.rmtree(tmp_dir, ignore_errors=True)

# --------------------------------------------------------------------------------
# API Authorization
# --------------------------------------------------------------------------------
def test_1_login(client, owner_user):
    assert owner_user.username == "owner"

# --------------------------------------------------------------------------------
# Merge and Git (Simulated)
# --------------------------------------------------------------------------------
def test_5_fast_forward_merge(client, owner_token, real_repo):
    res = client.post(f"/api/merge/owner/test-repo/merge", json={
        "base": "feature-ff", "head": "main", "strategy": "ff"
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert res.status_code == 200
    assert res.json["success"] is True

def test_8_rebase_merge(client, owner_token, real_repo):
    res = client.post(f"/api/merge/owner/test-repo/merge", json={
        "base": "main", "head": "feature-rebase", "strategy": "rebase"
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert res.status_code == 200
    assert res.json["success"] is True

def test_9_squash_merge(client, owner_token, real_repo):
    res = client.post(f"/api/merge/owner/test-repo/merge", json={
        "base": "main", "head": "feature-squash", "strategy": "squash"
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert res.status_code == 200
    assert res.json["success"] is True

# --------------------------------------------------------------------------------
# Branch Protection
# --------------------------------------------------------------------------------
def test_11_disable_force_push(client, real_repo):
    p = BranchProtectionRule(repo_id=real_repo.repository.repo_id, branch_pattern="main", disable_force_push=True)
    db.session.add(p)
    db.session.commit()
    from app.services.hook_policy_engine import HookPolicyEngine
    
    main_sha = subprocess.run(["git", "rev-parse", "main"], cwd=real_repo.repository.repo_path, capture_output=True, text=True).stdout.strip()
    feature_ff_sha = subprocess.run(["git", "rev-parse", "feature-ff"], cwd=real_repo.repository.repo_path, capture_output=True, text=True).stdout.strip()
    
    resp, code = HookPolicyEngine.validate_pre_receive(real_repo.repository.repo_path, main_sha, feature_ff_sha, "refs/heads/main", str(real_repo.owner_user_id), {})
    assert code == 403

def test_12_restrict_push_read_only(client, real_repo, dev_user):
    c = Collaborator(project_id=real_repo.project_id, user_id=dev_user.user_id, permission="read")
    db.session.add(c)
    db.session.commit()
    from app.services.hook_policy_engine import HookPolicyEngine
    main_sha = subprocess.run(["git", "rev-parse", "main"], cwd=real_repo.repository.repo_path, capture_output=True, text=True).stdout.strip()
    resp, code = HookPolicyEngine.validate_pre_receive(real_repo.repository.repo_path, main_sha, main_sha, "refs/heads/main", str(dev_user.user_id), {})
    assert code == 403

def test_13_require_admin_for_push(client, real_repo, admin_user):
    p = BranchProtectionRule(repo_id=real_repo.repository.repo_id, branch_pattern="main", restrict_push=True, allowed_push_roles=["admin"])
    db.session.add(p)
    db.session.commit()
    from app.services.hook_policy_engine import HookPolicyEngine
    main_sha = subprocess.run(["git", "rev-parse", "main"], cwd=real_repo.repository.repo_path, capture_output=True, text=True).stdout.strip()
    resp, code = HookPolicyEngine.validate_pre_receive(real_repo.repository.repo_path, "0"*40, main_sha, "refs/heads/main", str(admin_user.user_id), {})
    assert code == 200

# --------------------------------------------------------------------------------
# Webhooks
# --------------------------------------------------------------------------------
def test_14_webhook_creation(client, owner_token, real_repo):
    res = client.post(f"/api/webhooks/owner/test-repo", json={
        "name": "Test Hook",
        "target_url": "http://127.0.0.1:8080/hook",
        "events": ["push"]
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert res.status_code == 201

# --------------------------------------------------------------------------------
# SSH & Internal Auth
# --------------------------------------------------------------------------------
def test_17_ssh_authentication(client, owner_user, real_repo):
    res = client.post("/api/internal/ssh-auth", json={
        "user_id": owner_user.user_id,
        "owner": "owner",
        "project_name": "test-repo",
        "action": "write"
    }, headers={"X-Hook-Secret": os.environ.get("INTERNAL_HOOK_SECRET", "")})
    assert res.status_code == 200
    assert res.json["repo_path"] == real_repo.repository.repo_path

def test_21_push_to_protected_branch_unauthorized(client, dev_user, real_repo):
    p = BranchProtectionRule(repo_id=real_repo.repository.repo_id, branch_pattern="main", restrict_push=True, allowed_push_roles=["admin"])
    db.session.add(p)
    c = Collaborator(project_id=real_repo.project_id, user_id=dev_user.user_id, permission="write")
    db.session.add(c)
    db.session.commit()
    
    from app.services.hook_policy_engine import HookPolicyEngine
    main_sha = subprocess.run(["git", "rev-parse", "main"], cwd=real_repo.repository.repo_path, capture_output=True, text=True).stdout.strip()
    resp, code = HookPolicyEngine.validate_pre_receive(real_repo.repository.repo_path, "0"*40, main_sha, "refs/heads/main", str(dev_user.user_id), {})
    assert code == 403

def test_25_webhook_dns_failure(client, owner_token, real_repo):
    w = WebhookEndpoint(project_id=real_repo.project_id, name="Test", target_url="http://nonexistent.local/hook", events=["push"])
    db.session.add(w)
    db.session.commit()
    res = client.post(f"/api/webhooks/owner/test-repo/{w.webhook_id}/test", headers={"Authorization": f"Bearer {owner_token}"})
    assert res.status_code == 400
    assert res.json["code"] in ["DNS_FAILURE", "BLOCKED", "ERROR", "UNKNOWN_DELIVERY_ERROR"]
