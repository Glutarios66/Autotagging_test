from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: str
    adapter: str
    adapter_version: str = "mock-1"
    model: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_artifact_id: str | None = None
    source_element_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float = Field(ge=0)
    height: float = Field(ge=0)
    coordinate_space: Literal["pdf_points", "pixels", "normalized"] = "pdf_points"


class DocumentElement(BaseModel):
    id: str
    page: int = Field(ge=1)
    kind: Literal["text", "image", "table", "form", "annotation", "path", "unknown"]
    bbox: BoundingBox
    text: str | None = None
    reading_order: int | None = Field(default=None, ge=0)
    language: str | None = None
    style: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)


class DocumentPage(BaseModel):
    number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: int = 0
    element_ids: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)


class DocumentIR(BaseModel):
    schema_version: str = "1.0"
    document_id: str | None = None
    page_count: int = Field(ge=1)
    pages: list[DocumentPage] = Field(default_factory=list)
    elements: list[DocumentElement]
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SemanticNode(BaseModel):
    id: str
    role: Literal[
        "document",
        "part",
        "heading",
        "paragraph",
        "list",
        "list_item",
        "figure",
        "caption",
        "table",
        "table_row",
        "table_header",
        "table_cell",
        "form",
        "link",
        "artifact",
    ]
    source_element_ids: list[str] = Field(default_factory=list)
    children: list[SemanticNode] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance: list[Provenance] = Field(default_factory=list)


class SemanticDocumentIR(BaseModel):
    schema_version: str = "1.0"
    document_id: str | None = None
    root: SemanticNode
    language: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


SemanticIR = SemanticDocumentIR


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: ValidationSeverity
    rule: str | None = None
    page: int | None = None
    element_id: str | None = None
    remediable: bool = True
    provenance: list[Provenance] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    rule: str
    passed: bool
    message: str | None = None
    provenance: list[Provenance] = Field(default_factory=list)


class ValidationResult(BaseModel):
    schema_version: str = "1.0"
    standard: str
    passed: bool
    score: float | None = Field(default=None, ge=0, le=1)
    checks: list[ValidationCheck] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)
