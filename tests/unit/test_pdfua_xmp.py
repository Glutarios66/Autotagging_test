from io import BytesIO

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("fontTools")

from pdf_remediation.adapters.pdfua_normalizer import PDFUAConformanceNormalizer


def test_pdfua_identification_is_written() -> None:
    source = BytesIO()
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    pdf.save(source)

    normalizer = PDFUAConformanceNormalizer(font_dirs=[])
    normalized, report = normalizer.normalize(source.getvalue())

    assert report["pdfua_identification"]["pdfuaid:part"] == 1
    with pikepdf.Pdf.open(BytesIO(normalized)) as result:
        metadata = result.open_metadata()
        assert int(metadata["pdfuaid:part"]) == 1
