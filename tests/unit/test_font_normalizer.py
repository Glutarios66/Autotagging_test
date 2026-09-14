from io import BytesIO

import pytest

pikepdf = pytest.importorskip("pikepdf")
from pikepdf import Array, Dictionary, Name, Pdf, Stream

from pdf_remediation.adapters.font_normalizer import CIDSetFontNormalizer


def _pdf_with_cidset() -> bytes:
    output = BytesIO()
    pdf = Pdf.new()
    page = pdf.add_blank_page(page_size=(200, 200))

    descriptor = Dictionary(
        Type=Name("/FontDescriptor"),
        FontName=Name("/AAAAAA+Test"),
        Flags=4,
        FontBBox=Array([0, 0, 1000, 1000]),
        ItalicAngle=0,
        Ascent=800,
        Descent=-200,
        CapHeight=700,
        StemV=80,
    )
    descriptor["/CIDSet"] = Stream(pdf, b"\\xff")

    cid = Dictionary(
        Type=Name("/Font"),
        Subtype=Name("/CIDFontType2"),
        BaseFont=Name("/AAAAAA+Test"),
        CIDSystemInfo=Dictionary(
            Registry="Adobe",
            Ordering="Identity",
            Supplement=0,
        ),
        FontDescriptor=descriptor,
    )
    type0 = Dictionary(
        Type=Name("/Font"),
        Subtype=Name("/Type0"),
        BaseFont=Name("/AAAAAA+Test"),
        Encoding=Name("/Identity-H"),
        DescendantFonts=Array([cid]),
    )
    page.obj["/Resources"] = Dictionary(Font=Dictionary(F1=type0))
    pdf.save(output)
    return output.getvalue()


def test_cidset_normalizer_removes_only_cidset() -> None:
    normalized, report = CIDSetFontNormalizer().normalize(_pdf_with_cidset())
    assert normalized.startswith(b"%PDF-")
    assert report["removed_cidset_entries"] == 1
    assert report["changed"] is True

    with pikepdf.Pdf.open(BytesIO(normalized)) as pdf:
        font = pdf.pages[0].obj["/Resources"]["/Font"]["/F1"]
        descriptor = font["/DescendantFonts"][0]["/FontDescriptor"]
        assert "/CIDSet" not in descriptor
        assert descriptor["/FontName"] == Name("/AAAAAA+Test")
