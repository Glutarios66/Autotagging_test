from __future__ import annotations

from pathlib import Path

import yaml

from pdf_remediation.pipeline.models import PipelineRecipe


def load_recipe(path: Path) -> PipelineRecipe:
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return PipelineRecipe.model_validate(data)


def load_recipes(directory: Path) -> list[PipelineRecipe]:
    return [load_recipe(path) for path in sorted(directory.glob("*.yaml"))]
