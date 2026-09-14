from __future__ import annotations

import hashlib
import json
import re
from typing import Any, cast

from pdf_remediation.ir import (
    BoundingBox,
    DocumentElement,
    DocumentIR,
    DocumentPage,
    Provenance,
    SemanticDocumentIR,
    SemanticNode,
    ValidationCheck,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


PROVENANCE = Provenance(source="deterministic_mock", adapter="mock", confidence=1.0)


class MockPDFExtractor:
    """Deterministic token extractor for fixtures; not a production PDF parser."""

    def extract(self, content: bytes) -> DocumentIR:
        if not content.startswith(b"%PDF-"):
            raise ValueError("input is not a PDF")
        page_count = max(1, len(re.findall(rb"/Type\s*/Page(?!s)", content)))
        strings = re.findall(rb"\(([^()]*)\)\s*Tj", content)
        elements = [
            DocumentElement(
                id=f"e-{index}",
                page=1,
                kind="text",
                bbox=BoundingBox(x=72, y=72 + index * 18, width=468, height=16),
                text=value.decode("latin-1", errors="replace"),
                reading_order=index - 1,
                provenance=[PROVENANCE],
            )
            for index, value in enumerate(strings, start=1)
        ]
        if not elements:
            elements.append(
                DocumentElement(
                    id="e-1",
                    page=1,
                    kind="unknown",
                    bbox=BoundingBox(x=0, y=0, width=0, height=0),
                    metadata={"source_sha256": hashlib.sha256(content).hexdigest()},
                    provenance=[PROVENANCE],
                )
            )
        page_ids = [element.id for element in elements if element.page == 1]
        pages = [
            DocumentPage(
                number=index,
                width=612,
                height=792,
                element_ids=page_ids if index == 1 else [],
                provenance=[PROVENANCE],
            )
            for index in range(1, page_count + 1)
        ]
        return DocumentIR(
            document_id=hashlib.sha256(content).hexdigest(),
            page_count=page_count,
            pages=pages,
            elements=elements,
            provenance=[PROVENANCE],
        )


class MockSemanticAnalyzer:
    def analyze(self, document: DocumentIR) -> SemanticDocumentIR:
        children: list[SemanticNode] = []
        for index, element in enumerate(document.elements):
            roles = {"image": "figure", "table": "table", "form": "form"}
            role = roles.get(element.kind, "heading" if index == 0 else "paragraph")
            children.append(
                SemanticNode(
                    id=f"node-{element.id}",
                    role=cast(Any, role),
                    source_element_ids=[element.id],
                    attributes={"text": element.text or ""},
                    confidence=1.0,
                    provenance=[PROVENANCE],
                )
            )
        return SemanticDocumentIR(
            document_id=document.document_id,
            root=SemanticNode(
                id="root",
                role="document",
                children=children,
                confidence=1.0,
                provenance=[PROVENANCE],
            ),
            provenance=[PROVENANCE],
        )


class MockMultimodalModel:
    def __init__(self) -> None:
        self.analyzer = MockSemanticAnalyzer()

    def infer(self, content: bytes, document: DocumentIR) -> SemanticDocumentIR:
        result = self.analyzer.analyze(document)
        result.provenance = [
            Provenance(
                source="multimodal_mock",
                adapter="mock_multimodal",
                model="deterministic-fixture-model",
                confidence=0.9,
                details={"source_size": len(content)},
            )
        ]
        return result


class MockPDFRemediator:
    def remediate(self, source: bytes, semantics: SemanticDocumentIR) -> bytes:
        marker = (
            f"\n% PDF-REMEDIATION-MOCK tagged=true nodes={len(semantics.root.children)}\n"
        ).encode()
        eof = source.rfind(b"%%EOF")
        return source[:eof] + marker + source[eof:] if eof >= 0 else source + marker


class MockAccessibilityValidator:
    def validate(
        self, content: bytes, semantics: SemanticDocumentIR | None = None
    ) -> ValidationResult:
        is_pdf = content.startswith(b"%PDF-")
        tagged = b"PDF-REMEDIATION-MOCK tagged=true" in content
        checks = [
            ValidationCheck(rule="pdf.header", passed=is_pdf, provenance=[PROVENANCE]),
            ValidationCheck(rule="pdfua.tagged", passed=tagged, provenance=[PROVENANCE]),
        ]
        issues: list[ValidationIssue] = []
        if not is_pdf:
            issues.append(
                ValidationIssue(
                    code="not_pdf",
                    message="Content does not have a PDF header",
                    severity=ValidationSeverity.ERROR,
                    provenance=[PROVENANCE],
                )
            )
        if semantics is not None and not semantics.root.children:
            issues.append(
                ValidationIssue(
                    code="empty_structure_tree",
                    message="Semantic structure has no children",
                    severity=ValidationSeverity.ERROR,
                    provenance=[PROVENANCE],
                )
            )
        if semantics is not None and not tagged:
            issues.append(
                ValidationIssue(
                    code="missing_mock_tag_marker",
                    message="Candidate has no mock tag marker",
                    severity=ValidationSeverity.ERROR,
                    provenance=[PROVENANCE],
                )
            )
        return ValidationResult(
            standard="PDF/UA-1-mock",
            passed=not issues,
            score=sum(check.passed for check in checks) / len(checks),
            checks=checks,
            issues=issues,
            provenance=[PROVENANCE],
        )


class MockFinalizer:
    def finalize(self, candidate: bytes, validation: ValidationResult) -> bytes:
        if not validation.passed:
            raise ValueError("candidate failed validation")
        marker = b"\n% PDF-REMEDIATION-MOCK final=true\n"
        eof = candidate.rfind(b"%%EOF")
        return candidate[:eof] + marker + candidate[eof:] if eof >= 0 else candidate + marker


class MockReportGenerator:
    def generate(self, validation: ValidationResult, context: dict[str, Any]) -> bytes:
        return json.dumps(
            {"context": context, "validation": validation.model_dump(mode="json")},
            indent=2,
            sort_keys=True,
        ).encode()
