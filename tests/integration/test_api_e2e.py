from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import pdf_remediation.api.main as api
from pdf_remediation.bootstrap import build_container
from pdf_remediation.settings import Settings


def test_upload_process_and_list_artifacts(
    tmp_path: Path,
    monkeypatch,
    simple_pdf_bytes: bytes,
) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        artifact_backend="filesystem",
        artifact_root=tmp_path / "artifacts",
        recipe_dir=Path("config/pipelines"),
        run_jobs_inline=True,
        json_logs=False,
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

    job_id = payload["job"]["id"]
    artifacts_response = client.get(f"/jobs/{job_id}/artifacts")

    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    kinds = {artifact["kind"] for artifact in artifacts}
    assert "source_pdf" in kinds
    assert "document_ir" in kinds
    assert "semantic_ir" in kinds
