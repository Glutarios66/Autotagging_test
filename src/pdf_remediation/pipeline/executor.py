from __future__ import annotations

from pdf_remediation.pipeline.models import PipelineRecipe
from pdf_remediation.pipeline.registry import AdapterRegistry
from pdf_remediation.pipeline.runtime import PipelineContext


class PipelineExecutor:
    def __init__(self, registry: AdapterRegistry) -> None:
        self.registry = registry

    def execute(self, recipe: PipelineRecipe, context: PipelineContext) -> PipelineContext:
        for step in recipe.ordered_steps():
            component = self.registry.get(step.type, step.adapter)
            outputs = component.run(context, step.config)
            context.values.update(outputs)
        return context
