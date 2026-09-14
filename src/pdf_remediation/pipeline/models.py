from __future__ import annotations

from collections import deque
from typing import Any

from pydantic import BaseModel, Field, model_validator


class StepSpec(BaseModel):
    id: str
    type: str
    adapter: str
    needs: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class PipelineRecipe(BaseModel):
    name: str
    description: str | None = None
    version: str = "1"
    steps: list[StepSpec]

    @model_validator(mode="after")
    def validate_graph(self) -> "PipelineRecipe":
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("step ids must be unique")
        id_set = set(ids)
        for step in self.steps:
            missing = set(step.needs) - id_set
            if missing:
                raise ValueError(f"unknown dependencies for {step.id}: {sorted(missing)}")
        self.ordered_steps()
        return self

    def ordered_steps(self) -> list[StepSpec]:
        by_id = {step.id: step for step in self.steps}
        indegree = {step.id: 0 for step in self.steps}
        downstream: dict[str, list[str]] = {step.id: [] for step in self.steps}
        order_index = {step.id: i for i, step in enumerate(self.steps)}

        for step in self.steps:
            for need in step.needs:
                indegree[step.id] += 1
                downstream[need].append(step.id)

        queue = deque(
            sorted(
                (step_id for step_id, degree in indegree.items() if degree == 0),
                key=order_index.__getitem__,
            )
        )
        result: list[StepSpec] = []

        while queue:
            current = queue.popleft()
            result.append(by_id[current])
            for child in sorted(downstream[current], key=order_index.__getitem__):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        if len(result) != len(self.steps):
            raise ValueError("dependency cycle detected")
        return result

    def steps_from(self, step_id: str) -> list[StepSpec]:
        if step_id not in {step.id for step in self.steps}:
            raise KeyError(step_id)

        wanted = {step_id}
        changed = True
        while changed:
            changed = False
            for step in self.steps:
                if step.id not in wanted and any(dep in wanted for dep in step.needs):
                    wanted.add(step.id)
                    changed = True
        return [step for step in self.ordered_steps() if step.id in wanted]
