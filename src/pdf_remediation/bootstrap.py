from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_remediation.adapters import (
    MockAccessibilityValidator,
    MockFinalizer,
    MockMultimodalModel,
    MockPDFExtractor,
    MockPDFRemediator,
    MockReportGenerator,
    MockSemanticAnalyzer,
)
from pdf_remediation.application import RemediationService
from pdf_remediation.infrastructure import (
    Base,
    FileSystemArtifactStore,
    S3ArtifactStore,
    SQLAlchemyRepository,
)
from pdf_remediation.pipeline import AdapterRegistry, PipelineExecutor, RecipeRegistry, load_recipes
from pdf_remediation.pipeline.components import (
    AnalyzeComponent,
    BaselineComponent,
    ExtractComponent,
    FinalizeComponent,
    MultimodalComponent,
    RemediateComponent,
    ReportComponent,
    ValidateComponent,
)
from pdf_remediation.ports import ArtifactStore, Repository
from pdf_remediation.settings import Settings, configure_logging


@dataclass
class Container:
    settings: Settings
    repository: Repository
    artifact_store: ArtifactStore
    recipes: RecipeRegistry
    adapters: AdapterRegistry
    service: RemediationService


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    configure_logging(settings.log_level, settings.json_logs)
    engine_args = {"connect_args": {"check_same_thread": False}} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, **engine_args)
    Base.metadata.create_all(engine)
    repository = SQLAlchemyRepository(sessionmaker(engine, expire_on_commit=False))
    if settings.artifact_backend in {"s3", "minio"}:
        store: ArtifactStore = S3ArtifactStore(
            settings.s3_bucket,
            settings.s3_endpoint_url,
            settings.s3_access_key,
            settings.s3_secret_key,
            settings.s3_region,
        )
    else:
        store = FileSystemArtifactStore(settings.artifact_root)

    adapters = AdapterRegistry()
    adapters.register("baseline", "mock", BaselineComponent())
    adapters.register("extract", "mock", ExtractComponent(MockPDFExtractor()))
    adapters.register("semantic_analysis", "mock", AnalyzeComponent(MockSemanticAnalyzer()))
    adapters.register("multimodal_analysis", "mock", MultimodalComponent(MockMultimodalModel()))
    adapters.register("remediation", "mock", RemediateComponent(MockPDFRemediator()))
    adapters.register("validation", "mock", ValidateComponent(MockAccessibilityValidator()))
    adapters.register("finalization", "mock", FinalizeComponent(MockFinalizer()))
    adapters.register("report", "mock", ReportComponent(MockReportGenerator()))
    recipes = RecipeRegistry()
    for recipe in load_recipes(settings.recipe_dir):
        recipes.register(recipe)
    service = RemediationService(repository, store, recipes, PipelineExecutor(adapters))
    return Container(settings, repository, store, recipes, adapters, service)
