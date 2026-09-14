from pathlib import Path

from pdf_remediation.adapters.pdfua_normalizer import PDFUAConformanceNormalizer


def test_font_key_strips_subset_prefix() -> None:
    assert PDFUAConformanceNormalizer._font_key("/ABCDEF+ArialMT") == "arialmt"
    assert PDFUAConformanceNormalizer._font_key("ArialMT") == "arialmt"


def test_embedding_restrictions() -> None:
    assert PDFUAConformanceNormalizer._embedding_allowed(0)[0] is True
    assert PDFUAConformanceNormalizer._embedding_allowed(0x0002)[0] is False
    assert PDFUAConformanceNormalizer._embedding_allowed(0x0200)[0] is False


def test_explicit_font_dirs_are_retained() -> None:
    normalizer = PDFUAConformanceNormalizer(font_dirs=[Path("/tmp/fonts")])
    assert normalizer.font_dirs == (Path("/tmp/fonts"),)
