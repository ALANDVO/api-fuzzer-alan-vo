"""Celery application configuration for distributed fuzz worker queue."""
import os
from celery import Celery

# Use the same settings as the FastAPI app
environ = os.environ.copy()

# Broker and backend use Redis
broker_url = environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
result_backend = environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")

celery_app = Celery(
    "api-fuzzer-alan-vo",
    broker=broker_url,
    backend=result_backend,
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_lazy=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,  # Fair dispatch: one task at a time per worker
)

# Auto-discover tasks in the backend.app.services module
celery_app.autodiscover_tasks(["backend.app.services"])
