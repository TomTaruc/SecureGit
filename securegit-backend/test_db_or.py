from app import create_app
from app.extensions import db
from app.models.project import Project

app = create_app()
app.app_context().push()

user_id = 2
collaborated_ids = [1, 2]
q = Project.query.filter(db.or_(Project.owner_user_id == user_id, Project.project_id.in_(collaborated_ids)), Project.deleted_at.is_(None))
print(q)
