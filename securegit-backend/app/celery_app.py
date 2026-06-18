import os
from celery import Celery

def make_celery(app_name=__name__):
    broker_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    backend_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    return Celery(
        app_name,
        broker=broker_url,
        backend=backend_url,
        include=['app.tasks']
    )

celery = make_celery()
