from app import create_app
from app.extensions import db
from app.models.collaborator import Collaborator, PERMISSION_PRESETS

app = create_app()
app.app_context().push()

collabs = Collaborator.query.all()
for c in collabs:
    # Sync permissions JSONB to match the 'permission' column
    # since 'permission' was the source of truth for the UI dropdown
    preset = PERMISSION_PRESETS.get(c.permission, PERMISSION_PRESETS["read"])
    c.permissions = preset
    
db.session.commit()
print("Fixed split brain data")
