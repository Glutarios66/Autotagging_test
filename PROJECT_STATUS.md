# Project status – v0.4

Implemented:
- veraPDF preflight on the original PDF
- real OpenDataLoader tagging
- targeted CIDSet font normalization using pikepdf/qpdf
- veraPDF postflight on the normalized Tagged PDF
- before/after validation comparison
- final PDF emitted only after successful postflight validation
- normalization report with affected fonts/pages
- existing PyMuPDF/OpenDataLoader/OpenAI/HITL/experiment foundations retained

The CIDSet repair is intentionally conservative. It removes inconsistent
optional CIDSet entries from embedded CID font descriptors; it does not
re-encode text or rebuild font programs. Any other remaining font or PDF/UA
issue stays visible in validation.json/report.json.
