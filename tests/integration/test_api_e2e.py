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


def _client(tmp_path: Path, monkeypatch) -> TestClient:
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
    return TestClient(api.app)


def test_api_exposes_only_current_recipes(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.get("/recipes")
    assert response.status_code == 200
    assert set(response.json()["recipes"]) == {"accessibility_full", "accessibility_ai"}


def test_recipe_status_marks_ai_unready_without_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PDFR_OPENAI_API_KEY", raising=False)
    client = _client(tmp_path, monkeypatch)

    payload = client.get("/recipes/status").json()
    assert payload["accessibility_full"]["ready"] is True
    assert payload["accessibility_ai"]["ready"] is False
    assert "semantic_analysis/openai" in payload["accessibility_ai"]["missing_adapters"]
