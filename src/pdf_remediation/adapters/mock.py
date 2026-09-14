from __future__ import annotations

import json
from typing import Any

from pdf_remediation.ir import (
    BoundingBox,
    DocumentElement,
    DocumentIR,
    DocumentPage,
    Provenance,
    SemanticDocumentIR,
    SemanticNode,
    ValidationResult,
)


class MockPDFExtractor:
    def extract(self, content: bytes) -> DocumentIR:
        return DocumentIR(
            document_id="mock-document",
            page_count=1,
            pages=[
                DocumentPage(number=1, width=612, height=792, element_ids=["mock-text-1"])
            ],
            elements=[
                DocumentElement(
                    id="mock-text-1",
                    page=1,
                    kind="text",
                    bbox=BoundingBox(x=72, y=72, width=240, height=20),
                    text="Mock extracted text",
                    reading_order=0,
                    provenance=[Provenance(source="mock", adapter="mock")],
                )
            ],
            provenance=[Provenance(source="mock", adapter="mock")],
        )


class MockSemanticAnalyzer:
    def analyze(self, document: DocumentIR) -> SemanticDocumentIR:
        nodes = []
        for element in document.elements:
            if element.kind == "text":
                nodes.append(
                    SemanticNode(
                        id=f"semantic-{element.id}",
                        role="P",
                        source_element_ids=[element.id],
                        text=element.text,
                        confidence=1.0,
                    )
                )
        return SemanticDocumentIR(
            document_id=document.document_id,
            nodes=nodes,
            reading_order=[node.id for node in nodes],
            provenance=[Provenance(source="mock_semantics", adapter="mock")],
        )


class MockMultimodalModel:
    def infer(self, content: bytes, document: DocumentIR) -> SemanticDocumentIR:
        return MockSemanticAnalyzer().analyze(document)


class MockPDFRemediator:
    def remediate(self, source: bytes, semantics: SemanticDocumentIR) -> bytes:
        return source


class MockAccessibilityValidator:
    def validate(
        self,
        content: bytes,
        semantics: SemanticDocumentIR | None = None,
    ) -> ValidationResult:
        return ValidationResult(valid=True, validator="mock", issues=[])


class MockFinalizer:
    def finalize(self, candidate: bytes, validation: ValidationResult) -> bytes:
        return candidate


class MockReportGenerator:
    def generate(self, validation: ValidationResult, context: dict[str, Any]) -> bytes:
        return json.dumps(
            {
                "valid": validation.valid,
                "validator": validation.validator,
                "issues": [issue.model_dump() for issue in validation.issues],
                "context": context,
            },
            indent=2,
        ).encode()
