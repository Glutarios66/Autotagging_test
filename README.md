# PDF Remediation Research Foundation

A runnable Python 3.12 modular monolith for researching AI-assisted PDF accessibility remediation. It separates stable domain and intermediate-representation models from adapter interfaces, pipeline orchestration, infrastructure, and delivery mechanisms. The included adapters are deterministic mocks: they make the full upload-to-artifact workflow testable, but do not claim production PDF/UA conformance.

## Quick start

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn pdf_remediation.api.main:app --reload
```

Upload and run the default mock recipe synchronously:

```bash
curl -F 'file=@sample.pdf' 'http://localhost:8000/jobs?recipe=remediate'
```

Use the returned `job_id` through `GET /jobs/{id}/artifacts`, then download an artifact from `GET /artifacts/{id}`. Other endpoints are `GET /health`, `GET /recipes`, `GET /jobs/{id}`, and `GET /runs/{id}`.

## Recipes and adapters

YAML recipes in `config/pipelines` define dependency-checked DAGs. `inventory` records file facts, `analyze` builds document and semantic IRs, and `remediate` additionally emits a marker-bearing mock PDF and report. Components are resolved through registries, allowing real extractors, AI analyzers, remediators, and validators to replace mocks without changing application services.

## Persistence and workers

The local default uses SQLite and `./artifacts`. Set `PDFR_ARTIFACT_BACKEND=s3` plus S3 settings for MinIO or compatible storage. SQLAlchemy provides runtime persistence and Alembic owns schema migration. Set `PDFR_RUN_JOBS_INLINE=false` to enqueue runs on Celery.

Run the complete deployment with `docker compose up --build`; this starts the API, Celery worker, PostgreSQL, Redis, and MinIO (console on port 9001).

## Quality checks

```bash
pytest --cov=pdf_remediation
ruff check .
mypy src
```

## Limitations

The mock parser recognizes basic PDF tokens rather than parsing arbitrary PDFs. The mock remediator only inserts an auditable marker. Production work should supply hardened PDF parsing/tagging, model governance, sandboxing, malware scanning, authentication, observability, and an independent PDF/UA validator.
