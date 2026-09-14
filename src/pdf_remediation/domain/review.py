from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReviewCorrection(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    run_id: UUID
    semantic_node_id: str
    action: Literal["change_role", "change_order", "set_alt_text", "approve", "reject"]
    value: Any = None
    reviewer: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Experiment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    recipe_names: list[str]
    status: Literal["draft", "running", "completed"] = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class ExperimentMetric(BaseModel):
    experiment_id: UUID
    recipe_name: str
    metric: str
    value: float
    unit: str | None = None
