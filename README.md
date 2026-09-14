# PDF Remediation – real Tagged-PDF pipeline

This project now contains two levels:

1. a lightweight PyMuPDF research baseline;
2. a real local accessibility pipeline using OpenDataLoader auto-tagging and veraPDF validation.

## What `accessibility_full` does

```text
source.pdf
  -> OpenDataLoader JSON extraction
  -> canonical DocumentIR
  -> semantic role mapping
  -> OpenDataLoader auto-tagging
  -> candidate_pdf.pdf (real Tagged PDF)
  -> veraPDF PDF/UA-1 machine validation
  -> final_pdf.pdf
  -> report.json
```

OpenDataLoader's Tagged-PDF output is a real tagged PDF. It is **not automatically
claimed to be PDF/UA compliant**. The separate veraPDF artifact records whether
the machine-verifiable PDF/UA checks pass.

## Requirements

- Python 3.12+
- Java 11+ for OpenDataLoader
- veraPDF CLI for PDF/UA validation

Check Java:

```bash
java -version
```

On macOS with Homebrew:

```bash
brew install --cask temurin
```

Install project with the real OpenDataLoader adapter:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,opendataloader]'
```

Initialize the database:

```bash
alembic upgrade head
```

Start:

```bash
python -m uvicorn pdf_remediation.api.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

## Generate a real tagged PDF

```bash
curl -F 'file=@sample.pdf'   -F 'recipe_name=accessibility_full'   http://127.0.0.1:8000/jobs
```

Then query:

```bash
curl http://127.0.0.1:8000/jobs/<JOB_ID>/artifacts
```

Expected artifacts:

```text
source_pdf.pdf
document_ir.json
semantic_ir.json
candidate_pdf.pdf
validation.json
final_pdf.pdf
report.json
```

`candidate_pdf.pdf` and `final_pdf.pdf` are the real auto-tagged PDF output.

## Optional AI structure recipe

Set:

```bash
export PDFR_OPENAI_API_KEY='...'
```

Then `accessibility_ai` becomes available through the registered
`semantic_analysis/openai` adapter. It uses the Responses API with a strict
JSON-schema structure classification. The OpenDataLoader writer remains
responsible for writing the actual PDF tags.

## HITL / experiments

The API also exposes review-correction and experiment metric endpoints. These are
an application-layer foundation. For multi-process production deployment, move
this state from the current in-memory service to the SQLAlchemy repository.

## Important limitation

veraPDF performs machine-verifiable conformance checks. Human accessibility
review remains necessary for semantic correctness such as meaningful alt text,
reading order quality and heading intent.
