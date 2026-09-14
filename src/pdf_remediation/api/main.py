from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from pdf_remediation.bootstrap import Container, build_container
from pdf_remediation.domain import (
    Artifact,
    Batch,
    Experiment,
    Job,
    PipelineRun,
    ReviewItem,
    ReviewStatus,
    StageExecution,
    utc_now,
)

app = FastAPI(title="PDF Remediation Research API", version="0.1.0")


class BatchCreate(BaseModel):
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentCreate(BaseModel):
    name: str
    recipe_name: str = "structured_pipeline"
    batch_id: UUID | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class RerunRequest(BaseModel):
    from_stage: str


class ReviewUpdate(BaseModel):
    status: ReviewStatus
    assigned_to: str | None = None
    resolution: str | None = None


class SubmissionResponse(BaseModel):
    job: Job
    run: PipelineRun


@lru_cache
def container() -> Container:
    return build_container()


def enqueue(run: PipelineRun) -> PipelineRun:
    if container().settings.run_jobs_inline:
        return container().service.process(run.id)
    from pdf_remediation.workers.tasks import process_run

    process_run.apply_async(
        args=[str(run.id)], queue=container().settings.celery_queue
    )
    return run


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recipes")
def recipes() -> dict[str, list[str]]:
    return {"recipes": container().recipes.names()}


@app.post("/jobs", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    pdf_file: UploadFile = File(..., alias="file"),
    recipe_name: str = Form("structured_pipeline"),
    batch_id: UUID | None = Form(None),
    experiment_id: UUID | None = Form(None),
) -> SubmissionResponse:
    content = await pdf_file.read(container().settings.max_upload_bytes + 1)
    if len(content) > container().settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="upload exceeds configured size limit")
    try:
        job, run = container().service.submit(
            pdf_file.filename or "upload.pdf",
            content,
            recipe_name,
            batch_id,
            experiment_id,
        )
        return SubmissionResponse(job=job, run=enqueue(run))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/jobs", response_model=list[Job])
def list_jobs(batch_id: UUID | None = None) -> list[Job]:
    return container().repository.list_jobs(batch_id)


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: UUID) -> Job:
    job = container().repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/jobs/{job_id}/runs", response_model=list[PipelineRun])
def list_runs(job_id: UUID) -> list[PipelineRun]:
    if container().repository.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return container().repository.list_runs(job_id)


@app.get("/jobs/{job_id}/artifacts", response_model=list[Artifact])
def list_artifacts(job_id: UUID, run_id: UUID | None = None) -> list[Artifact]:
    if container().repository.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return container().repository.list_artifacts(job_id, run_id)


@app.post("/batches", response_model=Batch, status_code=status.HTTP_201_CREATED)
def create_batch(request: BatchCreate) -> Batch:
    return container().service.create_batch(request.name, request.metadata)


@app.get("/batches", response_model=list[Batch])
def list_batches() -> list[Batch]:
    return container().repository.list_batches()


@app.get("/batches/{batch_id}", response_model=Batch)
def get_batch(batch_id: UUID) -> Batch:
    batch = container().repository.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return batch


@app.post("/batches/{batch_id}/jobs", response_model=list[SubmissionResponse])
async def create_batch_jobs(
    batch_id: UUID,
    files: list[UploadFile] = File(...),
    recipe_name: str = Form("structured_pipeline"),
    experiment_id: UUID | None = Form(None),
) -> list[SubmissionResponse]:
    responses: list[SubmissionResponse] = []
    for pdf_file in files:
        content = await pdf_file.read(container().settings.max_upload_bytes + 1)
        if len(content) > container().settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="upload exceeds configured size limit")
        try:
            job, run = container().service.submit(
                pdf_file.filename or "upload.pdf",
                content,
                recipe_name,
                batch_id,
                experiment_id,
            )
            responses.append(SubmissionResponse(job=job, run=enqueue(run)))
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return responses


@app.post("/experiments", response_model=Experiment, status_code=status.HTTP_201_CREATED)
def create_experiment(request: ExperimentCreate) -> Experiment:
    try:
        return container().service.create_experiment(
            request.name, request.recipe_name, request.batch_id, request.parameters
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/experiments", response_model=list[Experiment])
def list_experiments() -> list[Experiment]:
    return container().repository.list_experiments()


@app.get("/experiments/{experiment_id}", response_model=Experiment)
def get_experiment(experiment_id: UUID) -> Experiment:
    experiment = container().repository.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return experiment


@app.get("/runs/{run_id}", response_model=PipelineRun)
def get_run(run_id: UUID) -> PipelineRun:
    run = container().repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/runs/{run_id}/stages", response_model=list[StageExecution])
def list_stages(run_id: UUID) -> list[StageExecution]:
    if container().repository.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    return container().repository.list_stage_executions(run_id)


@app.post("/runs/{run_id}/rerun", response_model=PipelineRun, status_code=201)
def rerun(run_id: UUID, request: RerunRequest) -> PipelineRun:
    try:
        return enqueue(container().service.rerun(run_id, request.from_stage))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/review-items", response_model=list[ReviewItem])
def list_review_items(job_id: UUID | None = None) -> list[ReviewItem]:
    return container().repository.list_review_items(job_id)


@app.get("/review-items/{item_id}", response_model=ReviewItem)
def get_review_item(item_id: UUID) -> ReviewItem:
    item = container().repository.get_review_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="review item not found")
    return item


@app.patch("/review-items/{item_id}", response_model=ReviewItem)
def update_review_item(item_id: UUID, request: ReviewUpdate) -> ReviewItem:
    item = container().repository.get_review_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="review item not found")
    item.status = request.status
    item.assigned_to = request.assigned_to
    item.resolution = request.resolution
    item.updated_at = utc_now()
    return container().repository.update_review_item(item)


@app.get("/artifacts/{artifact_id}")
def download_artifact(artifact_id: UUID) -> Response:
    artifact = container().repository.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return Response(
        content=container().artifact_store.get(artifact.object_key),
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{artifact.object_key.rsplit("/", 1)[-1]}"'
            )
        },
    )
