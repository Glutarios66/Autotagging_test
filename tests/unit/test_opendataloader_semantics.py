from pdf_remediation.adapters.opendataloader import OpenDataLoaderSemanticAnalyzer
from pdf_remediation.ir import BoundingBox, DocumentElement, DocumentIR, DocumentPage


def test_opendataloader_semantic_mapping() -> None:
    document = DocumentIR(
        document_id="doc",
        page_count=1,
        pages=[DocumentPage(number=1, width=100, height=100, element_ids=["a", "b"])],
        elements=[
            DocumentElement(
                id="a",
                page=1,
                kind="text",
                bbox=BoundingBox(x=0, y=0, width=10, height=10),
                text="Title",
                reading_order=0,
                metadata={"odl_type": "heading", "heading_level": 1},
            ),
            DocumentElement(
                id="b",
                page=1,
                kind="text",
                bbox=BoundingBox(x=0, y=20, width=10, height=10),
                text="Body",
                reading_order=1,
                metadata={"odl_type": "paragraph"},
            ),
        ],
    )

    semantics = OpenDataLoaderSemanticAnalyzer().analyze(document)
    assert [node.role for node in semantics.nodes] == ["H1", "P"]
    assert semantics.reading_order == ["semantic-a", "semantic-b"]
