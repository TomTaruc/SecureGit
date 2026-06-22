from app import create_app
from app.extensions import db
from app.models.project import Project
from app.models.user import User
from app.utils.rbac import check_manage_collaborators

app = create_app()
app.app_context().push()

u = User.query.filter_by(username="user222").first()
p = Project.query.filter_by(project_name="test2").first()

if u and p:
    print("User role:", u.role)
    print("Owner?", p.owner_user_id == u.user_id)
    print("Can manage:", check_manage_collaborators(u, p))
else:
    print("Not found")
