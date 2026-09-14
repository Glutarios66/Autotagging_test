from __future__ import annotations

from typing import Any
import pytest

from pdf_remediation.pipeline import AdapterRegistry, PipelineContext


def passthrough(context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True}


def test_registry_registers_and_resolves_adapter() -> None:
    registry = AdapterRegistry()
    registry.register("extract", "test", passthrough)

    assert registry.get("extract", "test") is passthrough
    assert registry.names() == ["extract/test"]
    assert registry.names("extract") == ["extract/test"]


def test_registry_rejects_duplicate_adapter() -> None:
    registry = AdapterRegistry()
    registry.register("extract", "test", passthrough)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("extract", "test", passthrough)


def test_registry_reports_unknown_adapter() -> None:
    registry = AdapterRegistry()

    with pytest.raises(KeyError, match="unknown adapter"):
        registry.get("extract", "missing")
