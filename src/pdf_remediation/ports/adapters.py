from __future__ import annotations

from typing import Any, Protocol

from pdf_remediation.ir import DocumentIR, SemanticDocumentIR, ValidationResult


class PDFParser(Protocol):
    def parse(self, content: bytes) -> DocumentIR: ...


class PDFExtractor(Protocol):
    def extract(self, content: bytes) -> DocumentIR: ...


class OCRProvider(Protocol):
    def recognize(self, content: bytes, document: DocumentIR | None = None) -> DocumentIR: ...


class LayoutAnalyzer(Protocol):
    def analyze_layout(self, document: DocumentIR) -> DocumentIR: ...


class SemanticAnalyzer(Protocol):
    def analyze(self, document: DocumentIR) -> SemanticDocumentIR: ...


class MultimodalModel(Protocol):
    def infer(self, content: bytes, document: DocumentIR) -> SemanticDocumentIR: ...


class StructureGenerator(Protocol):
    def generate(self, document: DocumentIR) -> SemanticDocumentIR: ...


class PDFRemediator(Protocol):
    def remediate(self, source: bytes, semantics: SemanticDocumentIR) -> bytes: ...


class TaggingEngine(Protocol):
    def tag(self, source: bytes, semantics: SemanticDocumentIR) -> bytes: ...


class AccessibilityValidator(Protocol):
    def validate(
        self, content: bytes, semantics: SemanticDocumentIR | None = None
    ) -> ValidationResult: ...


class ReportGenerator(Protocol):
    def generate(self, validation: ValidationResult, context: dict[str, Any]) -> bytes: ...


class Finalizer(Protocol):
    def finalize(self, candidate: bytes, validation: ValidationResult) -> bytes: ...
