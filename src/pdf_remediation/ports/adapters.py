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


class StructureAnalyzer(Protocol):
    def analyze_structure(
        self,
        document: DocumentIR,
        semantics: SemanticDocumentIR | None = None,
    ) -> SemanticDocumentIR: ...


class ReadingOrderAnalyzer(Protocol):
    def analyze_reading_order(self, document: DocumentIR) -> DocumentIR: ...


class TableAnalyzer(Protocol):
    def analyze_tables(
        self,
        document: DocumentIR,
        semantics: SemanticDocumentIR | None = None,
    ) -> SemanticDocumentIR: ...


class FigureAnalyzer(Protocol):
    def analyze_figures(
        self,
        document: DocumentIR,
        semantics: SemanticDocumentIR | None = None,
    ) -> SemanticDocumentIR: ...


class AltTextGenerator(Protocol):
    def generate_alt_text(
        self,
        content: bytes,
        document: DocumentIR,
        semantics: SemanticDocumentIR,
    ) -> SemanticDocumentIR: ...


class StructureGenerator(Protocol):
    def generate(self, document: DocumentIR) -> SemanticDocumentIR: ...


class PDFRemediator(Protocol):
    def remediate(self, source: bytes, semantics: SemanticDocumentIR) -> bytes: ...


class TaggingEngine(Protocol):
    def tag(self, source: bytes, semantics: SemanticDocumentIR) -> bytes: ...


class PDFNormalizer(Protocol):
    def normalize(self, content: bytes) -> tuple[bytes, dict[str, Any]]: ...


class AccessibilityValidator(Protocol):
    def validate(
        self,
        content: bytes,
        semantics: SemanticDocumentIR | None = None,
    ) -> ValidationResult: ...


class ReportGenerator(Protocol):
    def generate(self, validation: ValidationResult, context: dict[str, Any]) -> bytes: ...


class Finalizer(Protocol):
    def finalize(self, candidate: bytes, validation: ValidationResult) -> bytes: ...
