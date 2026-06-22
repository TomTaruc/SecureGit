from app import create_app
from app.extensions import db
from app.models.project import Project

app = create_app()
app.app_context().push()
print(Project.query.filter(db.or_(Project.owner_user_id == 2, Project.project_id.in_([1]))).count())
