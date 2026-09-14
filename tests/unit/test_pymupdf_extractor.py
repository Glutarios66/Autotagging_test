from __future__ import annotations

import pytest

from pdf_remediation.adapters import PyMuPDFExtractor


def test_pymupdf_extractor_maps_pdf_to_canonical_document_ir(
    simple_pdf_bytes: bytes,
) -> None:
    result = PyMuPDFExtractor().extract(simple_pdf_bytes)

    assert result.page_count == 2
    assert len(result.pages) == 2
    assert result.document_id is not None
    assert result.metadata["extractor"] == "pymupdf"

    text_elements = [element for element in result.elements if element.kind == "text"]
    assert text_elements
    assert any("Accessibility Research" in (element.text or "") for element in text_elements)
    assert any("Second page" in (element.text or "") for element in text_elements)

    assert [element.reading_order for element in result.elements] == list(
        range(len(result.elements))
    )
    assert all(element.bbox.coordinate_space == "pdf_points" for element in result.elements)
    assert all(element.provenance for element in result.elements)
    assert all(element.provenance[0].adapter == "pymupdf" for element in result.elements)


def test_pymupdf_extractor_rejects_non_pdf() -> None:
    with pytest.raises(ValueError, match="not a PDF"):
        PyMuPDFExtractor().extract(b"not-a-pdf")
