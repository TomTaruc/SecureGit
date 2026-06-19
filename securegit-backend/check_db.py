from app import create_app
from app.extensions import db
from app.models.project import Project
from app.models.branch import Branch
from app.models.commit import Commit

app = create_app()
with app.app_context():
    project = Project.query.filter_by(project_name='dandannn22').first()
    if not project:
        print("Project not found")
    else:
        print(f"Project ID: {project.project_id}")
        print(f"Default Branch: {project.default_branch}")
        
        branches = Branch.query.filter_by(repo_id=project.repository.repo_id).all()
        print("\nBranches in DB:")
        for b in branches:
            print(f"- {b.branch_name} (is_default={b.is_default})")
            commits = Commit.query.filter_by(branch_id=b.branch_id).count()
            print(f"  Commits: {commits}")
