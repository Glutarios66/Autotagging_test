from __future__ import annotations

from pdf_remediation.ir import DocumentIR, SemanticDocumentIR, ValidationResult
from pdf_remediation.pipeline.runtime import PipelineContext
from pdf_remediation.ports import (
    AccessibilityValidator,
    Finalizer,
    PDFExtractor,
    PDFNormalizer,
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


class NormalizeComponent:
    def __init__(self, adapter: PDFNormalizer) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        input_key = str(config.get("input", "candidate_pdf"))
        output_key = str(config.get("output", "normalized_pdf"))
        report_key = str(config.get("report_output", "normalization_report"))

        candidate = context.values.get(input_key)
        if not isinstance(candidate, bytes):
            raise TypeError(f"{input_key} missing or invalid")

        normalized, report = self.adapter.normalize(candidate)
        import json

        return {
            output_key: normalized,
            report_key: json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
        }


class ValidateComponent:
    def __init__(self, adapter: AccessibilityValidator) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        input_key = str(config.get("input", "candidate_pdf"))
        output_key = str(config.get("output", "validation"))

        if input_key == "source_pdf":
            candidate = context.source_pdf
        else:
            candidate = context.values.get(input_key, context.source_pdf)

        if not isinstance(candidate, bytes):
            raise TypeError(f"{input_key} invalid")

        semantics = context.values.get("semantic_ir")
        semantic_ir = semantics if isinstance(semantics, SemanticDocumentIR) else None
        return {output_key: self.adapter.validate(candidate, semantic_ir)}


class FinalizeComponent:
    def __init__(self, adapter: Finalizer) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        input_key = str(config.get("input", "candidate_pdf"))
        validation_key = str(config.get("validation", "validation"))
        output_key = str(config.get("output", "final_pdf"))
        require_valid = bool(config.get("require_valid", False))

        candidate = context.values.get(input_key, context.source_pdf)
        validation = context.values.get(validation_key)
        if not isinstance(candidate, bytes) or not isinstance(validation, ValidationResult):
            raise TypeError("finalization inputs missing")

        if require_valid and not validation.valid:
            return {}

        return {output_key: self.adapter.finalize(candidate, validation)}


class ReportComponent:
    def __init__(self, adapter: ReportGenerator) -> None:
        self.adapter = adapter

    def run(self, context: PipelineContext, config: dict[str, object]) -> dict[str, object]:
        validation_key = str(config.get("validation", "validation"))
        validation = context.values.get(validation_key)
        if not isinstance(validation, ValidationResult):
            raise TypeError(f"{validation_key} missing")

        return {
            "report": self.adapter.generate(
                validation,
                {
                    "job_id": str(context.job_id),
                    "run_id": str(context.run_id),
                    "preflight_validation": context.values.get("preflight_validation"),
                    "normalization_report": context.values.get("normalization_report"),
                },
            )
        }
