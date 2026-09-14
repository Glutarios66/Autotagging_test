from __future__ import annotations

import pytest

from pdf_remediation.adapters import PyMuPDFExtractor


def test_pymupdf_extractor_maps_pdf_to_document_ir(simple_pdf_bytes: bytes) -> None:
    result = PyMuPDFExtractor().extract(simple_pdf_bytes)
    assert result.page_count == 2
    assert result.metadata["extractor"] == "pymupdf"
    text = [e for e in result.elements if e.kind == "text"]
    assert any("Accessibility Research" in (e.text or "") for e in text)
    assert any("Second page" in (e.text or "") for e in text)
    assert [e.reading_order for e in result.elements] == list(range(len(result.elements)))


def test_pymupdf_extractor_rejects_non_pdf() -> None:
    with pytest.raises(ValueError, match="not a PDF"):
        PyMuPDFExtractor().extract(b"not a pdf")
