from __future__ import annotations

from uuid import UUID

from pdf_remediation.bootstrap import build_container
from pdf_remediation.workers.celery_app import celery_app


@celery_app.task(name="pdf_remediation.process_run")
def process_run(run_id: str) -> str:
    return build_container().service.process(UUID(run_id)).status.value
