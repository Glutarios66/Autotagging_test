# Project status

Implemented and wired:

- canonical `DocumentIR`
- canonical `SemanticDocumentIR`
- recipe DAG validation and topological ordering
- adapter registry
- filesystem and S3/MinIO artifact stores
- SQLAlchemy persistence
- Alembic as schema owner
- FastAPI upload/list endpoints
- real PyMuPDF extractor
- mock semantic/remediation/validation/finalization/report adapters
- PyMuPDF baseline recipe
- granular future semantic ports
- unit and API integration tests
- GitHub Actions for Ruff, Mypy and Pytest

Not implemented yet:

- OpenDataLoader adapter
- production AI semantic adapter
- real PDF tag-tree writer / MCID remediation
- veraPDF validator
- HITL corrections
- experiment metrics / cost tracking
