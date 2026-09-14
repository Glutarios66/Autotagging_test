from __future__ import annotations

from pdf_remediation.pipeline.models import PipelineRecipe
from pdf_remediation.pipeline.registry import AdapterRegistry
from pdf_remediation.pipeline.runtime import PipelineContext


class PipelineStepError(RuntimeError):
    def __init__(self, step_id: str, stage_type: str, adapter: str, cause: Exception) -> None:
        self.step_id = step_id
        self.stage_type = stage_type
        self.adapter = adapter
        self.cause = cause
        super().__init__(
            f"pipeline step '{step_id}' failed "
            f"({stage_type}/{adapter}): {type(cause).__name__}: {cause}"
        )


class PipelineExecutor:
    def __init__(self, registry: AdapterRegistry) -> None:
        self.registry = registry

    def execute(self, recipe: PipelineRecipe, context: PipelineContext) -> PipelineContext:
        for step in recipe.ordered_steps():
            try:
                component = self.registry.get(step.type, step.adapter)
                outputs = component.run(context, step.config)
                context.values.update(outputs)
            except Exception as exc:
                if isinstance(exc, PipelineStepError):
                    raise
                raise PipelineStepError(step.id, step.type, step.adapter, exc) from exc
        return context
