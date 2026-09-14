# Next development steps

## Active pipelines

### `accessibility_full` — production candidate
1. veraPDF preflight
2. OpenDataLoader extraction
3. OpenDataLoader semantic analysis
4. OpenDataLoader tagged-PDF generation
5. PDF/UA normalization
   - CIDSet cleanup
   - exact-match TrueType embedding
   - `pdfuaid:part = 1`
   - `/Tabs /S` for pages with annotations
6. veraPDF postflight
7. accessibility report
8. final PDF only if postflight is valid

### `accessibility_ai` — experimental
1. veraPDF preflight
2. PyMuPDF extraction
3. OpenAI semantic analysis
4. OpenDataLoader tagged-PDF generation
5. same PDF/UA normalizer as production
6. veraPDF postflight
7. report
8. conditional finalization

## Development roadmap

### P0 — correctness and observability
- ✅ Persist partial artifacts when a pipeline fails.
- ✅ Persist the failing step id and exception type in the run error.
- ✅ Add a recipe readiness endpoint so `accessibility_ai` is reported unavailable
  when `OPENAI_API_KEY` is not configured.
- Add an end-to-end fixture corpus and assert veraPDF postflight results.

### P1 — PDF/UA repair coverage
- Annotation semantic checks beyond `/Tabs /S`.
- Link annotations: structure association and accessible link content.
- Figure/Formula alternate text workflow.
- Table header/scope repair.
- Heading hierarchy checks.
- Language metadata (`/Lang`) normalization.
- Form field names/tooltips and widget annotation checks.

### P2 — production hardening
- Persist review/HITL decisions in the repository.
- Apply approved corrections back into the semantic/tagging stage.
- Add deterministic artifact hashes and provenance to reports.
- Add retry/timeout/resource limits for OpenDataLoader and veraPDF.
- Add containerized integration tests with Java + veraPDF + OpenDataLoader.
