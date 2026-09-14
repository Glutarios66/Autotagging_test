from __future__ import annotations

import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

PDFUA_PART = 1

# macOS locations plus user-configurable locations via PDFR_FONT_DIRS.
DEFAULT_FONT_DIRS = (
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
)

SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")


class PDFUAConformanceNormalizer:
    """Narrow PDF/UA-1 normalization before the final veraPDF pass.

    Repairs:
    1. removes inconsistent optional /CIDSet entries from CID font descriptors;
    2. embeds missing *matching* TrueType fonts as /FontFile2 when a local font
       with the same PostScript name exists and its OS/2 fsType permits embedding;
    3. writes the PDF/UA-1 XMP identification field pdfuaid:part=1.

    It does not substitute one font for another, rewrite text, alter ToUnicode,
    rebuild tags, or claim success by itself. veraPDF remains the authority for
    the machine-verifiable postflight result.
    """

    adapter_name = "pdfua"

    def __init__(self, font_dirs: Iterable[Path] | None = None) -> None:
        self.font_dirs = tuple(font_dirs or self._default_font_dirs())

    def normalize(self, content: bytes) -> tuple[bytes, dict[str, Any]]:
        if not content.startswith(b"%PDF-"):
            raise ValueError("input is not a PDF")

        try:
            import pikepdf
        except ImportError as exc:
            raise RuntimeError(
                "PDF/UA normalization requires pikepdf. "
                "Run: python -m pip install -e '.[dev,opendataloader]'"
            ) from exc

        try:
            from fontTools.ttLib import TTFont
        except ImportError as exc:
            raise RuntimeError(
                "Font embedding requires fontTools. "
                "Run: python -m pip install -e '.[dev,opendataloader]'"
            ) from exc

        font_index = self._build_font_index(TTFont)
        source = BytesIO(content)
        output = BytesIO()

        cidset_repairs: list[dict[str, Any]] = []
        embedded_fonts: list[dict[str, Any]] = []
        unresolved_fonts: list[dict[str, Any]] = []
        visited: set[tuple[int, int] | int] = set()

        with pikepdf.Pdf.open(source) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                resources = page.obj.get("/Resources")
                if isinstance(resources, pikepdf.Dictionary):
                    self._walk_resources(
                        pdf=pdf,
                        pikepdf=pikepdf,
                        resources=resources,
                        page_number=page_number,
                        font_index=font_index,
                        cidset_repairs=cidset_repairs,
                        embedded_fonts=embedded_fonts,
                        unresolved_fonts=unresolved_fonts,
                        visited=visited,
                    )

            # pikepdf knows the standard PDF/UA identification schema.
            with pdf.open_metadata(set_pikepdf_as_editor=False) as metadata:
                metadata["pdfuaid:part"] = PDFUA_PART

            pdf.save(output)

        normalized = output.getvalue()
        if not normalized.startswith(b"%PDF-"):
            raise RuntimeError("PDF/UA normalization did not produce a PDF")

        report: dict[str, Any] = {
            "normalizer": self.adapter_name,
            "changed": bool(cidset_repairs or embedded_fonts) or True,
            "pdfua_identification": {
                "pdfuaid:part": PDFUA_PART,
                "written": True,
            },
            "cidset": {
                "removed_entries": len(cidset_repairs),
                "repairs": cidset_repairs,
            },
            "font_embedding": {
                "embedded_count": len(embedded_fonts),
                "embedded": embedded_fonts,
                "unresolved_count": len(unresolved_fonts),
                "unresolved": unresolved_fonts,
                "search_directories": [str(path) for path in self.font_dirs],
            },
        }
        return normalized, report

    @staticmethod
    def _default_font_dirs() -> tuple[Path, ...]:
        configured = os.environ.get("PDFR_FONT_DIRS", "")
        extras = tuple(
            Path(item).expanduser()
            for item in configured.split(os.pathsep)
            if item.strip()
        )
        seen: set[str] = set()
        result: list[Path] = []
        for path in (*extras, *DEFAULT_FONT_DIRS):
            key = str(path)
            if key not in seen:
                seen.add(key)
                result.append(path)
        return tuple(result)

    def _build_font_index(self, TTFont: Any) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for directory in self.font_dirs:
            if not directory.exists():
                continue

            try:
                candidates = list(directory.rglob("*.ttf"))
            except OSError:
                continue

            for path in candidates:
                try:
                    with TTFont(path, lazy=True, recalcTimestamp=False) as font:
                        if "glyf" not in font:
                            continue
                        ps_name = self._name_record(font, 6)
                        if not ps_name:
                            continue
                        fs_type = int(getattr(font.get("OS/2"), "fsType", 0) or 0)
                        embeddable, reason = self._embedding_allowed(fs_type)
                        index.setdefault(
                            self._font_key(ps_name),
                            {
                                "path": path,
                                "postscript_name": ps_name,
                                "fs_type": fs_type,
                                "embeddable": embeddable,
                                "embedding_reason": reason,
                            },
                        )
                except Exception:
                    # Broken/unreadable system fonts must not fail PDF remediation.
                    continue
        return index

    @staticmethod
    def _name_record(font: Any, name_id: int) -> str | None:
        name_table = font.get("name")
        if name_table is None:
            return None
        # Prefer Windows/English when available; then accept first decodable value.
        records = list(name_table.names)
        records.sort(
            key=lambda rec: (
                rec.nameID != name_id,
                rec.platformID != 3,
                getattr(rec, "langID", 0) != 0x409,
            )
        )
        for record in records:
            if record.nameID != name_id:
                continue
            try:
                value = record.toUnicode().strip()
            except Exception:
                continue
            if value:
                return value
        return None

    @staticmethod
    def _embedding_allowed(fs_type: int) -> tuple[bool, str]:
        # OpenType OS/2 fsType bit 1 (0x0002) means restricted license embedding.
        # We embed the complete font, so the "no subsetting" bit is respected.
        if fs_type & 0x0002:
            return False, "restricted_license_embedding"
        if fs_type & 0x0200:
            return False, "bitmap_embedding_only"
        return True, "allowed"

    @classmethod
    def _font_key(cls, name: str) -> str:
        clean = name.lstrip("/")
        clean = SUBSET_PREFIX.sub("", clean)
        clean = clean.replace(" ", "")
        return clean.casefold()

    def _walk_resources(
        self,
        *,
        pdf: Any,
        pikepdf: Any,
        resources: Any,
        page_number: int,
        font_index: dict[str, dict[str, Any]],
        cidset_repairs: list[dict[str, Any]],
        embedded_fonts: list[dict[str, Any]],
        unresolved_fonts: list[dict[str, Any]],
        visited: set[tuple[int, int] | int],
    ) -> None:
        identity = self._identity(resources)
        if identity in visited:
            return
        visited.add(identity)

        fonts = resources.get("/Font")
        if isinstance(fonts, pikepdf.Dictionary):
            for resource_name, font in fonts.items():
                self._repair_font(
                    pdf=pdf,
                    pikepdf=pikepdf,
                    font=font,
                    page_number=page_number,
                    resource_name=str(resource_name),
                    font_index=font_index,
                    cidset_repairs=cidset_repairs,
                    embedded_fonts=embedded_fonts,
                    unresolved_fonts=unresolved_fonts,
                )

        xobjects = resources.get("/XObject")
        if isinstance(xobjects, pikepdf.Dictionary):
            for xobject in xobjects.values():
                if not isinstance(xobject, pikepdf.Dictionary):
                    continue
                nested = xobject.get("/Resources")
                if isinstance(nested, pikepdf.Dictionary):
                    self._walk_resources(
                        pdf=pdf,
                        pikepdf=pikepdf,
                        resources=nested,
                        page_number=page_number,
                        font_index=font_index,
                        cidset_repairs=cidset_repairs,
                        embedded_fonts=embedded_fonts,
                        unresolved_fonts=unresolved_fonts,
                        visited=visited,
                    )

    def _repair_font(
        self,
        *,
        pdf: Any,
        pikepdf: Any,
        font: object,
        page_number: int,
        resource_name: str,
        font_index: dict[str, dict[str, Any]],
        cidset_repairs: list[dict[str, Any]],
        embedded_fonts: list[dict[str, Any]],
        unresolved_fonts: list[dict[str, Any]],
    ) -> None:
        if not isinstance(font, pikepdf.Dictionary):
            return

        subtype = font.get("/Subtype")

        if subtype == pikepdf.Name("/Type0"):
            descendants = font.get("/DescendantFonts")
            if isinstance(descendants, pikepdf.Array):
                for descendant in descendants:
                    if not isinstance(descendant, pikepdf.Dictionary):
                        continue
                    descriptor = descendant.get("/FontDescriptor")
                    descendant_subtype = descendant.get("/Subtype")
                    if (
                        descendant_subtype
                        in {
                            pikepdf.Name("/CIDFontType0"),
                            pikepdf.Name("/CIDFontType2"),
                        }
                        and isinstance(descriptor, pikepdf.Dictionary)
                        and "/CIDSet" in descriptor
                    ):
                        name = descriptor.get("/FontName") or descendant.get("/BaseFont")
                        del descriptor["/CIDSet"]
                        cidset_repairs.append(
                            {
                                "page": page_number,
                                "resource": resource_name,
                                "font_name": str(name or "unknown"),
                                "cid_font_subtype": str(descendant_subtype),
                            }
                        )
            return

        if subtype != pikepdf.Name("/TrueType"):
            return

        descriptor = font.get("/FontDescriptor")
        base_font = font.get("/BaseFont")
        if not isinstance(descriptor, pikepdf.Dictionary):
            unresolved_fonts.append(
                {
                    "page": page_number,
                    "resource": resource_name,
                    "font_name": str(base_font or "unknown"),
                    "reason": "missing_font_descriptor",
                }
            )
            return

        if any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")):
            return

        font_name_obj = descriptor.get("/FontName") or base_font
        font_name = str(font_name_obj or "").lstrip("/")
        if not font_name:
            unresolved_fonts.append(
                {
                    "page": page_number,
                    "resource": resource_name,
                    "font_name": "unknown",
                    "reason": "missing_font_name",
                }
            )
            return

        match = font_index.get(self._font_key(font_name))
        if match is None:
            unresolved_fonts.append(
                {
                    "page": page_number,
                    "resource": resource_name,
                    "font_name": font_name,
                    "reason": "matching_local_truetype_font_not_found",
                }
            )
            return

        if not match["embeddable"]:
            unresolved_fonts.append(
                {
                    "page": page_number,
                    "resource": resource_name,
                    "font_name": font_name,
                    "reason": match["embedding_reason"],
                    "font_path": str(match["path"]),
                    "fs_type": match["fs_type"],
                }
            )
            return

        font_bytes = Path(match["path"]).read_bytes()
        stream = pikepdf.Stream(pdf, font_bytes)
        stream["/Length1"] = len(font_bytes)
        descriptor["/FontFile2"] = stream

        embedded_fonts.append(
            {
                "page": page_number,
                "resource": resource_name,
                "font_name": font_name,
                "matched_postscript_name": match["postscript_name"],
                "font_path": str(match["path"]),
                "bytes": len(font_bytes),
                "fs_type": match["fs_type"],
            }
        )


    @staticmethod
    def _identity(obj: object) -> tuple[int, int] | int:
        objgen = getattr(obj, "objgen", None)
        if isinstance(objgen, tuple) and objgen != (0, 0):
            return objgen
        return id(obj)
