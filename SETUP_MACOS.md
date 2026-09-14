# macOS setup – PDF/UA v0.4

```bash
brew install python@3.12
brew install --cask temurin
brew install verapdf

cd /Users/talhayilmaz/Documents/Accessibility_test

rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e '.[dev,opendataloader]'

alembic upgrade head
pytest
ruff check .
mypy src

python -m uvicorn pdf_remediation.api.main:app --reload
```

For company/custom fonts:

```bash
export PDFR_FONT_DIRS="/path/to/fonts"
python -m uvicorn pdf_remediation.api.main:app --reload
```

Run:

```bash
curl -F 'file=@sample.pdf'   -F 'recipe_name=accessibility_full'   http://127.0.0.1:8000/jobs
```

Inspect:

```text
preflight_validation.json
candidate_pdf.pdf
normalized_pdf.pdf
normalization_report.json
validation.json
report.json
```

The final verdict is `validation.json -> valid`.
`final_pdf.pdf` exists only when that value is `true`.
