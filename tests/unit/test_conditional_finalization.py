from uuid import uuid4

from pdf_remediation.adapters.finalization import PassThroughFinalizer
from pdf_remediation.ir import ValidationResult
from pdf_remediation.pipeline.components import FinalizeComponent
from pdf_remediation.pipeline.runtime import PipelineContext


def test_final_pdf_is_not_emitted_when_validation_fails() -> None:
    context = PipelineContext(job_id=uuid4(), run_id=uuid4(), source_pdf=b"%PDF-1.7")
    context.values["normalized_pdf"] = b"%PDF-1.7 normalized"
    context.values["validation"] = ValidationResult(
        valid=False,
        validator="veraPDF",
    )
    component = FinalizeComponent(PassThroughFinalizer())
    result = component.run(
        context,
        {
            "input": "normalized_pdf",
            "validation": "validation",
            "require_valid": True,
        },
    )
    assert result == {}
