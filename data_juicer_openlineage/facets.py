import os
from typing import Any

import attrs
from openlineage.client.facet_v2 import JobFacet, RunFacet

SCHEMA_BASE_URL = os.getenv(
    "DATA_JUICER_OPENLINEAGE_SCHEMA_BASE_URL",
    "https://raw.githubusercontent.com/Dludora/data-juicer-openlineage/main/data_juicer_openlineage/schemas",
)
RUN_FACET_SCHEMA_URL = f"{SCHEMA_BASE_URL}/DataJuicerRunFacet.json"
PIPELINE_JOB_FACET_SCHEMA_URL = f"{SCHEMA_BASE_URL}/DataJuicerPipelineJobFacet.json"
OPERATOR_JOB_FACET_SCHEMA_URL = f"{SCHEMA_BASE_URL}/DataJuicerOperatorJobFacet.json"


@attrs.define
class DataJuicerRunFacet(RunFacet):
    jobId: str | None = None
    executorType: str | None = None
    status: str | None = None
    durationSeconds: float | None = None
    errorMessage: str | None = None
    workDir: str | None = None
    custom: dict[str, Any] = attrs.field(factory=dict)

    @staticmethod
    def _get_schema() -> str:
        return RUN_FACET_SCHEMA_URL


@attrs.define
class DataJuicerCodeVersion:
    repoOwner: str | None = None
    repoUrl: str | None = None
    relativePath: str | None = None
    commit: str | None = None
    tag: str | None = None
    branch: str | None = None
    dirty: bool | None = None
    packageVersion: str | None = None
    authorName: str | None = None
    authorEmail: str | None = None
    committerName: str | None = None
    committerEmail: str | None = None


@attrs.define
class DataJuicerPipelineJobFacet(JobFacet):
    projectName: str | None = None
    executorType: str | None = None
    configPath: str | None = None
    numOperators: int | None = None
    recipeHash: str | None = None
    recipe: Any = None
    operatorNames: list[str] = attrs.field(factory=list)
    dag: dict[str, Any] = attrs.field(factory=dict)

    @staticmethod
    def _get_schema() -> str:
        return PIPELINE_JOB_FACET_SCHEMA_URL


@attrs.define
class DataJuicerOperatorJobFacet(JobFacet):
    projectName: str | None = None
    executorType: str | None = None
    configPath: str | None = None
    opName: str | None = None
    opType: str | None = None
    opIndex: int | None = None
    recipeHash: str | None = None
    recipe: Any = None
    code: DataJuicerCodeVersion | None = None

    @staticmethod
    def _get_schema() -> str:
        return OPERATOR_JOB_FACET_SCHEMA_URL
