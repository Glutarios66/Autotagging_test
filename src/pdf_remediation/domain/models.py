from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename: str
    recipe_name: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    created_at: datetime = Field(default_factory=utcnow)


class Run(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    run_id: UUID
    kind: str
    uri: str
    media_type: str
    created_at: datetime = Field(default_factory=utcnow)
