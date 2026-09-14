from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    coordinate_space: str = "pdf_points"


class Provenance(BaseModel):
    source: str
    adapter: str | None = None
    adapter_version: str | None = None
    confidence: float | None = None
    source_element_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class DocumentElement(BaseModel):
    id: str
    page: int
    kind: str
    bbox: BoundingBox
    text: str | None = None
    reading_order: int | None = None
    style: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)


class DocumentPage(BaseModel):
    number: int
    width: float
    height: float
    rotation: int = 0
    element_ids: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)


class DocumentIR(BaseModel):
    document_id: str
    page_count: int
    pages: list[DocumentPage] = Field(default_factory=list)
    elements: list[DocumentElement] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SemanticNode(BaseModel):
    id: str
    role: str
    source_element_ids: list[str] = Field(default_factory=list)
    text: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticDocumentIR(BaseModel):
    document_id: str
    nodes: list[SemanticNode] = Field(default_factory=list)
    reading_order: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    element_id: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    validator: str
    issues: list[ValidationIssue] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
