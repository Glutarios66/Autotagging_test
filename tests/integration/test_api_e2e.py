from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

import pdf_remediation.api.main as api
from pdf_remediation.bootstrap import build_container
from pdf_remediation.settings import Settings


def migrate(database_url: str) -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")


def test_upload_pymupdf_recipe(
    tmp_path: Path,
    monkeypatch,
    simple_pdf_bytes: bytes,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("PDFR_DATABASE_URL", database_url)
    migrate(database_url)

    settings = Settings(
        database_url=database_url,
        artifact_backend="filesystem",
        artifact_root=tmp_path / "artifacts",
        recipe_dir=Path("config/pipelines"),
        run_jobs_inline=True,
    )
    test_container = build_container(settings)
    monkeypatch.setattr(api, "container", lambda: test_container)

    client = TestClient(api.app)
    response = client.post(
        "/jobs",
        files={"file": ("fixture.pdf", simple_pdf_bytes, "application/pdf")},
        data={"recipe_name": "pymupdf_baseline"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["run"]["status"] == "succeeded"

    artifacts = client.get(f"/jobs/{payload['job']['id']}/artifacts").json()
    kinds = {artifact["kind"] for artifact in artifacts}
    assert {"source_pdf", "document_ir", "semantic_ir"} <= kinds
