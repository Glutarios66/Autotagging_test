from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pdf_remediation.domain import Artifact, Job, Run
from pdf_remediation.infrastructure.models import ArtifactRow, JobRow, RunRow


class SQLAlchemyRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory

    def add_job(self, job: Job) -> None:
        with self.factory.begin() as session:
            session.add(
                JobRow(
                    id=str(job.id),
                    filename=job.filename,
                    recipe_name=job.recipe_name,
                    status=job.status,
                    created_at=job.created_at,
                )
            )

    def get_job(self, job_id: UUID) -> Job | None:
        with self.factory() as session:
            row = session.get(JobRow, str(job_id))
            return Job.model_validate(row.__dict__) if row else None

    def list_jobs(self) -> list[Job]:
        with self.factory() as session:
            rows = session.scalars(select(JobRow).order_by(JobRow.created_at.desc())).all()
            return [Job.model_validate(row.__dict__) for row in rows]

    def update_job(self, job: Job) -> None:
        with self.factory.begin() as session:
            row = session.get(JobRow, str(job.id))
            if row is None:
                raise KeyError(job.id)
            row.status = job.status

    def add_run(self, run: Run) -> None:
        with self.factory.begin() as session:
            session.add(
                RunRow(
                    id=str(run.id),
                    job_id=str(run.job_id),
                    status=run.status,
                    error=run.error,
                    created_at=run.created_at,
                    finished_at=run.finished_at,
                )
            )

    def get_run(self, run_id: UUID) -> Run | None:
        with self.factory() as session:
            row = session.get(RunRow, str(run_id))
            return Run.model_validate(row.__dict__) if row else None

    def list_runs_for_job(self, job_id: UUID) -> list[Run]:
        with self.factory() as session:
            rows = session.scalars(
                select(RunRow)
                .where(RunRow.job_id == str(job_id))
                .order_by(RunRow.created_at.desc())
            ).all()
            return [Run.model_validate(row.__dict__) for row in rows]

    def update_run(self, run: Run) -> None:
        with self.factory.begin() as session:
            row = session.get(RunRow, str(run.id))
            if row is None:
                raise KeyError(run.id)
            row.status = run.status
            row.error = run.error
            row.finished_at = run.finished_at

    def add_artifact(self, artifact: Artifact) -> None:
        with self.factory.begin() as session:
            session.add(
                ArtifactRow(
                    id=str(artifact.id),
                    job_id=str(artifact.job_id),
                    run_id=str(artifact.run_id),
                    kind=artifact.kind,
                    uri=artifact.uri,
                    media_type=artifact.media_type,
                    created_at=artifact.created_at,
                )
            )

    def list_artifacts_for_job(self, job_id: UUID) -> list[Artifact]:
        with self.factory() as session:
            rows = session.scalars(
                select(ArtifactRow)
                .where(ArtifactRow.job_id == str(job_id))
                .order_by(ArtifactRow.created_at)
            ).all()
            return [Artifact.model_validate(row.__dict__) for row in rows]
