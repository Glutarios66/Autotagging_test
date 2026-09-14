from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class PipelineContext:
    job_id: UUID
    run_id: UUID
    source_pdf: bytes
    values: dict[str, Any] = field(default_factory=dict)
