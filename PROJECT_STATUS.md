# Project status

The repository now ships **no mock adapters or mock pipelines**.

## Active recipes
- `accessibility_full`: production candidate using OpenDataLoader + PDF/UA normalizer + veraPDF.
- `accessibility_ai`: experimental PyMuPDF/OpenAI semantics flow, using the same PDF/UA normalizer + veraPDF.

## Removed
- mock adapter module and mock registrations
- mock remediation recipe
- mock-backed PyMuPDF baseline recipe
- standalone legacy CIDSet adapter (subsumed by `PDFUAConformanceNormalizer`)

See `docs/NEXT_STEPS.md` for the development roadmap.
