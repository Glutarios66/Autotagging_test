from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pdf_remediation.domain import Artifact, Job, Run
from pdf_remediation.ir import DocumentIR, SemanticDocumentIR, ValidationResult
from pdf_remediation.pipeline import PipelineContext, PipelineExecutor, RecipeRegistry
from pdf_remediation.ports import ArtifactStore, Repository


class RemediationService:
    def __init__(
        self,
        repository: Repository,
        store: ArtifactStore,
        recipes: RecipeRegistry,
        executor: PipelineExecutor,
    ) -> None:
        self.repository = repository
        self.store = store
        self.recipes = recipes
        self.executor = executor

    def submit(self, filename: str, content: bytes, recipe_name: str) -> tuple[Job, Run]:
        recipe = self.recipes.get(recipe_name)
        job = Job(filename=filename, recipe_name=recipe_name)
        run = Run(job_id=job.id)
        self.repository.add_job(job)
        self.repository.add_run(run)
        self._persist(job, run, "source_pdf", content, "application/pdf")

        job.status = "running"
        run.status = "running"
        self.repository.update_job(job)
        self.repository.update_run(run)

        context = PipelineContext(job_id=job.id, run_id=run.id, source_pdf=content)
        try:
            self.executor.execute(recipe, context)
            job.status = "succeeded"
            run.status = "succeeded"
        except Exception as exc:
            job.status = "failed"
            run.status = "failed"
            run.error = str(exc)
        finally:
            # Persist every output produced before a failure so debugging does not
            # collapse to source_pdf only.
            self._persist_outputs(job, run, context.values)
            run.finished_at = datetime.now(timezone.utc)
            self.repository.update_job(job)
            self.repository.update_run(run)

        return job, run

    def get_job(self, job_id: UUID) -> Job | None:
        return self.repository.get_job(job_id)

    def list_jobs(self) -> list[Job]:
        return self.repository.list_jobs()

    def runs_for_job(self, job_id: UUID) -> list[Run]:
        return self.repository.list_runs_for_job(job_id)

    def artifacts_for_job(self, job_id: UUID) -> list[Artifact]:
        return self.repository.list_artifacts_for_job(job_id)

    def _persist_outputs(self, job: Job, run: Run, values: dict[str, object]) -> None:
        for key, value in values.items():
            if isinstance(value, DocumentIR | SemanticDocumentIR | ValidationResult):
                self._persist(
                    job,
                    run,
                    key,
                    value.model_dump_json(indent=2).encode(),
                    "application/json",
                )
            elif isinstance(value, bytes):
                media = "application/pdf" if key.endswith("_pdf") else "application/octet-stream"
                if key in {"report", "normalization_report"}:
                    media = "application/json"
                self._persist(job, run, key, value, media)

    def _persist(
        self,
        job: Job,
        run: Run,
        kind: str,
        content: bytes,
        media_type: str,
    ) -> None:
        extension = {
            "application/pdf": ".pdf",
            "application/json": ".json",
        }.get(media_type, "")
        key = f"{job.id}/{run.id}/{kind}{extension}"
        uri = self.store.put(key, content, media_type)
        self.repository.add_artifact(
            Artifact(
                job_id=job.id,
                run_id=run.id,
                kind=kind,
                uri=uri,
                media_type=media_type,
            )
        )
