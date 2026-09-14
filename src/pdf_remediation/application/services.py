from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pdf_remediation.domain import (
    Artifact,
    ArtifactKind,
    Batch,
    Experiment,
    Job,
    JobStatus,
    PipelineRun,
    ReviewItem,
    RunStatus,
    StageExecution,
    utc_now,
)
from pdf_remediation.ir import DocumentIR, SemanticDocumentIR, ValidationResult
from pdf_remediation.pipeline import PipelineContext, PipelineExecutor, RecipeRegistry
from pdf_remediation.ports import ArtifactStore, Repository

logger = logging.getLogger(__name__)


class RemediationService:
    def __init__(
        self,
        repository: Repository,
        artifacts: ArtifactStore,
        recipes: RecipeRegistry,
        executor: PipelineExecutor,
    ) -> None:
        self.repository = repository
        self.artifacts = artifacts
        self.recipes = recipes
        self.executor = executor

    def submit(
        self,
        filename: str,
        content: bytes,
        recipe_name: str = "structured_pipeline",
        batch_id: UUID | None = None,
        experiment_id: UUID | None = None,
    ) -> tuple[Job, PipelineRun]:
        if not content.startswith(b"%PDF-"):
            raise ValueError("uploaded file must have a PDF header")
        self.recipes.get(recipe_name)
        if batch_id is not None and self.repository.get_batch(batch_id) is None:
            raise ValueError("batch does not exist")
        if experiment_id is not None and self.repository.get_experiment(experiment_id) is None:
            raise ValueError("experiment does not exist")
        job_id = uuid4()
        safe_name = Path(filename).name or "upload.pdf"
        source = self._store_artifact(
            uuid4(),
            job_id,
            None,
            ArtifactKind.SOURCE_PDF,
            f"jobs/{job_id}/source/{safe_name}",
            content,
            "application/pdf",
        )
        job = self.repository.create_job(
            Job(
                id=job_id,
                batch_id=batch_id,
                filename=safe_name,
                source_artifact_id=source.id,
                status=JobStatus.QUEUED,
            )
        )
        self.repository.create_artifact(source)
        run = self.repository.create_run(
            PipelineRun(
                job_id=job.id,
                recipe_name=recipe_name,
                experiment_id=experiment_id,
                status=RunStatus.QUEUED,
            )
        )
        logger.info("run_submitted", extra={"job_id": str(job.id), "run_id": str(run.id)})
        return job, run

    def process(self, run_id: UUID) -> PipelineRun:
        run = self._required_run(run_id)
        job = self._required_job(run.job_id)
        run.status = RunStatus.RUNNING
        run.updated_at = utc_now()
        job.status = JobStatus.RUNNING
        job.updated_at = run.updated_at
        self.repository.update_run(run)
        self.repository.update_job(job)
        try:
            context = self._build_context(job, run)
            result = self.executor.execute(
                self.recipes.get(run.recipe_name),
                context,
                from_stage=run.rerun_from_stage,
                on_stage_created=self.repository.create_stage_execution,
                on_stage_updated=self.repository.update_stage_execution,
            )
            self._persist_outputs(job.id, run.id, result.values)
            self._create_reviews(job.id, run.id, result.values.get("validation_result"))
            run.status = RunStatus.SUCCEEDED
            job.status = JobStatus.SUCCEEDED
            logger.info("run_succeeded", extra={"job_id": str(job.id), "run_id": str(run.id)})
        except Exception as exc:
            run.status = RunStatus.FAILED
            job.status = JobStatus.FAILED
            run.error = str(exc)
            job.error = str(exc)
            logger.exception("run_failed", extra={"job_id": str(job.id), "run_id": str(run.id)})
            raise
        finally:
            now = utc_now()
            run.updated_at = now
            job.updated_at = now
            self.repository.update_run(run)
            self.repository.update_job(job)
        return run

    def rerun(self, run_id: UUID, from_stage: str) -> PipelineRun:
        parent = self._required_run(run_id)
        recipe = self.recipes.get(parent.recipe_name)
        recipe.steps_from(from_stage)
        rerun = PipelineRun(
            job_id=parent.job_id,
            recipe_name=parent.recipe_name,
            experiment_id=parent.experiment_id,
            parent_run_id=parent.id,
            rerun_from_stage=from_stage,
            status=RunStatus.QUEUED,
        )
        return self.repository.create_run(rerun)

    def create_batch(self, name: str, metadata: dict[str, Any] | None = None) -> Batch:
        return self.repository.create_batch(Batch(name=name, metadata=metadata or {}))

    def create_experiment(
        self,
        name: str,
        recipe_name: str,
        batch_id: UUID | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Experiment:
        self.recipes.get(recipe_name)
        if batch_id is not None and self.repository.get_batch(batch_id) is None:
            raise ValueError("batch does not exist")
        return self.repository.create_experiment(
            Experiment(
                name=name,
                recipe_name=recipe_name,
                batch_id=batch_id,
                parameters=parameters or {},
            )
        )

    def _required_run(self, run_id: UUID) -> PipelineRun:
        run = self.repository.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def _required_job(self, job_id: UUID) -> Job:
        job = self.repository.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def _build_context(self, job: Job, run: PipelineRun) -> PipelineContext:
        source_artifact = self.repository.get_artifact(job.source_artifact_id)
        if source_artifact is None:
            raise RuntimeError("source artifact is missing")
        values: dict[str, Any] = {
            "source_bytes": self.artifacts.get(source_artifact.object_key),
            "filename": job.filename,
        }
        if run.parent_run_id is not None:
            for artifact in self.repository.list_artifacts(job.id, run.parent_run_id):
                key = {
                    ArtifactKind.DOCUMENT_IR: "document_ir",
                    ArtifactKind.SEMANTIC_IR: "semantic_ir",
                    ArtifactKind.CANDIDATE: "candidate_pdf",
                    ArtifactKind.VALIDATION: "validation_result",
                    ArtifactKind.FINAL_PDF: "final_pdf",
                }.get(artifact.kind)
                if key and artifact.content_type == "application/json":
                    payload = json.loads(self.artifacts.get(artifact.object_key))
                    model_types = {
                        "document_ir": DocumentIR,
                        "semantic_ir": SemanticDocumentIR,
                        "validation_result": ValidationResult,
                    }
                    values[key] = model_types[key].model_validate(payload) if key in model_types else payload
                elif key:
                    values[key] = self.artifacts.get(artifact.object_key)
        return PipelineContext(job.id, run.id, run.recipe_name, values=values)

    def _persist_outputs(self, job_id: UUID, run_id: UUID, result: dict[str, Any]) -> None:
        outputs = [
            ("document_ir", ArtifactKind.DOCUMENT_IR, "application/json"),
            ("semantic_ir", ArtifactKind.SEMANTIC_IR, "application/json"),
            ("candidate_pdf", ArtifactKind.CANDIDATE, "application/pdf"),
            ("validation_result", ArtifactKind.VALIDATION, "application/json"),
            ("final_pdf", ArtifactKind.FINAL_PDF, "application/pdf"),
            ("report", ArtifactKind.REPORT, "application/json"),
        ]
        for name, kind, content_type in outputs:
            if name not in result:
                continue
            value = result[name]
            if isinstance(value, bytes):
                content = value
            elif hasattr(value, "model_dump_json"):
                content = value.model_dump_json(indent=2).encode()
            else:
                content = json.dumps(value, indent=2, sort_keys=True).encode()
            extension = "pdf" if content_type == "application/pdf" else "json"
            artifact = self._store_artifact(
                uuid4(),
                job_id,
                run_id,
                kind,
                f"jobs/{job_id}/runs/{run_id}/{name}.{extension}",
                content,
                content_type,
            )
            self.repository.create_artifact(artifact)

    def _create_reviews(
        self, job_id: UUID, run_id: UUID, validation: ValidationResult | Any | None
    ) -> None:
        if not isinstance(validation, ValidationResult):
            return
        for issue in validation.issues:
            self.repository.create_review_item(
                ReviewItem(
                    job_id=job_id,
                    run_id=run_id,
                    category=issue.code,
                    message=issue.message,
                    element_id=issue.element_id,
                    page=issue.page,
                )
            )

    def _store_artifact(
        self,
        artifact_id: UUID,
        job_id: UUID,
        run_id: UUID | None,
        kind: ArtifactKind,
        key: str,
        content: bytes,
        content_type: str,
        stage_execution: StageExecution | None = None,
    ) -> Artifact:
        self.artifacts.put(key, content, content_type)
        return Artifact(
            id=artifact_id,
            job_id=job_id,
            run_id=run_id,
            stage_execution_id=stage_execution.id if stage_execution else None,
            kind=kind,
            object_key=key,
            content_type=content_type,
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
        )
