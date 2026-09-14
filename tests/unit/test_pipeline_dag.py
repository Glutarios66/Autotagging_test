from __future__ import annotations

import pytest
from pydantic import ValidationError

from pdf_remediation.pipeline import PipelineRecipe, StepSpec


def test_pipeline_orders_dependencies() -> None:
    recipe = PipelineRecipe(
        name="dag",
        steps=[
            StepSpec(id="validate", type="validation", adapter="test_adapter", needs=["analyze"]),
            StepSpec(id="extract", type="extract", adapter="test_adapter"),
            StepSpec(id="analyze", type="semantic_analysis", adapter="test_adapter", needs=["extract"]),
        ],
    )
    assert [s.id for s in recipe.ordered_steps()] == ["extract", "analyze", "validate"]


def test_pipeline_rejects_cycles() -> None:
    with pytest.raises(ValidationError, match="dependency cycle"):
        PipelineRecipe(
            name="cycle",
            steps=[
                StepSpec(id="a", type="x", adapter="test_adapter", needs=["b"]),
                StepSpec(id="b", type="x", adapter="test_adapter", needs=["a"]),
            ],
        )
