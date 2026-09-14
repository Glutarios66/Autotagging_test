from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class LifecycleStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


JobStatus = LifecycleStatus
RunStatus = LifecycleStatus
BatchStatus = LifecycleStatus
ExperimentStatus = LifecycleStatus


class ReviewStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class StageStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ArtifactKind(StrEnum):
    SOURCE_PDF = "source_pdf"
    DOCUMENT_IR = "document_ir"
    SEMANTIC_IR = "semantic_ir"
    CANDIDATE = "candidate"
    VALIDATION = "validation"
    FINAL_PDF = "final_pdf"
    REPORT = "report"
    REMEDIATED_PDF = "remediated_pdf"


class Batch(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    status: BatchStatus = BatchStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Job(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    batch_id: UUID | None = None
    filename: str
    source_artifact_id: UUID
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    error: str | None = None


class Experiment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    recipe_name: str
    batch_id: UUID | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PipelineRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    recipe_name: str
    experiment_id: UUID | None = None
    parent_run_id: UUID | None = None
    rerun_from_stage: str | None = None
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    error: str | None = None


class StageExecution(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    stage_id: str
    stage_type: str
    adapter_name: str
    status: StageStatus = StageStatus.PENDING
    attempt: int = 1
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    input_artifact_ids: list[UUID] = Field(default_factory=list)
    output_artifact_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ReviewItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    run_id: UUID
    stage_execution_id: UUID | None = None
    status: ReviewStatus = ReviewStatus.OPEN
    category: str
    message: str
    element_id: str | None = None
    page: int | None = None
    assigned_to: str | None = None
    resolution: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    run_id: UUID | None = None
    stage_execution_id: UUID | None = None
    kind: ArtifactKind
    object_key: str
    content_type: str
    checksum_sha256: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
