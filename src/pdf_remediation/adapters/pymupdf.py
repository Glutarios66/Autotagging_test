from __future__ import annotations

import hashlib
from typing import Any

import pymupdf

from pdf_remediation.ir import BoundingBox, DocumentElement, DocumentIR, DocumentPage, Provenance


class PyMuPDFExtractor:
    adapter_name = "pymupdf"

    def __init__(self) -> None:
        self._version = str(getattr(pymupdf, "VersionBind", "unknown"))

    def extract(self, content: bytes) -> DocumentIR:
        if not content.startswith(b"%PDF-"):
            raise ValueError("input is not a PDF")

        sha256 = hashlib.sha256(content).hexdigest()

        try:
            document = pymupdf.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise ValueError(f"PyMuPDF could not open PDF: {exc}") from exc

        with document:
            if document.needs_pass:
                raise ValueError("encrypted PDF requires a password")

            pages: list[DocumentPage] = []
            elements: list[DocumentElement] = []
            warnings: list[str] = []
            reading_order = 0

            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                page_number = page_index + 1
                page_ids: list[str] = []

                try:
                    page_dict: dict[str, Any] = page.get_text("dict")
                except Exception as exc:
                    warnings.append(f"page {page_number}: extraction failed: {exc}")
                    page_dict = {"blocks": []}

                blocks = page_dict.get("blocks", [])
                if not isinstance(blocks, list):
                    blocks = []

                for block_index, block in enumerate(blocks, start=1):
                    if not isinstance(block, dict):
                        continue
                    element = self._from_block(
                        block,
                        page_number=page_number,
                        block_index=block_index,
                        reading_order=reading_order,
                    )
                    if element is None:
                        continue
                    elements.append(element)
                    page_ids.append(element.id)
                    reading_order += 1

                rect = page.rect
                pages.append(
                    DocumentPage(
                        number=page_number,
                        width=float(rect.width),
                        height=float(rect.height),
                        rotation=int(page.rotation),
                        element_ids=page_ids,
                        provenance=[
                            self._provenance(
                                "pdf_page",
                                details={"page_number": page_number, "coordinate_origin": "top_left"},
                            )
                        ],
                    )
                )

            return DocumentIR(
                document_id=sha256,
                page_count=document.page_count,
                pages=pages,
                elements=elements,
                metadata={
                    "extractor": self.adapter_name,
                    "extractor_version": self._version,
                    "pdf_metadata": {
                        str(k): v
                        for k, v in (document.metadata or {}).items()
                        if v not in (None, "")
                    },
                },
                provenance=[
                    self._provenance("pdf", details={"source_sha256": sha256})
                ],
                warnings=warnings,
            )

    def _from_block(
        self,
        block: dict[str, Any],
        *,
        page_number: int,
        block_index: int,
        reading_order: int,
    ) -> DocumentElement | None:
        block_type = int(block.get("type", -1))
        if block_type not in {0, 1}:
            return None

        element_id = f"p{page_number}-b{block_index}"
        bbox = self._bbox(block.get("bbox"))

        if block_type == 0:
            text, style = self._text_and_style(block)
            if not text:
                return None
            return DocumentElement(
                id=element_id,
                page=page_number,
                kind="text",
                bbox=bbox,
                text=text,
                reading_order=reading_order,
                style=style,
                metadata={"block_number": block.get("number", block_index - 1)},
                provenance=[
                    self._provenance(
                        "pymupdf_text_block",
                        source_element_ids=[element_id],
                        details={"coordinate_origin": "top_left"},
                    )
                ],
            )

        image = block.get("image")
        metadata: dict[str, Any] = {
            "block_number": block.get("number", block_index - 1),
            "image_width": block.get("width"),
            "image_height": block.get("height"),
            "extension": block.get("ext"),
            "colorspace": block.get("colorspace"),
            "bits_per_component": block.get("bpc"),
            "x_resolution": block.get("xres"),
            "y_resolution": block.get("yres"),
        }
        if isinstance(image, (bytes, bytearray)):
            metadata["image_sha256"] = hashlib.sha256(bytes(image)).hexdigest()

        return DocumentElement(
            id=element_id,
            page=page_number,
            kind="image",
            bbox=bbox,
            reading_order=reading_order,
            metadata={k: v for k, v in metadata.items() if v is not None},
            provenance=[
                self._provenance(
                    "pymupdf_image_block",
                    source_element_ids=[element_id],
                    details={"coordinate_origin": "top_left"},
                )
            ],
        )

    @staticmethod
    def _bbox(raw: Any) -> BoundingBox:
        if not isinstance(raw, (tuple, list)) or len(raw) != 4:
            return BoundingBox(x=0, y=0, width=0, height=0)
        x0, y0, x1, y1 = (float(v) for v in raw)
        return BoundingBox(
            x=x0,
            y=y0,
            width=max(0.0, x1 - x0),
            height=max(0.0, y1 - y0),
        )

    @staticmethod
    def _text_and_style(block: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        text_lines: list[str] = []
        fonts: set[str] = set()
        sizes: set[float] = set()

        lines = block.get("lines", [])
        if not isinstance(lines, list):
            return "", {}

        for line in lines:
            if not isinstance(line, dict):
                continue
            parts: list[str] = []
            spans = line.get("spans", [])
            if not isinstance(spans, list):
                continue
            for span in spans:
                if not isinstance(span, dict):
                    continue
                value = span.get("text")
                if isinstance(value, str):
                    parts.append(value)
                font = span.get("font")
                if isinstance(font, str) and font:
                    fonts.add(font)
                size = span.get("size")
                if isinstance(size, (int, float)):
                    sizes.add(round(float(size), 4))
            line_text = "".join(parts).strip()
            if line_text:
                text_lines.append(line_text)

        style: dict[str, Any] = {}
        if fonts:
            style["fonts"] = sorted(fonts)
        if sizes:
            style["font_sizes"] = sorted(sizes)
        return "\n".join(text_lines), style

    def _provenance(
        self,
        source: str,
        *,
        source_element_ids: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> Provenance:
        return Provenance(
            source=source,
            adapter=self.adapter_name,
            adapter_version=self._version,
            confidence=1.0,
            source_element_ids=source_element_ids or [],
            details=details or {},
        )
