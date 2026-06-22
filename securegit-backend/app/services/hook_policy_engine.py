import os
import subprocess
from flask import jsonify

class HookPolicyEngine:
    @staticmethod
    def validate_pre_receive(repo_path, oldrev, newrev, ref, user_id_str, git_env=None):
        if not os.path.isabs(repo_path) or ".." in repo_path:
            return {"error": "Invalid path."}, 400

        from ..models.repository import Repository
        repo = Repository.query.filter_by(repo_path=repo_path).first()
        if not repo:
            return {"error": "Repository not found."}, 404

        import re
        ref = re.sub(r'/+', '/', ref)
        is_branch = ref.startswith("refs/heads/")
        branch_name = ref[len("refs/heads/"):] if is_branch else None
        
        is_delete = (newrev == "0000000000000000000000000000000000000000")
        is_new = (oldrev == "0000000000000000000000000000000000000000")

        user_role = None
        is_owner = False
        is_admin = False

        if user_id_str:
            from ..models.user import User
            try:
                user_id = int(user_id_str)
                user = User.query.get(user_id)
                if user:
                    from ..models.project import Project
                    project = Project.query.get(repo.project_id)
                    is_owner = (project.owner_user_id == user_id)
                    is_admin = (user.role == "admin")
                    
                    from ..utils.rbac import get_user_permission
                    user_role = get_user_permission(user_id, project.project_id) or ("owner" if is_owner else "read")
                    if is_admin:
                        user_role = "admin"
            except ValueError:
                pass
                
        # Enforce base write permissions for user-initiated pushes
        if user_id_str:
            if not user_role or (user_role not in ("write", "admin") and not is_owner):
                return {"error": f"Push access denied for role: {user_role or 'unknown'}"}, 403

        if is_branch:
            # Check Branch Protection Rules
            err, status = HookPolicyEngine._enforce_branch_protection(repo, branch_name, user_role, is_owner, oldrev, newrev, is_delete, is_new, repo_path, git_env)
            if err:
                return {"error": err}, status

        # Check Quota Enforcement
        err, status = HookPolicyEngine._enforce_quota(repo_path)
        if err:
            return {"error": err}, status

        # Check File Size Limit
        if not is_delete:
            err, status = HookPolicyEngine._enforce_large_file_limit(repo_path, oldrev, newrev, is_new)
            if err:
                return {"error": err}, status

        return {"message": "OK"}, 200

    @staticmethod
    def _enforce_branch_protection(repo, branch_name, user_role, is_owner, oldrev, newrev, is_delete, is_new, repo_path, git_env):
        from ..models.branch_protection import BranchProtectionRule
        import fnmatch

        rules = BranchProtectionRule.query.filter_by(repo_id=repo.repo_id).all()
        matched_rule = None
        for rule in rules:
            if fnmatch.fnmatch(branch_name, rule.branch_pattern):
                matched_rule = rule
                break
                
        if not matched_rule:
            return None, 200

        if not user_role:
            return "User context missing for protected branch.", 403

        if matched_rule.require_admin_for_push and user_role != "admin" and not is_owner:
            return f"Branch '{branch_name}' requires admin privileges to push.", 403

        if matched_rule.restrict_push:
            if user_role not in matched_rule.allowed_push_roles and not is_owner:
                return f"Your role ({user_role}) is not allowed to push to '{branch_name}'.", 403

        if is_delete and matched_rule.disable_deletion:
            return f"Branch '{branch_name}' is protected against deletion.", 403

        if not is_delete and not is_new and matched_rule.disable_force_push:
            sub_env = os.environ.copy()
            if git_env:
                for k, v in git_env.items():
                    if v:
                        sub_env[k] = v
            try:
                subprocess.run(
                    ["git", "merge-base", "--is-ancestor", oldrev, newrev],
                    cwd=repo_path, check=True, capture_output=True,
                    env=sub_env, user="git", group="git",
                )
            except subprocess.CalledProcessError:
                return f"Force pushing to '{branch_name}' is disabled.", 403
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("merge-base ancestor check failed unexpectedly: %s", e)
                return f"Unable to verify push safety for '{branch_name}'; push rejected as a precaution.", 403

        if not is_delete and not is_new and matched_rule.require_linear_history:
            sub_env = os.environ.copy()
            if git_env:
                for k, v in git_env.items():
                    if v:
                        sub_env[k] = v
            try:
                out = subprocess.run(
                    ["git", "rev-list", "--merges", f"{oldrev}..{newrev}"],
                    cwd=repo_path, check=True, capture_output=True, text=True,
                    env=sub_env, user="git", group="git",
                ).stdout
                if out.strip():
                    return f"Linear history required: merge commits are not allowed on '{branch_name}'.", 403
            except Exception:
                pass

        return None, 200

    @staticmethod
    def _enforce_quota(repo_path):
        from ..models.enhancement_models import ServerConfig
        quota_config = ServerConfig.query.filter_by(key="storage_quota_mb").first()
        quota_mb = int(quota_config.value) if (quota_config and quota_config.value.isdigit()) else 1024
        
        if quota_mb > 0:
            try:
                total_size = 0
                for dirpath, _, filenames in os.walk(repo_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            total_size += os.path.getsize(fp)
                repo_size_mb = total_size / (1024 * 1024)
                if repo_size_mb > quota_mb:
                    return f"Repository storage quota exceeded ({repo_size_mb:.1f}MB / {quota_mb}MB). Push rejected.", 403
            except Exception:
                pass
        return None, 200

    @staticmethod
    def _enforce_large_file_limit(repo_path, oldrev, newrev, is_new):
        from ..models.enhancement_models import ServerConfig
        limit_config = ServerConfig.query.filter_by(key="max_file_size_mb").first()
        limit_mb = int(limit_config.value) if (limit_config and limit_config.value.isdigit()) else 50
        max_file_size_bytes = limit_mb * 1024 * 1024
        
        try:
            rev_list_cmd = ["git", "rev-list", "--objects", f"{oldrev}..{newrev}"]
            if is_new:
                rev_list_cmd = ["git", "rev-list", "--objects", newrev]
            
            rev_list_out = subprocess.run(rev_list_cmd, cwd=repo_path, capture_output=True, text=True, check=True).stdout
            object_hashes = [line.split()[0] for line in rev_list_out.splitlines() if line.strip()]
            
            if object_hashes:
                cat_file_proc = subprocess.Popen(["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"], cwd=repo_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                out, _ = cat_file_proc.communicate(input="\n".join(object_hashes) + "\n")
                
                for line in out.splitlines():
                    if not line.strip(): continue
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == "blob":
                        size = int(parts[2])
                        if size > max_file_size_bytes:
                            return f"Push rejected: File exceeds the {limit_mb}MB limit ({size / (1024*1024):.1f}MB).", 403
        except Exception:
            pass
        return None, 200
