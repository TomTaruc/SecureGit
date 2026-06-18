import pytest
from app.services.hook_policy_engine import HookPolicyEngine

import pytest
from app.services.hook_policy_engine import HookPolicyEngine

def test_pre_receive_hook_policy(app, db_session, project, normal_user):
    from app.models.repository import Repository
    repo = Repository.query.filter_by(project_id=project.project_id).first()
    
    # Valid branch update
    resp, status = HookPolicyEngine.validate_pre_receive(
        repo_path=repo.repo_path,
        oldrev="1234567890abcdef",
        newrev="abcdef1234567890",
        ref="refs/heads/main",
        user_id_str=str(normal_user.user_id)
    )
    assert status == 200

    # Branch protection test
    from app.models.branch_protection import BranchProtectionRule
    bp = BranchProtectionRule(repo_id=repo.repo_id, branch_pattern="main", disable_force_push=True)
    db_session.add(bp)
    db_session.commit()

    # Try force push (mocking subprocess.run to raise exception for merge-base)
    from unittest.mock import patch
    import subprocess
    
    original_run = subprocess.run
    def mock_subprocess_run(*args, **kwargs):
        if "merge-base" in args[0]:
            raise subprocess.CalledProcessError(1, args[0])
        return original_run(*args, **kwargs)

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        resp, status = HookPolicyEngine.validate_pre_receive(
            repo_path=repo.repo_path,
            oldrev="1234567890abcdef",
            newrev="abcdef1234567890",
            ref="refs/heads/main",
            user_id_str=str(normal_user.user_id)
        )
        assert status == 403
        assert "Force pushing" in resp["error"]
