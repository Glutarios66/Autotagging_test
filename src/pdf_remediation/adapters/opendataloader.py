from __future__ import annotations

import hashlib
import importlib
import json
import tempfile
from pathlib import Path
from typing import Any

import pymupdf

from pdf_remediation.ir import (
    BoundingBox,
    DocumentElement,
    DocumentIR,
    DocumentPage,
    Provenance,
    SemanticDocumentIR,
    SemanticNode,
)


def _load_opendataloader() -> Any:
    try:
        return importlib.import_module("opendataloader_pdf")
    except ImportError as exc:
        raise RuntimeError(
            "OpenDataLoader is not installed. "
            "Install it with: pip install -e '.[opendataloader]'"
        ) from exc


def _run_conversion(content: bytes, formats: str) -> Path:
    opendataloader_pdf = _load_opendataloader()
    work = Path(tempfile.mkdtemp(prefix="pdf-remediation-odl-"))
    input_pdf = work / "source.pdf"
    output_dir = work / "output"
    output_dir.mkdir()
    input_pdf.write_bytes(content)

    opendataloader_pdf.convert(
        input_path=[str(input_pdf)],
        output_dir=str(output_dir),
        format=formats,
        quiet=True,
    )
    return output_dir


def _first_file(root: Path, suffixes: tuple[str, ...]) -> Path:
    matches = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    )
    if not matches:
        raise RuntimeError(f"OpenDataLoader did not produce expected output: {suffixes}")
    return matches[0]


def _bbox(raw: Any) -> BoundingBox:
    if not isinstance(raw, list) or len(raw) != 4:
        return BoundingBox(x=0, y=0, width=0, height=0)
    left, bottom, right, top = (float(v) for v in raw)
    return BoundingBox(
        x=left,
        y=bottom,
        width=max(0.0, right - left),
        height=max(0.0, top - bottom),
        coordinate_space="pdf_points",
    )


def _flatten(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    stack = list(reversed(nodes))
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        result.append(node)
        children: list[dict[str, Any]] = []
        for key in ("kids", "list items"):
            raw = node.get(key)
            if isinstance(raw, list):
                children.extend(x for x in raw if isinstance(x, dict))
        rows = node.get("rows")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    cells = row.get("cells")
                    if isinstance(cells, list):
                        for cell in cells:
                            if isinstance(cell, dict):
                                children.append(cell)
        stack.extend(reversed(children))
    return result


class OpenDataLoaderExtractor:
    adapter_name = "opendataloader"

    def extract(self, content: bytes) -> DocumentIR:
        if not content.startswith(b"%PDF-"):
            raise ValueError("input is not a PDF")

        out = _run_conversion(content, "json")
        json_path = _first_file(out, (".json",))
        data = json.loads(json_path.read_text(encoding="utf-8"))

        page_count = int(data.get("number of pages") or 0)
        if page_count < 1:
            with pymupdf.open(stream=content, filetype="pdf") as pdf:
                page_count = pdf.page_count

        page_sizes: dict[int, tuple[float, float, int]] = {}
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            for index in range(pdf.page_count):
                page = pdf[index]
                page_sizes[index + 1] = (
                    float(page.rect.width),
                    float(page.rect.height),
                    int(page.rotation),
                )

        elements: list[DocumentElement] = []
        by_page: dict[int, list[str]] = {page: [] for page in range(1, page_count + 1)}
        reading_order = 0

        kids = data.get("kids")
        flat = _flatten(kids if isinstance(kids, list) else [])
        for index, node in enumerate(flat, start=1):
            page_number = int(node.get("page number") or 1)
            node_type = str(node.get("type") or "unknown")
            content_text = node.get("content")
            text = content_text if isinstance(content_text, str) else None

            if node_type in {"image", "figure"}:
                kind = "image"
            elif node_type == "table":
                kind = "table"
            elif text:
                kind = "text"
            else:
                kind = "unknown"

            element_id = f"odl-{index}"
            metadata: dict[str, Any] = {
                "odl_type": node_type,
                "odl_id": node.get("id"),
            }
            for field in (
                "heading level",
                "level",
                "number of rows",
                "number of columns",
                "row number",
                "column number",
                "row span",
                "column span",
                "linked content id",
            ):
                if field in node:
                    metadata[field.replace(" ", "_")] = node[field]

            style: dict[str, Any] = {}
            for source, target in (
                ("font", "font"),
                ("font size", "font_size"),
                ("text color", "text_color"),
            ):
                if source in node:
                    style[target] = node[source]

            element = DocumentElement(
                id=element_id,
                page=page_number,
                kind=kind,
                bbox=_bbox(node.get("bounding box")),
                text=text,
                reading_order=reading_order,
                style=style,
                metadata=metadata,
                provenance=[
                    Provenance(
                        source="opendataloader_json",
                        adapter=self.adapter_name,
                        confidence=1.0,
                        details={"coordinate_origin": "bottom_left"},
                    )
                ],
            )
            elements.append(element)
            by_page.setdefault(page_number, []).append(element_id)
            reading_order += 1

        pages = []
        for page_number in range(1, page_count + 1):
            width, height, rotation = page_sizes.get(page_number, (0.0, 0.0, 0))
            pages.append(
                DocumentPage(
                    number=page_number,
                    width=width,
                    height=height,
                    rotation=rotation,
                    element_ids=by_page.get(page_number, []),
                    provenance=[
                        Provenance(
                            source="opendataloader_json",
                            adapter=self.adapter_name,
                            confidence=1.0,
                        )
                    ],
                )
            )

        digest = hashlib.sha256(content).hexdigest()
        return DocumentIR(
            document_id=digest,
            page_count=page_count,
            pages=pages,
            elements=elements,
            metadata={
                "extractor": self.adapter_name,
                "title": data.get("title"),
                "author": data.get("author"),
                "file_name": data.get("file name"),
            },
            provenance=[
                Provenance(
                    source="opendataloader_json",
                    adapter=self.adapter_name,
                    confidence=1.0,
                )
            ],
        )


class OpenDataLoaderSemanticAnalyzer:
    adapter_name = "opendataloader"

    _roles = {
        "heading": "H",
        "paragraph": "P",
        "caption": "Caption",
        "list": "L",
        "list item": "LI",
        "table": "Table",
        "table row": "TR",
        "table cell": "TD",
        "image": "Figure",
        "figure": "Figure",
        "header": "Artifact",
        "footer": "Artifact",
    }

    def analyze(self, document: DocumentIR) -> SemanticDocumentIR:
        nodes: list[SemanticNode] = []
        for element in sorted(
            document.elements,
            key=lambda item: item.reading_order if item.reading_order is not None else 10**9,
        ):
            odl_type = str(element.metadata.get("odl_type") or "")
            role = self._roles.get(odl_type, "P" if element.kind == "text" else "Span")
            heading_level = element.metadata.get("heading_level")
            if role == "H" and isinstance(heading_level, int):
                role = f"H{max(1, min(6, heading_level))}"
            nodes.append(
                SemanticNode(
                    id=f"semantic-{element.id}",
                    role=role,
                    source_element_ids=[element.id],
                    text=element.text,
                    confidence=1.0,
                    metadata={"source_type": odl_type},
                )
            )
        return SemanticDocumentIR(
            document_id=document.document_id,
            nodes=nodes,
            reading_order=[node.id for node in nodes],
            metadata={"analyzer": self.adapter_name},
            provenance=[
                Provenance(
                    source="opendataloader_semantics",
                    adapter=self.adapter_name,
                    confidence=1.0,
                )
            ],
        )


class OpenDataLoaderTagger:
    adapter_name = "opendataloader"

    def remediate(self, source: bytes, semantics: SemanticDocumentIR) -> bytes:
        if not source.startswith(b"%PDF-"):
            raise ValueError("input is not a PDF")
        out = _run_conversion(source, "tagged-pdf")
        pdf_path = _first_file(out, (".pdf",))
        tagged = pdf_path.read_bytes()
        if not tagged.startswith(b"%PDF-"):
            raise RuntimeError("OpenDataLoader returned an invalid tagged PDF")
        return tagged
