from __future__ import annotations

from io import BytesIO
from typing import Any


class CIDSetFontNormalizer:
    """Targeted repair for inconsistent optional CIDSet entries."""

    adapter_name = "cidset"

    def normalize(self, content: bytes) -> tuple[bytes, dict[str, Any]]:
        if not content.startswith(b"%PDF-"):
            raise ValueError("input is not a PDF")

        try:
            import pikepdf
        except ImportError as exc:
            raise RuntimeError(
                "CIDSet normalization requires pikepdf. "
                "Reinstall the project with: python -m pip install -e '.[dev,opendataloader]'"
            ) from exc

        source = BytesIO(content)
        output = BytesIO()
        repaired: list[dict[str, Any]] = []
        visited: set[tuple[int, int] | int] = set()

        with pikepdf.Pdf.open(source) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                resources = page.obj.get("/Resources")
                if isinstance(resources, pikepdf.Dictionary):
                    self._walk_resources(
                        pikepdf,
                        resources,
                        page_number=page_number,
                        repaired=repaired,
                        visited=visited,
                    )

            pdf.save(output)

        normalized = output.getvalue()
        if not normalized.startswith(b"%PDF-"):
            raise RuntimeError("font normalization did not produce a PDF")

        return normalized, {
            "normalizer": self.adapter_name,
            "changed": bool(repaired),
            "removed_cidset_entries": len(repaired),
            "repairs": repaired,
            "strategy": "remove_inconsistent_optional_cidset",
        }

    def _walk_resources(
        self,
        pikepdf: Any,
        resources: Any,
        *,
        page_number: int,
        repaired: list[dict[str, Any]],
        visited: set[tuple[int, int] | int],
    ) -> None:
        key = self._identity(resources)
        if key in visited:
            return
        visited.add(key)

        fonts = resources.get("/Font")
        if isinstance(fonts, pikepdf.Dictionary):
            for resource_name, font in fonts.items():
                self._repair_font(
                    pikepdf,
                    font,
                    page_number=page_number,
                    resource_name=str(resource_name),
                    repaired=repaired,
                )

        xobjects = resources.get("/XObject")
        if isinstance(xobjects, pikepdf.Dictionary):
            for xobject in xobjects.values():
                if not isinstance(xobject, pikepdf.Dictionary):
                    continue
                nested = xobject.get("/Resources")
                if isinstance(nested, pikepdf.Dictionary):
                    self._walk_resources(
                        pikepdf,
                        nested,
                        page_number=page_number,
                        repaired=repaired,
                        visited=visited,
                    )

    def _repair_font(
        self,
        pikepdf: Any,
        font: object,
        *,
        page_number: int,
        resource_name: str,
        repaired: list[dict[str, Any]],
    ) -> None:
        if not isinstance(font, pikepdf.Dictionary):
            return

        if font.get("/Subtype") != pikepdf.Name("/Type0"):
            return

        descendants = font.get("/DescendantFonts")
        if not isinstance(descendants, pikepdf.Array):
            return

        for descendant in descendants:
            if not isinstance(descendant, pikepdf.Dictionary):
                continue

            subtype = descendant.get("/Subtype")
            if subtype not in {
                pikepdf.Name("/CIDFontType0"),
                pikepdf.Name("/CIDFontType2"),
            }:
                continue

            descriptor = descendant.get("/FontDescriptor")
            if not isinstance(descriptor, pikepdf.Dictionary):
                continue
            if "/CIDSet" not in descriptor:
                continue

            font_name = descriptor.get("/FontName")
            descendant_name = descendant.get("/BaseFont")
            del descriptor["/CIDSet"]
            repaired.append(
                {
                    "page": page_number,
                    "resource": resource_name,
                    "font_name": str(font_name or descendant_name or "unknown"),
                    "cid_font_subtype": str(subtype),
                }
            )

    @staticmethod
    def _identity(obj: object) -> tuple[int, int] | int:
        objgen = getattr(obj, "objgen", None)
        if isinstance(objgen, tuple) and objgen != (0, 0):
            return objgen
        return id(obj)
