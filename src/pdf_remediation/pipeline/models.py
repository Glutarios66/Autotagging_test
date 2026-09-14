from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class StepSpec(BaseModel):
    id: str
    type: str
    adapter: str
    needs: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class PipelineRecipe(BaseModel):
    name: str
    description: str = ""
    version: str = "1"
    steps: list[StepSpec]

    @model_validator(mode="after")
    def validate_graph(self) -> PipelineRecipe:
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("step ids must be unique")
        known = set(ids)
        for step in self.steps:
            missing = set(step.needs) - known
            if missing:
                raise ValueError(
                    f"step {step.id} has unknown dependencies: {sorted(missing)}"
                )
            if step.id in step.needs:
                raise ValueError(f"step {step.id} cannot depend on itself")
        self.ordered_steps()
        return self

    def ordered_steps(self) -> list[StepSpec]:
        remaining = {step.id: step for step in self.steps}
        completed: set[str] = set()
        result: list[StepSpec] = []
        while remaining:
            ready = [step for step in self.steps if step.id in remaining and set(step.needs) <= completed]
            if not ready:
                blocked = {key: value.needs for key, value in remaining.items()}
                raise ValueError(f"pipeline contains a dependency cycle: {blocked}")
            for step in ready:
                result.append(step)
                completed.add(step.id)
                del remaining[step.id]
        return result

    def steps_from(self, stage_id: str | None) -> list[StepSpec]:
        ordered = self.ordered_steps()
        if stage_id is None:
            return ordered
        positions = {step.id: index for index, step in enumerate(ordered)}
        if stage_id not in positions:
            raise ValueError(f"unknown rerun stage: {stage_id}")
        required = {stage_id}
        changed = True
        while changed:
            changed = False
            for step in ordered:
                if set(step.needs) & required and step.id not in required:
                    required.add(step.id)
                    changed = True
        return [step for step in ordered if step.id in required]


@dataclass
class PipelineContext(MutableMapping[str, Any]):
    job_id: UUID
    run_id: UUID
    recipe_name: str
    values: dict[str, Any] = field(default_factory=dict)
    step_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    current_stage_id: str | None = None
    current_stage_type: str | None = None
    current_adapter: str | None = None
    stage_started_at: datetime | None = None

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.values[key] = value

    def __delitem__(self, key: str) -> None:
        del self.values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def record(self, stage_id: str, outputs: dict[str, Any]) -> None:
        self.step_outputs[stage_id] = outputs
        self.values.update(outputs)


class PipelineComponent(Protocol):
    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]: ...
