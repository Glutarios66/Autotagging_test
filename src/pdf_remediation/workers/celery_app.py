from __future__ import annotations

from celery import Celery

from pdf_remediation.settings import Settings

settings = Settings()
celery_app = Celery(
    "pdf_remediation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["pdf_remediation.workers.tasks"],
)
celery_app.conf.update(
    task_default_queue=settings.celery_queue,
    task_routes={"pdf_remediation.process_run": {"queue": settings.celery_queue}},
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
