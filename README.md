# PDF Remediation – Tagged-PDF + PDF/UA validation pipeline

The real recipe now uses a before/after validation flow:

```text
source.pdf
  -> veraPDF PRE-FLIGHT
  -> OpenDataLoader extraction + semantic mapping
  -> OpenDataLoader Tagged-PDF generation
  -> CIDSet font normalization
  -> veraPDF POST-FLIGHT
  -> report.json
  -> final_pdf.pdf only if postflight passes
```

## Why CIDSet normalization exists

Some source PDFs contain embedded CID fonts with an inconsistent `/CIDSet`.
PDF/UA-1 checks the correctness of a CIDSet when one is present. The targeted
normalizer removes the inconsistent optional CIDSet entry from CIDFontType0/
CIDFontType2 font descriptors and leaves the embedded font program, ToUnicode,
page content, tags and MCIDs untouched. veraPDF is always run again afterwards.

This is intentionally narrow: it does not claim to repair arbitrary font
embedding problems.

## Install

Requirements:

- Python 3.12+
- Java 11+ for OpenDataLoader
- veraPDF CLI

macOS:

```bash
brew install python@3.12
brew install --cask temurin
brew install verapdf

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,opendataloader]'
alembic upgrade head
```

Start:

```bash
python -m uvicorn pdf_remediation.api.main:app --reload
```

Run a real remediation:

```bash
curl -F 'file=@sample.pdf'   -F 'recipe_name=accessibility_full'   http://127.0.0.1:8000/jobs
```

## Expected artifacts

Always:

```text
source_pdf.pdf
preflight_validation.json
document_ir.json
semantic_ir.json
candidate_pdf.pdf
normalized_pdf.pdf
normalization_report.json
validation.json
report.json
```

Only when postflight veraPDF passes:

```text
final_pdf.pdf
```

`report.json` separates fixed, remaining and newly introduced rule codes.
