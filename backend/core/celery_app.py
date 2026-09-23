"""PRISM Celery application for document review processing."""

from celery import Celery

from core.config import settings

celery_app = Celery(
    "prism",
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.extraction"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)
