from app import create_app, db
from app.models.project import Project
from app.models.branch import Branch
from app.models.commit import Commit
from app.models.user import User
from app.services import git_service

app = create_app()
with app.app_context():
    project = Project.query.filter_by(project_name='dandannn22').first()
    repo = project.repository
    branch = Branch.query.filter_by(repo_id=repo.repo_id, branch_name='master').first()
    
    # 1. Update project default branch
    project.default_branch = 'master'
    branch.is_default = True
    
    # 2. Sync git HEAD
    git_service.git_set_default_branch(repo.repo_path, 'master')
    
    # 3. Sync commits
    commits = git_service.git_log(repo.repo_path, 'master', limit=100)
    synced = 0
    for c in commits:
        if Commit.query.filter_by(commit_hash=c["hash"]).first():
            continue
        author = User.query.filter_by(email=c["author_email"]).first()
        commit = Commit(
            branch_id=branch.branch_id,
            author_id=author.user_id if author else project.owner_user_id,
            commit_hash=c["hash"],
            short_hash=c["short_hash"],
            message=c["message"],
            committed_at=c["date"],
            parent_hash=c.get("parent_hash"),
        )
        db.session.add(commit)
        synced += 1

    db.session.commit()
    print(f"Fixed dandannn22. Synced {synced} commits.")
