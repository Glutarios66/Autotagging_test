from __future__ import annotations

import hashlib
import json
from typing import Any

from pdf_remediation.pipeline.models import PipelineContext
from pdf_remediation.ports import (
    AccessibilityValidator,
    Finalizer,
    MultimodalModel,
    PDFExtractor,
    PDFRemediator,
    ReportGenerator,
    SemanticAnalyzer,
)


class ExtractComponent:
    def __init__(self, extractor: PDFExtractor) -> None:
        self.extractor = extractor

    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        return {"document_ir": self.extractor.extract(context["source_bytes"])}


class AnalyzeComponent:
    def __init__(self, analyzer: SemanticAnalyzer) -> None:
        self.analyzer = analyzer

    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        return {"semantic_ir": self.analyzer.analyze(context["document_ir"])}


class MultimodalComponent:
    def __init__(self, model: MultimodalModel) -> None:
        self.model = model

    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "semantic_ir": self.model.infer(context["source_bytes"], context["document_ir"])
        }


class RemediateComponent:
    def __init__(self, remediator: PDFRemediator) -> None:
        self.remediator = remediator

    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "candidate_pdf": self.remediator.remediate(
                context["source_bytes"], context["semantic_ir"]
            )
        }


class ValidateComponent:
    def __init__(self, validator: AccessibilityValidator) -> None:
        self.validator = validator

    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        content = context.get("candidate_pdf", context["source_bytes"])
        return {"validation_result": self.validator.validate(content, context.get("semantic_ir"))}


class FinalizeComponent:
    def __init__(self, finalizer: Finalizer) -> None:
        self.finalizer = finalizer

    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "final_pdf": self.finalizer.finalize(
                context["candidate_pdf"], context["validation_result"]
            )
        }


class ReportComponent:
    def __init__(self, generator: ReportGenerator) -> None:
        self.generator = generator

    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "report": self.generator.generate(
                context["validation_result"],
                {"job_id": str(context.job_id), "run_id": str(context.run_id)},
            )
        }


class BaselineComponent:
    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        source = context["source_bytes"]
        return {
            "inventory": {
                "filename": context["filename"],
                "size": len(source),
                "sha256": hashlib.sha256(source).hexdigest(),
                "is_pdf": source.startswith(b"%PDF-"),
            }
        }


class SerializeComponent:
    def __call__(self, context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
        value = context[config["input"]]
        if hasattr(value, "model_dump_json"):
            content = value.model_dump_json(indent=2).encode()
        else:
            content = json.dumps(value, indent=2, sort_keys=True).encode()
        return {config.get("output", "serialized"): content}
