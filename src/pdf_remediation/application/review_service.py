from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from pdf_remediation.domain.review import Experiment, ExperimentMetric, ReviewCorrection


class ReviewExperimentService:
    def __init__(self) -> None:
        self._corrections: dict[UUID, list[ReviewCorrection]] = defaultdict(list)
        self._experiments: dict[UUID, Experiment] = {}
        self._metrics: dict[UUID, list[ExperimentMetric]] = defaultdict(list)

    def add_correction(self, correction: ReviewCorrection) -> ReviewCorrection:
        self._corrections[correction.job_id].append(correction)
        return correction

    def corrections_for_job(self, job_id: UUID) -> list[ReviewCorrection]:
        return list(self._corrections.get(job_id, []))

    def create_experiment(self, experiment: Experiment) -> Experiment:
        self._experiments[experiment.id] = experiment
        return experiment

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        return self._experiments.get(experiment_id)

    def add_metric(self, metric: ExperimentMetric) -> ExperimentMetric:
        self._metrics[metric.experiment_id].append(metric)
        return metric

    def metrics(self, experiment_id: UUID) -> list[ExperimentMetric]:
        return list(self._metrics.get(experiment_id, []))
