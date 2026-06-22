from .celery_app import celery
from .services import backup_service
import logging

logger = logging.getLogger(__name__)

@celery.task
def run_full_backup_task(dest_dir: str, triggered_by: int = None):
    # We must ensure app context if we do DB operations
    # For Celery we usually create a bare app and push context
    from app import create_app
    app = create_app()
    with app.app_context():
        backup_service.run_full_backup(dest_dir, triggered_by=triggered_by)

@celery.task
def restore_backup_task(filename: str, dest_dir: str):
    from app import create_app
    app = create_app()
    with app.app_context():
        try:
            backup_service.restore_backup(filename, dest_dir)
        except Exception as e:
            backup_service.logger.error(f"Restore failed for {filename}: {e}")

@celery.task
def async_post_receive_task(payload: dict):
    from app import create_app
    from app.services import webhook_service
    from app.models.project import Project
    app = create_app()
    with app.app_context():
        project_id = payload.get("project_id")
        project = Project.query.filter_by(project_id=project_id).first()
        if not project:
            return
        
        actor = payload.get("actor", {})
        username = actor.get("username", "unknown")
        for ref in payload.get("refs", []):
            if not ref["ref_name"].startswith("refs/heads/"):
                continue
            branch_name = ref["ref_name"].replace("refs/heads/", "")
            
            webhook_service.dispatch_event(project_id, "push", {
                "project": project.project_name,
                "branch": branch_name,
                "old_sha": ref["old_sha"],
                "new_sha": ref["new_sha"],
                "actor": actor,
                "pusher": username,
            })
