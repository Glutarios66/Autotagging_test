from __future__ import annotations

import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PDFR_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "sqlite:///./pdf_remediation.db"
    artifact_backend: str = "filesystem"
    artifact_root: Path = Path("./artifacts")
    recipe_dir: Path = Path("./config/pipelines")
    run_jobs_inline: bool = True
    max_upload_bytes: int = 50 * 1024 * 1024

    s3_bucket: str = "pdf-remediation"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_queue: str = "pdf-remediation"

    log_level: str = "INFO"
    json_logs: bool = False


def configure_logging(level: str, json_logs: bool = False) -> None:
    # JSON formatting can be added later without coupling it to core logic.
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
