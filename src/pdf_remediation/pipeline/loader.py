from __future__ import annotations

from pathlib import Path

import yaml

from pdf_remediation.pipeline.models import PipelineRecipe


def load_recipes(recipe_dir: Path) -> list[PipelineRecipe]:
    recipes: list[PipelineRecipe] = []
    if not recipe_dir.exists():
        return recipes
    for path in sorted(recipe_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        recipes.append(PipelineRecipe.model_validate(data))
    return recipes
