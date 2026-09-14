# Architecture

## Modular monolith

The system deploys as one codebase while preserving inward-facing boundaries:

- `domain` owns job, run, batch, and artifact lifecycle records.
- `ir` owns versioned physical-layout and semantic document representations.
- `ports` declares adapter, repository, and object-store contracts.
- `pipeline` loads YAML recipes, validates DAGs, resolves components, and executes steps.
- `application` coordinates submission, lifecycle transitions, and artifact persistence.
- `adapters` contains deterministic research mocks; production integrations belong beside them.
- `infrastructure` implements SQLAlchemy and filesystem/S3-compatible persistence.
- `api` and `workers` are inbound delivery adapters sharing the same bootstrap container.

Dependencies point toward domain contracts. Framework-specific code does not enter the domain or IR layers.

## Execution and artifacts

An upload is persisted before its job and run records are created. A run loads immutable source bytes, executes recipe steps in topological order, then stores each meaningful output under a job/run namespace with SHA-256, content type, and size metadata. Status and error transitions are persisted even when a component fails. The API can run inline for development or dispatch the run ID to Celery.

## Extension seams

Adapters are structural Python protocols. A production implementation can replace extraction, semantic inference, remediation, validation, repositories, or artifact stores independently. Recipe dependencies refer to component names rather than concrete classes. IR schema versions make future migrations explicit.

## Security and research boundary

Uploaded filenames are reduced to basenames and filesystem keys cannot escape their root. Upload size and PDF header are checked. These controls are foundational rather than exhaustive: untrusted production PDFs require isolation, parser resource limits, malware scanning, authorization, retention policy, encryption, and redaction. Mock validation results must never be represented as real PDF/UA certification.
