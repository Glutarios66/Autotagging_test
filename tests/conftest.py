from __future__ import annotations

import pymupdf
import pytest


@pytest.fixture
def simple_pdf_bytes() -> bytes:
    document = pymupdf.open()
    page1 = document.new_page(width=612, height=792)
    page1.insert_text((72, 72), "Accessibility Research", fontsize=18)
    page1.insert_text((72, 110), "First paragraph", fontsize=11)

    page2 = document.new_page(width=612, height=792)
    page2.insert_text((72, 72), "Second page", fontsize=12)

    content = document.tobytes()
    document.close()
    return content
