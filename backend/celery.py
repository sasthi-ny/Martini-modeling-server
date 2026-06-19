import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "backend",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "backend.tasks",
        "backend.modeling.polymer_tasks",
        "backend.modeling.membrane_tasks",
    ],
)


celery_app.conf.update(
    task_track_started=True,
    result_extended=True,
)

