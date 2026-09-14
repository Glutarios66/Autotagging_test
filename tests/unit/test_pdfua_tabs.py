from io import BytesIO

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("fontTools")

from pdf_remediation.adapters.pdfua_normalizer import PDFUAConformanceNormalizer


def test_pages_with_annotations_get_tabs_s() -> None:
    source = BytesIO()
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page(page_size=(200, 200))

    annot = pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"),
        Subtype=pikepdf.Name("/Text"),
        Rect=pikepdf.Array([10, 10, 30, 30]),
        Contents="Note",
    )
    page.obj["/Annots"] = pikepdf.Array([pdf.make_indirect(annot)])
    pdf.save(source)

    normalizer = PDFUAConformanceNormalizer(font_dirs=[])
    normalized, report = normalizer.normalize(source.getvalue())

    assert report["page_tabs"]["repaired_count"] == 1

    with pikepdf.Pdf.open(BytesIO(normalized)) as result:
        assert result.pages[0].obj["/Tabs"] == pikepdf.Name("/S")
