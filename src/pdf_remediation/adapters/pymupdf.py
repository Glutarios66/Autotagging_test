from __future__ import annotations

import hashlib
from typing import Any

import pymupdf

from pdf_remediation.ir import (
    BoundingBox,
    DocumentElement,
    DocumentIR,
    DocumentPage,
    Provenance,
)


class PyMuPDFExtractor:
    """Extract a deterministic DocumentIR from a PDF using PyMuPDF.

    The adapter intentionally emits the project's existing DocumentIR. It does
    not create a PyMuPDF-specific IR, which keeps downstream pipeline stages
    extractor-agnostic.

    PyMuPDF coordinates use a top-left origin. Bounding boxes are expressed in
    points and are therefore stored as ``pdf_points`` with the origin recorded
    in provenance details.
    """

    adapter_name = "pymupdf"

    def __init__(self) -> None:
        self._version = self._detect_version()

    def extract(self, content: bytes) -> DocumentIR:
        if not content.startswith(b"%PDF-"):
            raise ValueError("input is not a PDF")

        source_sha256 = hashlib.sha256(content).hexdigest()
        document_provenance = self._provenance(
            source="pdf",
            details={"source_sha256": source_sha256},
        )

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
                page_element_ids: list[str] = []

                try:
                    page_dict: dict[str, Any] = page.get_text("dict")
                except Exception as exc:
                    warnings.append(f"page {page_number}: text extraction failed: {exc}")
                    page_dict = {"blocks": []}

                blocks = page_dict.get("blocks", [])
                if not isinstance(blocks, list):
                    blocks = []

                for block_index, raw_block in enumerate(blocks, start=1):
                    if not isinstance(raw_block, dict):
                        continue

                    block_type = int(raw_block.get("type", -1))
                    element = self._element_from_block(
                        raw_block,
                        page_number=page_number,
                        block_index=block_index,
                        reading_order=reading_order,
                    )
                    if element is None:
                        continue

                    # PyMuPDF block types 0 and 1 are text and image blocks.
                    # Unsupported block types are intentionally skipped instead
                    # of inventing semantics that the extractor cannot prove.
                    if block_type not in {0, 1}:
                        continue

                    elements.append(element)
                    page_element_ids.append(element.id)
                    reading_order += 1

                rect = page.rect
                pages.append(
                    DocumentPage(
                        number=page_number,
                        width=float(rect.width),
                        height=float(rect.height),
                        rotation=int(page.rotation),
                        element_ids=page_element_ids,
                        provenance=[
                            self._provenance(
                                source="pdf_page",
                                details={
                                    "page_number": page_number,
                                    "coordinate_origin": "top_left",
                                },
                            )
                        ],
                    )
                )

            metadata = {
                "extractor": self.adapter_name,
                "extractor_version": self._version,
                "pdf_metadata": {
                    str(key): value
                    for key, value in (document.metadata or {}).items()
                    if value not in (None, "")
                },
            }

            return DocumentIR(
                document_id=source_sha256,
                page_count=document.page_count,
                pages=pages,
                elements=elements,
                metadata=metadata,
                provenance=[document_provenance],
                warnings=warnings,
            )

    def _element_from_block(
        self,
        block: dict[str, Any],
        *,
        page_number: int,
        block_index: int,
        reading_order: int,
    ) -> DocumentElement | None:
        block_type = int(block.get("type", -1))
        bbox = self._bbox(block.get("bbox"))
        element_id = f"p{page_number}-b{block_index}"

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
                metadata={
                    "block_number": block.get("number", block_index - 1),
                    "block_type": "text",
                },
                provenance=[
                    self._provenance(
                        source="pymupdf_text_block",
                        source_element_ids=[element_id],
                        details={"coordinate_origin": "top_left"},
                    )
                ],
            )

        if block_type == 1:
            image_bytes = block.get("image")
            image_sha256 = (
                hashlib.sha256(bytes(image_bytes)).hexdigest()
                if isinstance(image_bytes, (bytes, bytearray))
                else None
            )
            metadata: dict[str, Any] = {
                "block_number": block.get("number", block_index - 1),
                "block_type": "image",
                "image_width": block.get("width"),
                "image_height": block.get("height"),
                "extension": block.get("ext"),
                "colorspace": block.get("colorspace"),
                "bits_per_component": block.get("bpc"),
                "x_resolution": block.get("xres"),
                "y_resolution": block.get("yres"),
            }
            if image_sha256 is not None:
                metadata["image_sha256"] = image_sha256

            return DocumentElement(
                id=element_id,
                page=page_number,
                kind="image",
                bbox=bbox,
                reading_order=reading_order,
                metadata={key: value for key, value in metadata.items() if value is not None},
                provenance=[
                    self._provenance(
                        source="pymupdf_image_block",
                        source_element_ids=[element_id],
                        details={"coordinate_origin": "top_left"},
                    )
                ],
            )

        return None

    @staticmethod
    def _bbox(raw_bbox: Any) -> BoundingBox:
        if not isinstance(raw_bbox, (tuple, list)) or len(raw_bbox) != 4:
            return BoundingBox(x=0, y=0, width=0, height=0)

        x0, y0, x1, y1 = (float(value) for value in raw_bbox)
        return BoundingBox(
            x=x0,
            y=y0,
            width=max(0.0, x1 - x0),
            height=max(0.0, y1 - y0),
            coordinate_space="pdf_points",
        )

    @staticmethod
    def _text_and_style(block: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        lines = block.get("lines", [])
        text_lines: list[str] = []
        fonts: set[str] = set()
        sizes: set[float] = set()
        colors: set[int] = set()
        flags: set[int] = set()

        if not isinstance(lines, list):
            return "", {}

        for line in lines:
            if not isinstance(line, dict):
                continue
            spans = line.get("spans", [])
            if not isinstance(spans, list):
                continue

            line_parts: list[str] = []
            for span in spans:
                if not isinstance(span, dict):
                    continue
                value = span.get("text")
                if isinstance(value, str):
                    line_parts.append(value)

                font = span.get("font")
                if isinstance(font, str) and font:
                    fonts.add(font)

                size = span.get("size")
                if isinstance(size, (int, float)):
                    sizes.add(round(float(size), 4))

                color = span.get("color")
                if isinstance(color, int):
                    colors.add(color)

                span_flags = span.get("flags")
                if isinstance(span_flags, int):
                    flags.add(span_flags)

            joined = "".join(line_parts).strip()
            if joined:
                text_lines.append(joined)

        style: dict[str, Any] = {}
        if fonts:
            style["fonts"] = sorted(fonts)
        if sizes:
            style["font_sizes"] = sorted(sizes)
        if colors:
            style["colors"] = sorted(colors)
        if flags:
            style["span_flags"] = sorted(flags)

        return "\n".join(text_lines), style

    def _provenance(
        self,
        *,
        source: str,
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

    @staticmethod
    def _detect_version() -> str:
        version = getattr(pymupdf, "VersionBind", None)
        if isinstance(version, str):
            return version
        doc = getattr(pymupdf, "__doc__", "") or ""
        first_line = str(doc).strip().splitlines()
        return first_line[0][:80] if first_line else "unknown"
