# PDF Remediation Research Foundation

A modular Python 3.12 research platform for PDF accessibility remediation.

The project keeps stable intermediate representations and pipeline orchestration
separate from concrete extraction, AI, remediation, validation and storage
adapters.

## Current real capability

The repository includes a real `PyMuPDFExtractor` that maps PDF text/image blocks
into the canonical `DocumentIR`.

The remaining semantic-analysis, remediation, validation and report adapters are
deterministic research mocks. They are intentionally not presented as PDF/UA
conformance tooling.

## Architecture

```text
PDF upload
  -> recipe
  -> extractor
  -> DocumentIR
  -> semantic analysis
  -> SemanticDocumentIR
  -> remediation candidate
  -> validation
  -> finalization/report
  -> artifacts
```

Adapters are resolved through `(stage_type, adapter_name)` pairs, so a recipe can
switch from `mock` extraction to `pymupdf` without changing the pipeline core.

## Quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

alembic upgrade head
pytest
ruff check .
mypy src

uvicorn pdf_remediation.api.main:app --reload
```

Run a real extraction baseline:

```bash
curl -F 'file=@sample.pdf'   -F 'recipe_name=pymupdf_baseline'   http://localhost:8000/jobs
```

## Recipes

- `mock_remediation`: complete deterministic mock flow.
- `pymupdf_baseline`: real PyMuPDF extraction + mock semantic analysis.

## Next research increments

1. OpenDataLoader adapter emitting the same `DocumentIR`.
2. Real structure-analysis adapter.
3. Reading-order, table, figure and alt-text analyzers.
4. Real tagged-PDF remediation writer.
5. veraPDF validation adapter.
6. Human-in-the-loop corrections and experiment metrics.
