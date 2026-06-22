from app import create_app
from app.extensions import db
from app.models.project import Project
from app.models.collaborator import Collaborator
from app.models.user import User

app = create_app()
app.app_context().push()

user = User.query.filter_by(username="user222").first()
if not user:
    print("User user222 not found")
else:
    user_id = user.user_id
    owned = Project.query.filter(Project.owner_user_id == user_id, Project.deleted_at.is_(None)).all()
    collaborated_ids = [c.project_id for c in Collaborator.query.filter_by(user_id=user_id).all()]
    print("Owned:", len(owned))
    print("Collab IDs:", collaborated_ids)
    collaborated = Project.query.filter(Project.project_id.in_(collaborated_ids), Project.owner_user_id != user_id, Project.deleted_at.is_(None)).all()
    print("Collaborated:", len(collaborated))
    
    total = Project.query.filter(db.or_(Project.owner_user_id == user_id, Project.project_id.in_(collaborated_ids)), Project.deleted_at.is_(None)).count()
    print("Dashboard total:", total)
