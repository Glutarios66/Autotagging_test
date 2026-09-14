# Project status – v0.3

## Implemented

- PyMuPDF extractor -> canonical DocumentIR
- OpenDataLoader extractor -> canonical DocumentIR
- OpenDataLoader semantic mapping
- optional OpenAI structured-output semantic adapter
- OpenDataLoader real Tagged-PDF writer
- veraPDF PDF/UA-1 validator adapter
- real `accessibility_full` recipe
- downloadable `.pdf` / `.json` artifacts
- explicit file extensions in filesystem artifacts
- accessibility report
- HITL review correction API foundation
- experiment/metric API foundation
- tests for DAG, registry, IR, PyMuPDF, semantic mapping, artifact extensions,
  veraPDF-unavailable behavior and API baseline
- GitHub Actions

## Output of the real recipe

- source_pdf.pdf
- document_ir.json
- semantic_ir.json
- candidate_pdf.pdf
- validation.json
- final_pdf.pdf
- report.json

## Still intentionally not claimed

A Tagged PDF is not automatically equivalent to a PDF/UA-conformant PDF.
`validation.json`/`report.json` are the source of truth for machine validation.

Human checkpoints still need review.
