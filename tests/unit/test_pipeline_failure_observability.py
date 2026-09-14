from uuid import uuid4

import pytest

from pdf_remediation.pipeline.executor import PipelineExecutor, PipelineStepError
from pdf_remediation.pipeline.models import PipelineRecipe, StepSpec
from pdf_remediation.pipeline.registry import AdapterRegistry
from pdf_remediation.pipeline.runtime import PipelineContext


class Emit:
    def run(self, context, config):
        return {"first_output": b"ok"}


class Fail:
    def run(self, context, config):
        raise ValueError("boom")


def test_executor_reports_failing_step_and_preserves_prior_context() -> None:
    registry = AdapterRegistry()
    registry.register("stage", "emit", Emit())
    registry.register("stage", "fail", Fail())

    recipe = PipelineRecipe(
        name="failure",
        steps=[
            StepSpec(id="first", type="stage", adapter="emit"),
            StepSpec(id="second", type="stage", adapter="fail", needs=["first"]),
        ],
    )
    context = PipelineContext(job_id=uuid4(), run_id=uuid4(), source_pdf=b"%PDF-1.7")

    with pytest.raises(PipelineStepError, match="second"):
        PipelineExecutor(registry).execute(recipe, context)

    assert context.values["first_output"] == b"ok"
