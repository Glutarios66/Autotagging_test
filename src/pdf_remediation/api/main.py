from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile

from pdf_remediation.bootstrap import Container, build_container
from pdf_remediation.domain.review import Experiment, ExperimentMetric, ReviewCorrection

app = FastAPI(title="PDF Remediation Research API", version="0.5.0")


@lru_cache(maxsize=1)
def container() -> Container:
    return build_container()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recipes")
def list_recipes() -> dict[str, list[str]]:
    return {"recipes": container().recipes.names()}


@app.get("/recipes/status")
def recipe_status() -> dict[str, dict[str, object]]:
    current = container()
    statuses: dict[str, dict[str, object]] = {}
    registered = set(current.adapters.names())

    for recipe_name in current.recipes.names():
        recipe = current.recipes.get(recipe_name)
        missing = [
            f"{step.type}/{step.adapter}"
            for step in recipe.steps
            if f"{step.type}/{step.adapter}" not in registered
        ]
        statuses[recipe_name] = {
            "ready": not missing,
            "missing_adapters": missing,
        }

    return statuses


@app.get("/adapters")
def list_adapters() -> dict[str, list[str]]:
    return {"adapters": container().adapters.names()}


@app.post("/jobs", status_code=201)
async def create_job(
    file: UploadFile = File(...),
    recipe_name: str = Form("accessibility_full"),
) -> dict[str, object]:
    settings = container().settings
    content = await file.read(settings.max_upload_bytes + 1)

    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds upload limit")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="uploaded file is not a PDF")
    if recipe_name not in container().recipes.names():
        raise HTTPException(status_code=422, detail=f"unknown recipe: {recipe_name}")

    job, run = container().service.submit(
        filename=file.filename or "upload.pdf",
        content=content,
        recipe_name=recipe_name,
    )
    return {"job": job.model_dump(mode="json"), "run": run.model_dump(mode="json")}


@app.get("/jobs")
def list_jobs() -> list[dict[str, object]]:
    return [job.model_dump(mode="json") for job in container().service.list_jobs()]


@app.get("/jobs/{job_id}")
def get_job(job_id: UUID) -> dict[str, object]:
    job = container().service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.model_dump(mode="json")


@app.get("/jobs/{job_id}/runs")
def list_runs(job_id: UUID) -> list[dict[str, object]]:
    return [run.model_dump(mode="json") for run in container().service.runs_for_job(job_id)]


@app.get("/jobs/{job_id}/artifacts")
def list_artifacts(job_id: UUID) -> list[dict[str, object]]:
    return [
        artifact.model_dump(mode="json")
        for artifact in container().service.artifacts_for_job(job_id)
    ]


@app.get("/jobs/{job_id}/artifacts/{artifact_id}/download")
def download_artifact(job_id: UUID, artifact_id: UUID) -> Response:
    artifacts = container().service.artifacts_for_job(job_id)
    artifact = next((item for item in artifacts if item.id == artifact_id), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")

    content = container().artifact_store.get(artifact.uri)
    extension = ".pdf" if artifact.media_type == "application/pdf" else ".json"
    filename = f"{artifact.kind}{extension}"
    return Response(
        content=content,
        media_type=artifact.media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/jobs/{job_id}/reviews", status_code=201)
def add_review(job_id: UUID, correction: ReviewCorrection) -> dict[str, object]:
    if correction.job_id != job_id:
        raise HTTPException(status_code=422, detail="job id mismatch")
    return container().review_service.add_correction(correction).model_dump(mode="json")


@app.get("/jobs/{job_id}/reviews")
def list_reviews(job_id: UUID) -> list[dict[str, object]]:
    return [
        correction.model_dump(mode="json")
        for correction in container().review_service.corrections_for_job(job_id)
    ]


@app.post("/experiments", status_code=201)
def create_experiment(experiment: Experiment) -> dict[str, object]:
    return container().review_service.create_experiment(experiment).model_dump(mode="json")


@app.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: UUID) -> dict[str, object]:
    experiment = container().review_service.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return experiment.model_dump(mode="json")


@app.post("/experiments/{experiment_id}/metrics", status_code=201)
def add_experiment_metric(
    experiment_id: UUID,
    metric: ExperimentMetric,
) -> dict[str, object]:
    if metric.experiment_id != experiment_id:
        raise HTTPException(status_code=422, detail="experiment id mismatch")
    return container().review_service.add_metric(metric).model_dump(mode="json")


@app.get("/experiments/{experiment_id}/metrics")
def list_experiment_metrics(experiment_id: UUID) -> list[dict[str, object]]:
    return [
        metric.model_dump(mode="json")
        for metric in container().review_service.metrics(experiment_id)
    ]
