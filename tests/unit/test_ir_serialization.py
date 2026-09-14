from pdf_remediation.ir import BoundingBox, DocumentElement, DocumentIR, DocumentPage


def test_document_ir_roundtrip() -> None:
    original = DocumentIR(
        document_id="doc-1",
        page_count=1,
        pages=[DocumentPage(number=1, width=612, height=792, element_ids=["e1"])],
        elements=[
            DocumentElement(
                id="e1",
                page=1,
                kind="text",
                bbox=BoundingBox(x=1, y=2, width=3, height=4),
                text="Hello",
                reading_order=0,
            )
        ],
    )
    restored = DocumentIR.model_validate_json(original.model_dump_json())
    assert restored == original
