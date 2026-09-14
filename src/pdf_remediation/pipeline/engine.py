from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from time import monotonic
from typing import Any

from pdf_remediation.domain import StageExecution, StageStatus, utc_now
from pdf_remediation.pipeline.models import PipelineComponent, PipelineContext, PipelineRecipe


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], PipelineComponent] = {}

    def register(self, stage_type: str, name: str, adapter: PipelineComponent) -> None:
        key = (stage_type, name)
        if key in self._adapters:
            raise ValueError(f"adapter already registered: {stage_type}/{name}")
        self._adapters[key] = adapter

    def get(self, stage_type: str, name: str) -> PipelineComponent:
        try:
            return self._adapters[(stage_type, name)]
        except KeyError as exc:
            raise KeyError(f"unknown adapter: {stage_type}/{name}") from exc

    def names(self, stage_type: str | None = None) -> list[str]:
        return sorted(
            f"{kind}/{name}"
            for kind, name in self._adapters
            if stage_type is None or kind == stage_type
        )


ComponentRegistry = AdapterRegistry


class RecipeRegistry:
    def __init__(self) -> None:
        self._recipes: dict[str, PipelineRecipe] = {}

    def register(self, recipe: PipelineRecipe) -> None:
        self._recipes[recipe.name] = recipe

    def get(self, name: str) -> PipelineRecipe:
        try:
            return self._recipes[name]
        except KeyError as exc:
            raise KeyError(f"unknown recipe: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._recipes)

    def all(self) -> list[PipelineRecipe]:
        return [self._recipes[name] for name in self.names()]


StageCallback = Callable[[StageExecution], None]


class PipelineExecutor:
    def __init__(self, adapters: AdapterRegistry) -> None:
        self.adapters = adapters

    def execute(
        self,
        recipe: PipelineRecipe,
        context: PipelineContext,
        *,
        from_stage: str | None = None,
        on_stage_created: StageCallback | None = None,
        on_stage_updated: StageCallback | None = None,
    ) -> PipelineContext:
        for step in recipe.steps_from(from_stage):
            execution = StageExecution(
                run_id=context.run_id,
                stage_id=step.id,
                stage_type=step.type,
                adapter_name=step.adapter,
                status=StageStatus.RUNNING,
                started_at=utc_now(),
                metadata={"config": step.config, "dependencies": step.needs},
            )
            if on_stage_created:
                on_stage_created(execution)
            context.current_stage_id = step.id
            context.current_stage_type = step.type
            context.current_adapter = step.adapter
            context.stage_started_at = execution.started_at
            started = monotonic()
            try:
                outputs = self.adapters.get(step.type, step.adapter)(context, step.config)
                context.record(step.id, outputs)
                execution.status = StageStatus.SUCCEEDED
                execution.metadata["output_names"] = sorted(outputs)
            except Exception as exc:
                execution.status = StageStatus.FAILED
                execution.error = str(exc)
                raise
            finally:
                execution.finished_at = utc_now()
                execution.duration_ms = max(0, round((monotonic() - started) * 1000))
                if on_stage_updated:
                    on_stage_updated(execution)
        context.current_stage_id = None
        context.current_stage_type = None
        context.current_adapter = None
        return context


def stage_time(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
