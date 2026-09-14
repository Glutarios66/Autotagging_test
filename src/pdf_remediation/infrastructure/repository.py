from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from pdf_remediation.domain import (
    Artifact,
    Batch,
    Experiment,
    Job,
    PipelineRun,
    ReviewItem,
    StageExecution,
)
from pdf_remediation.infrastructure.database import (
    ArtifactRow,
    BatchRow,
    ExperimentRow,
    JobRow,
    PipelineRunRow,
    ReviewItemRow,
    StageExecutionRow,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class SQLAlchemyRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _row_values(model: BaseModel) -> dict[str, Any]:
        values = model.model_dump(mode="json")
        values["id"] = str(getattr(model, "id"))
        if "metadata" in values:
            values["metadata_json"] = values.pop("metadata")
        return values

    @staticmethod
    def _model_values(row: Any) -> dict[str, Any]:
        values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
        if "metadata_json" in values:
            values["metadata"] = values.pop("metadata_json")
        return values

    def _create(self, row_type: type[Any], model: ModelT) -> ModelT:
        values = self._row_values(model)
        with self.session_factory() as session:
            session.add(row_type(**values))
            session.commit()
        return model

    def _update(self, row_type: type[Any], model: ModelT) -> ModelT:
        with self.session_factory() as session:
            row = session.get(row_type, str(model.id))
            if row is None:
                raise KeyError(model.id)
            for key, value in self._row_values(model).items():
                setattr(row, key, value)
            session.commit()
        return model

    def _get(self, row_type: type[Any], model_type: type[ModelT], value: UUID) -> ModelT | None:
        with self.session_factory() as session:
            row = session.get(row_type, str(value))
            return None if row is None else model_type.model_validate(self._model_values(row))

    def _list(self, row_type: type[Any], model_type: type[ModelT], *filters: Any) -> list[ModelT]:
        with self.session_factory() as session:
            statement = select(row_type)
            for condition in filters:
                statement = statement.where(condition)
            rows = session.scalars(statement).all()
            return [model_type.model_validate(self._model_values(row)) for row in rows]

    def create_batch(self, batch: Batch) -> Batch:
        return self._create(BatchRow, batch)

    def update_batch(self, batch: Batch) -> Batch:
        return self._update(BatchRow, batch)

    def get_batch(self, batch_id: UUID) -> Batch | None:
        return self._get(BatchRow, Batch, batch_id)

    def list_batches(self) -> list[Batch]:
        return self._list(BatchRow, Batch)

    def create_job(self, job: Job) -> Job:
        return self._create(JobRow, job)

    def update_job(self, job: Job) -> Job:
        return self._update(JobRow, job)

    def get_job(self, job_id: UUID) -> Job | None:
        return self._get(JobRow, Job, job_id)

    def list_jobs(self, batch_id: UUID | None = None) -> list[Job]:
        filters = () if batch_id is None else (JobRow.batch_id == str(batch_id),)
        return self._list(JobRow, Job, *filters)

    def create_experiment(self, experiment: Experiment) -> Experiment:
        return self._create(ExperimentRow, experiment)

    def update_experiment(self, experiment: Experiment) -> Experiment:
        return self._update(ExperimentRow, experiment)

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        return self._get(ExperimentRow, Experiment, experiment_id)

    def list_experiments(self) -> list[Experiment]:
        return self._list(ExperimentRow, Experiment)

    def create_run(self, run: PipelineRun) -> PipelineRun:
        return self._create(PipelineRunRow, run)

    def update_run(self, run: PipelineRun) -> PipelineRun:
        return self._update(PipelineRunRow, run)

    def get_run(self, run_id: UUID) -> PipelineRun | None:
        return self._get(PipelineRunRow, PipelineRun, run_id)

    def list_runs(self, job_id: UUID) -> list[PipelineRun]:
        return self._list(PipelineRunRow, PipelineRun, PipelineRunRow.job_id == str(job_id))

    def create_stage_execution(self, execution: StageExecution) -> StageExecution:
        return self._create(StageExecutionRow, execution)

    def update_stage_execution(self, execution: StageExecution) -> StageExecution:
        return self._update(StageExecutionRow, execution)

    def list_stage_executions(self, run_id: UUID) -> list[StageExecution]:
        return self._list(
            StageExecutionRow, StageExecution, StageExecutionRow.run_id == str(run_id)
        )

    def create_review_item(self, item: ReviewItem) -> ReviewItem:
        return self._create(ReviewItemRow, item)

    def update_review_item(self, item: ReviewItem) -> ReviewItem:
        return self._update(ReviewItemRow, item)

    def get_review_item(self, item_id: UUID) -> ReviewItem | None:
        return self._get(ReviewItemRow, ReviewItem, item_id)

    def list_review_items(self, job_id: UUID | None = None) -> list[ReviewItem]:
        filters = () if job_id is None else (ReviewItemRow.job_id == str(job_id),)
        return self._list(ReviewItemRow, ReviewItem, *filters)

    def create_artifact(self, artifact: Artifact) -> Artifact:
        return self._create(ArtifactRow, artifact)

    def get_artifact(self, artifact_id: UUID) -> Artifact | None:
        return self._get(ArtifactRow, Artifact, artifact_id)

    def list_artifacts(self, job_id: UUID, run_id: UUID | None = None) -> list[Artifact]:
        filters = [ArtifactRow.job_id == str(job_id)]
        if run_id is not None:
            filters.append(ArtifactRow.run_id == str(run_id))
        return self._list(ArtifactRow, Artifact, *filters)
