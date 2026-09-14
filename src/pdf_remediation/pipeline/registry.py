from __future__ import annotations

from typing import Protocol

from pdf_remediation.pipeline.runtime import PipelineContext


class PipelineComponent(Protocol):
    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]: ...


class AdapterRegistry:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], PipelineComponent] = {}

    def register(self, stage_type: str, adapter: str, component: PipelineComponent) -> None:
        key = (stage_type, adapter)
        if key in self._items:
            raise ValueError(f"adapter already registered: {stage_type}/{adapter}")
        self._items[key] = component

    def get(self, stage_type: str, adapter: str) -> PipelineComponent:
        try:
            return self._items[(stage_type, adapter)]
        except KeyError as exc:
            raise KeyError(f"unknown adapter: {stage_type}/{adapter}") from exc

    def names(self, stage_type: str | None = None) -> list[str]:
        return sorted(
            f"{kind}/{name}"
            for (kind, name) in self._items
            if stage_type is None or kind == stage_type
        )


class RecipeRegistry:
    def __init__(self) -> None:
        self._recipes: dict[str, object] = {}

    def register(self, recipe: object) -> None:
        name = getattr(recipe, "name")
        self._recipes[str(name)] = recipe

    def get(self, name: str):
        try:
            return self._recipes[name]
        except KeyError as exc:
            raise KeyError(f"unknown recipe: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._recipes)
