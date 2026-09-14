# PDF Remediation – PDF/UA normalization pipeline v0.4

The default `accessibility_full` recipe now performs:

```text
source.pdf
  -> veraPDF PRE-FLIGHT
  -> OpenDataLoader extraction / semantic mapping
  -> OpenDataLoader Tagged-PDF generation
  -> PDF/UA normalizer
       - remove inconsistent optional CIDSet entries
       - embed missing matching TrueType fonts when legally embeddable
       - write XMP pdfuaid:part = 1
       - set /Tabs /S on pages containing annotations
  -> veraPDF POST-FLIGHT
  -> report.json
  -> final_pdf.pdf only if postflight valid == true
```

## Font repair policy

The normalizer does **not** silently replace fonts. For an unembedded `/TrueType`
font such as `ArialMT`, it searches local macOS font directories for a `.ttf`
whose PostScript name exactly matches the PDF font name (subset prefixes are
ignored). It then checks the OpenType `OS/2.fsType` flags. Restricted-license or
bitmap-only fonts are not embedded.

Default macOS search directories:

```text
/System/Library/Fonts
/System/Library/Fonts/Supplemental
/Library/Fonts
~/Library/Fonts
```

Additional directories can be supplied before starting the API:

```bash
export PDFR_FONT_DIRS="/path/to/company/fonts:/another/font/dir"
```

If no safe exact match exists, the run remains invalid and
`normalization_report.json` explains why.

## PDF/UA metadata

The normalizer writes the PDF/UA-1 identification property:

```text
pdfuaid:part = 1
```

This is only a conformance *claim*. The project still requires the following
veraPDF postflight to pass before `final_pdf.pdf` is emitted.

## Install

```bash
brew install python@3.12
brew install --cask temurin
brew install verapdf

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,opendataloader]'

alembic upgrade head
pytest
ruff check .
mypy src
```

Start:

```bash
python -m uvicorn pdf_remediation.api.main:app --reload
```

Submit:

```bash
curl -F 'file=@sample.pdf'   -F 'recipe_name=accessibility_full'   http://127.0.0.1:8000/jobs
```

The authoritative machine result is `validation.json`.

```json
{
  "valid": true
}
```

Only then is `final_pdf.pdf` generated.
