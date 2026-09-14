from __future__ import annotations

import json
from typing import Any

from pdf_remediation.ir import DocumentIR, SemanticDocumentIR, ValidationResult
from pdf_remediation.pipeline.runtime import PipelineContext
from pdf_remediation.ports import (
    AccessibilityValidator,
    Finalizer,
    PDFExtractor,
    PDFRemediator,
    ReportGenerator,
    SemanticAnalyzer,
)


class ExtractComponent:
    def __init__(self, adapter: PDFExtractor) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        document = self.adapter.extract(context.source_pdf)
        return {"document_ir": document}


class AnalyzeComponent:
    def __init__(self, adapter: SemanticAnalyzer) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        document = context.values["document_ir"]
        if not isinstance(document, DocumentIR):
            raise TypeError("document_ir missing")
        return {"semantic_ir": self.adapter.analyze(document)}


class RemediateComponent:
    def __init__(self, adapter: PDFRemediator) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        semantics = context.values["semantic_ir"]
        if not isinstance(semantics, SemanticDocumentIR):
            raise TypeError("semantic_ir missing")
        return {"candidate_pdf": self.adapter.remediate(context.source_pdf, semantics)}


class ValidateComponent:
    def __init__(self, adapter: AccessibilityValidator) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        candidate = context.values.get("candidate_pdf", context.source_pdf)
        if not isinstance(candidate, bytes):
            raise TypeError("candidate_pdf invalid")
        semantics = context.values.get("semantic_ir")
        semantic_ir = semantics if isinstance(semantics, SemanticDocumentIR) else None
        return {"validation": self.adapter.validate(candidate, semantic_ir)}


class FinalizeComponent:
    def __init__(self, adapter: Finalizer) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        candidate = context.values.get("candidate_pdf", context.source_pdf)
        validation = context.values["validation"]
        if not isinstance(candidate, bytes) or not isinstance(validation, ValidationResult):
            raise TypeError("finalization inputs missing")
        return {"final_pdf": self.adapter.finalize(candidate, validation)}


class ReportComponent:
    def __init__(self, adapter: ReportGenerator) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        validation = context.values["validation"]
        if not isinstance(validation, ValidationResult):
            raise TypeError("validation missing")
        return {
            "report": self.adapter.generate(
                validation,
                {"job_id": str(context.job_id), "run_id": str(context.run_id)},
            )
        }
