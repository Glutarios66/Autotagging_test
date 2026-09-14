# macOS setup

## 1. Python 3.12

```bash
brew install python@3.12
python3.12 --version
```

## 2. Java for OpenDataLoader

OpenDataLoader requires Java 11+.

```bash
brew install --cask temurin
java -version
```

## 3. veraPDF

```bash
brew install verapdf
verapdf --version
```

## 4. Project

```bash
cd /path/to/Autotagging_test_complete

rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e '.[dev,opendataloader]'

alembic upgrade head
pytest
ruff check .
mypy src
```

## 5. Start API

```bash
python -m uvicorn pdf_remediation.api.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 6. Real tagging test

```bash
curl -F 'file=@sample.pdf'   -F 'recipe_name=accessibility_full'   http://127.0.0.1:8000/jobs
```

The successful real recipe produces:

```text
source_pdf.pdf
document_ir.json
semantic_ir.json
candidate_pdf.pdf
validation.json
final_pdf.pdf
report.json
```

Use the `/jobs/{job_id}/artifacts` endpoint to obtain artifact IDs, then download
with `/jobs/{job_id}/artifacts/{artifact_id}/download`.
