from pathlib import Path

import yaml


PIPELINE_DIR = Path(__file__).resolve().parents[2] / "config" / "pipelines"


def _recipes() -> list[dict]:
    return [
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(PIPELINE_DIR.glob("*.yaml"))
    ]


def test_only_current_pipelines_are_shipped() -> None:
    names = {recipe["name"] for recipe in _recipes()}
    assert names == {"accessibility_full", "accessibility_ai"}


def test_no_mock_or_legacy_cidset_adapters_are_referenced() -> None:
    forbidden = {"mock", "cidset"}
    for recipe in _recipes():
        for step in recipe["steps"]:
            assert step["adapter"] not in forbidden


def test_both_pipelines_use_full_pdfua_normalization() -> None:
    for recipe in _recipes():
        normalizers = [
            step for step in recipe["steps"]
            if step["type"] == "normalization"
        ]
        assert len(normalizers) == 1
        assert normalizers[0]["adapter"] == "pdfua"
