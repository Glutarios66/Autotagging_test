from __future__ import annotations

from celery import Celery

from pdf_remediation.settings import Settings

settings = Settings()
celery_app = Celery(
    "pdf_remediation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_default_queue = settings.celery_queue
