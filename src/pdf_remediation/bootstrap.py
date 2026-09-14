from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_remediation.adapters import (
    AccessibilityReportGenerator,
    CIDSetFontNormalizer,
    MockAccessibilityValidator,
    MockFinalizer,
    MockPDFExtractor,
    MockPDFRemediator,
    MockReportGenerator,
    MockSemanticAnalyzer,
    OpenAIStructureAnalyzer,
    OpenDataLoaderExtractor,
    OpenDataLoaderSemanticAnalyzer,
    OpenDataLoaderTagger,
    PassThroughFinalizer,
    PyMuPDFExtractor,
    VeraPDFValidator,
)
from pdf_remediation.application import RemediationService
from pdf_remediation.application.review_service import ReviewExperimentService
from pdf_remediation.infrastructure import (
    FileSystemArtifactStore,
    S3ArtifactStore,
    SQLAlchemyRepository,
)
from pdf_remediation.pipeline import AdapterRegistry, PipelineExecutor, RecipeRegistry, load_recipes
from pdf_remediation.pipeline.components import (
    AnalyzeComponent,
    NormalizeComponent,
    ExtractComponent,
    FinalizeComponent,
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
    review_service: ReviewExperimentService


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    configure_logging(settings.log_level, settings.json_logs)

    engine_args = (
        {"connect_args": {"check_same_thread": False}}
        if settings.database_url.startswith("sqlite")
        else {}
    )
    engine = create_engine(settings.database_url, **engine_args)
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

    # Extraction
    adapters.register("extract", "mock", ExtractComponent(MockPDFExtractor()))
    adapters.register("extract", "pymupdf", ExtractComponent(PyMuPDFExtractor()))
    adapters.register(
        "extract",
        "opendataloader",
        ExtractComponent(OpenDataLoaderExtractor()),
    )

    # Semantic analysis
    adapters.register("semantic_analysis", "mock", AnalyzeComponent(MockSemanticAnalyzer()))
    adapters.register(
        "semantic_analysis",
        "opendataloader",
        AnalyzeComponent(OpenDataLoaderSemanticAnalyzer()),
    )
    if settings.openai_api_key:
        adapters.register(
            "semantic_analysis",
            "openai",
            AnalyzeComponent(
                OpenAIStructureAnalyzer(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    base_url=settings.openai_base_url,
                )
            ),
        )

    # Remediation
    adapters.register("remediation", "mock", RemediateComponent(MockPDFRemediator()))
    adapters.register(
        "remediation",
        "opendataloader",
        RemediateComponent(OpenDataLoaderTagger()),
    )

    # Targeted PDF normalization
    adapters.register(
        "normalization",
        "cidset",
        NormalizeComponent(CIDSetFontNormalizer()),
    )

    # Validation/finalization/reporting
    adapters.register("validation", "mock", ValidateComponent(MockAccessibilityValidator()))
    adapters.register(
        "validation",
        "verapdf",
        ValidateComponent(
            VeraPDFValidator(
                executable=settings.verapdf_executable,
                flavour=settings.verapdf_flavour,
            )
        ),
    )
    adapters.register("finalization", "mock", FinalizeComponent(MockFinalizer()))
    adapters.register(
        "finalization",
        "passthrough",
        FinalizeComponent(PassThroughFinalizer()),
    )
    adapters.register("report", "mock", ReportComponent(MockReportGenerator()))
    adapters.register(
        "report",
        "accessibility",
        ReportComponent(AccessibilityReportGenerator()),
    )

    recipes = RecipeRegistry()
    for recipe in load_recipes(settings.recipe_dir):
        recipes.register(recipe)

    service = RemediationService(repository, store, recipes, PipelineExecutor(adapters))
    return Container(
        settings=settings,
        repository=repository,
        artifact_store=store,
        recipes=recipes,
        adapters=adapters,
        service=service,
        review_service=ReviewExperimentService(),
    )
