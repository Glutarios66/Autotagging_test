from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from pdf_remediation.bootstrap import Container, build_container

app = FastAPI(title="PDF Remediation Research API", version="0.2.0")


@lru_cache(maxsize=1)
def container() -> Container:
    return build_container()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recipes")
def list_recipes() -> dict[str, list[str]]:
    return {"recipes": container().recipes.names()}


@app.get("/adapters")
def list_adapters() -> dict[str, list[str]]:
    return {"adapters": container().adapters.names()}


@app.post("/jobs", status_code=201)
async def create_job(
    file: UploadFile = File(...),
    recipe_name: str = Form("mock_remediation"),
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
    return [
        run.model_dump(mode="json")
        for run in container().service.runs_for_job(job_id)
    ]


@app.get("/jobs/{job_id}/artifacts")
def list_artifacts(job_id: UUID) -> list[dict[str, object]]:
    return [
        artifact.model_dump(mode="json")
        for artifact in container().service.artifacts_for_job(job_id)
    ]
