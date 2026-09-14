from __future__ import annotations

import pytest

from pdf_remediation.pipeline import AdapterRegistry, PipelineContext


class Component:
    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        return {"ok": True}


def test_registry_registers_and_resolves() -> None:
    registry = AdapterRegistry()
    component = Component()
    registry.register("extract", "test", component)
    assert registry.get("extract", "test") is component
    assert registry.names() == ["extract/test"]


def test_registry_rejects_duplicate() -> None:
    registry = AdapterRegistry()
    registry.register("extract", "test", Component())
    with pytest.raises(ValueError, match="already registered"):
        registry.register("extract", "test", Component())
