from __future__ import annotations

from pdf_remediation.ir import (
    BoundingBox,
    DocumentElement,
    DocumentIR,
    DocumentPage,
    Provenance,
)


def test_document_ir_json_roundtrip() -> None:
    provenance = Provenance(
        source="fixture",
        adapter="test",
        adapter_version="1",
        confidence=1.0,
    )
    original = DocumentIR(
        document_id="doc-1",
        page_count=1,
        pages=[
            DocumentPage(
                number=1,
                width=612,
                height=792,
                element_ids=["e-1"],
                provenance=[provenance],
            )
        ],
        elements=[
            DocumentElement(
                id="e-1",
                page=1,
                kind="text",
                bbox=BoundingBox(x=10, y=20, width=100, height=12),
                text="Hello",
                reading_order=0,
                provenance=[provenance],
            )
        ],
        provenance=[provenance],
    )

    restored = DocumentIR.model_validate_json(original.model_dump_json())

    assert restored == original
    assert restored.elements[0].bbox.coordinate_space == "pdf_points"
