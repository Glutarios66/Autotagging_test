from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("job_id", "run_id", "stage_id"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if json_logs else logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDFR_", env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./pdf_remediation.db"
    artifact_backend: Literal["filesystem", "s3", "minio"] = "filesystem"
    artifact_root: Path = Path("./artifacts")
    s3_bucket: str = "pdf-remediation"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    recipe_dir: Path = Path("./config/pipelines")
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_queue: str = "pdf-remediation"
    run_jobs_inline: bool = True
    max_upload_bytes: int = 25 * 1024 * 1024
    log_level: str = "INFO"
    json_logs: bool = True
