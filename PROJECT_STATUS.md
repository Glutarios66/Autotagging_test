# Project status – v0.4

Implemented:
- veraPDF preflight on source PDF
- OpenDataLoader real tagged-PDF generation
- targeted CIDSet cleanup
- exact-match TrueType font embedding via FontFile2
- OpenType OS/2 fsType embedding-rights guard
- macOS font discovery + PDFR_FONT_DIRS override
- PDF/UA-1 XMP identification (`pdfuaid:part = 1`)
- veraPDF postflight
- before/after report
- final PDF only on successful postflight

The font repair intentionally supports missing embedded TrueType fonts with an
existing FontDescriptor and an exact locally available font match. It does not
substitute fonts or attempt generic Type1/CFF repair.

- `/Tabs /S` repair for pages with annotations
