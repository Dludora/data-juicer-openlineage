from __future__ import annotations

import traceback
import uuid
from typing import Any

from data_juicer import __version__
from data_juicer.core.metadata.models import (
    Ctx,
    DatasetRef,
    DatasetSnapshot,
    OpCtx,
    SchemaField,
)
from data_juicer.utils.config_utils import ConfigAccessor
from data_juicer_openlineage.facets import (
    DataJuicerCodeVersion,
    DataJuicerOperatorJobFacet,
    DataJuicerPipelineJobFacet,
    DataJuicerRunFacet,
)

DEFAULT_PRODUCER = f"https://github.com/datajuicer/data-juicer/tree/v{__version__}"


class OpenLineageBuilder:
    def __init__(self, provider_cfg: dict[str, Any] | None = None):
        self.provider_cfg = provider_cfg or {}
        self.producer = ConfigAccessor.get(
            self.provider_cfg, "producer", DEFAULT_PRODUCER
        )

    def build_pipeline_event(
        self, ctx: Ctx, event_type: str, error: Exception | None = None
    ) -> Any:
        from openlineage.client.event_v2 import Job, Run, RunEvent

        event_time = (
            ctx.started_at if event_type == "START" else ctx.ended_at or ctx.started_at
        )
        return RunEvent(
            eventTime=event_time,
            eventType=self._run_state(event_type),
            producer=self.producer,
            run=Run(
                runId=ctx.run_id,
                facets=self._build_pipeline_run_facets(ctx, event_type, error),
            ),
            job=Job(
                namespace=self._job_namespace(ctx),
                name=self._pipeline_job_name(ctx),
                facets=self._build_pipeline_job_facets(ctx),
            ),
            inputs=[
                self._build_input_dataset(ref, ctx.input_snapshot)
                for ref in self._snapshot_refs(ctx.input_snapshot)
            ],
            outputs=[
                self._build_output_dataset(ref, ctx.output_snapshot)
                for ref in self._snapshot_refs(ctx.output_snapshot)
            ],
        )

    def build_operator_event(
        self, ctx: Ctx, op_ctx: OpCtx, event_type: str, error: Exception | None = None
    ) -> Any:
        from openlineage.client.event_v2 import Job, Run, RunEvent

        event_time = (
            op_ctx.started_at
            if event_type == "START"
            else op_ctx.ended_at or op_ctx.started_at or ctx.started_at
        )
        return RunEvent(
            eventTime=event_time,
            eventType=self._run_state(event_type),
            producer=self.producer,
            run=Run(
                runId=self._operator_run_id(ctx, op_ctx),
                facets=self._build_operator_run_facets(ctx, op_ctx, event_type, error),
            ),
            job=Job(
                namespace=self._job_namespace(ctx),
                name=self._operator_job_name(ctx, op_ctx),
                facets=self._build_operator_job_facets(ctx, op_ctx),
            ),
            inputs=[
                self._build_input_dataset(ref, op_ctx.input_snapshot)
                for ref in self._snapshot_refs(op_ctx.input_snapshot)
            ],
            outputs=[
                self._build_output_dataset(ref, op_ctx.output_snapshot)
                for ref in self._snapshot_refs(op_ctx.output_snapshot)
            ],
        )

    def _build_pipeline_run_facets(
        self, ctx: Ctx, event_type: str, error: Exception | None
    ) -> dict[str, Any]:
        from openlineage.client.facet_v2 import (
            error_message_run,
            execution_parameters_run,
            processing_engine_run,
        )

        facets: dict[str, Any] = {
            "datajuicer": DataJuicerRunFacet(
                producer=self.producer,
                jobId=ctx.job_id,
                executorType=ctx.executor_type,
                status=ctx.status,
                durationSeconds=self._ctx_duration(ctx),
                errorMessage=str(error) if error else None,
                workDir=ConfigAccessor.get(ctx.extra, "work_dir", None),
                custom={
                    "namespace": ctx.namespace,
                    "run_id": ctx.run_id,
                },
            ),
            "processing_engine": processing_engine_run.ProcessingEngineRunFacet(
                name="data-juicer",
                version=__version__,
                openlineageAdapterVersion=__version__,
                producer=self.producer,
            ),
            "execution_parameters": execution_parameters_run.ExecutionParametersRunFacet(
                parameters=[
                    execution_parameters_run.ExecutionParameter(
                        key="project_name",
                        name="project_name",
                        value=ctx.project_name,
                    ),
                    execution_parameters_run.ExecutionParameter(
                        key="executor_type",
                        name="executor_type",
                        value=ctx.executor_type,
                    ),
                    execution_parameters_run.ExecutionParameter(
                        key="num_operators",
                        name="num_operators",
                        value=str(ConfigAccessor.get(ctx.extra, "num_operators", 0)),
                    ),
                ],
                producer=self.producer,
            ),
        }
        if event_type == "FAIL" and error is not None:
            facets["errorMessage"] = error_message_run.ErrorMessageRunFacet(
                message=str(error),
                programmingLanguage="python",
                stackTrace="".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                ),
                producer=self.producer,
            )
        return facets

    def _build_pipeline_job_facets(self, ctx: Ctx) -> dict[str, Any]:
        return {
            "datajuicerPipeline": DataJuicerPipelineJobFacet(
                producer=self.producer,
                projectName=ctx.project_name,
                executorType=ctx.executor_type,
                configPath=ConfigAccessor.get(ctx.extra, "config_path", None),
                numOperators=ConfigAccessor.get(ctx.extra, "num_operators", None),
                recipeHash=ConfigAccessor.get(ctx.extra, "recipe_hash", None),
                recipe=str(ConfigAccessor.get(ctx.extra, "recipe", None)),
                operatorNames=ConfigAccessor.get(ctx.extra, "operator_names", []),
                dag=ConfigAccessor.get(ctx.extra, "dag", {}),
            )
        }

    def _build_operator_run_facets(
        self,
        ctx: Ctx,
        op_ctx: OpCtx,
        event_type: str,
        error: Exception | None,
    ) -> dict[str, Any]:
        from openlineage.client.facet_v2 import (
            error_message_run,
            parent_run,
            processing_engine_run,
        )

        facets: dict[str, Any] = {
            "parent": parent_run.ParentRunFacet(
                run=parent_run.Run(runId=ctx.run_id),
                job=parent_run.Job(
                    namespace=self._job_namespace(ctx),
                    name=self._pipeline_job_name(ctx),
                ),
                root=parent_run.Root(
                    run=parent_run.RootRun(runId=ctx.run_id),
                    job=parent_run.RootJob(
                        namespace=self._job_namespace(ctx),
                        name=self._pipeline_job_name(ctx),
                    ),
                    producer=self.producer,
                ),
                producer=self.producer,
            ),
            "datajuicer": DataJuicerRunFacet(
                producer=self.producer,
                jobId=ctx.job_id,
                executorType=ctx.executor_type,
                status=op_ctx.status,
                durationSeconds=self._op_duration(op_ctx),
                errorMessage=str(error) if error else None,
                workDir=ConfigAccessor.get(ctx.extra, "work_dir", None),
                custom={
                    "op_id": op_ctx.op_id,
                    "op_name": op_ctx.op_name,
                    "op_type": op_ctx.op_type,
                    "op_index": op_ctx.op_index,
                    "partition_id": op_ctx.partition_id,
                    "metrics": op_ctx.metrics,
                },
            ),
            "processing_engine": processing_engine_run.ProcessingEngineRunFacet(
                name="data-juicer",
                version=__version__,
                openlineageAdapterVersion=__version__,
                producer=self.producer,
            ),
        }
        if event_type == "FAIL" and error is not None:
            facets["errorMessage"] = error_message_run.ErrorMessageRunFacet(
                message=str(error),
                programmingLanguage="python",
                stackTrace="".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                ),
                producer=self.producer,
            )
        return facets

    def _build_operator_job_facets(self, ctx: Ctx, op_ctx: OpCtx) -> dict[str, Any]:
        facets = {
            "datajuicerOperator": DataJuicerOperatorJobFacet(
                producer=self.producer,
                projectName=ctx.project_name,
                executorType=ctx.executor_type,
                configPath=ConfigAccessor.get(ctx.extra, "config_path", None),
                opName=op_ctx.op_name,
                opType=op_ctx.op_type,
                opIndex=op_ctx.op_index,
                recipeHash=ConfigAccessor.get(op_ctx.extra, "op_config_hash", None),
                recipe=str(ConfigAccessor.get(op_ctx.extra, "op_args", {})),
                code=self._build_code_version(op_ctx),
            )
        }

        source_location_facet = self._build_source_code_location_facet(op_ctx)
        if source_location_facet is not None:
            facets["sourceCodeLocation"] = source_location_facet
        return facets

    def _build_code_version(self, op_ctx: OpCtx) -> DataJuicerCodeVersion | None:
        source_info = ConfigAccessor.get(op_ctx.extra, "source", {}) or {}
        if not source_info:
            return None
        return DataJuicerCodeVersion(
            repoOwner=ConfigAccessor.get(source_info, "repo_owner", None),
            repoUrl=ConfigAccessor.get(source_info, "repo_url", None),
            relativePath=ConfigAccessor.get(source_info, "relative_path", None),
            commit=ConfigAccessor.get(source_info, "git_commit", None),
            tag=ConfigAccessor.get(source_info, "git_tag", None),
            branch=ConfigAccessor.get(source_info, "git_branch", None),
            dirty=ConfigAccessor.get(source_info, "dirty", None),
            packageVersion=ConfigAccessor.get(source_info, "package_version", None),
            authorName=ConfigAccessor.get(source_info, "git_author_name", None),
            authorEmail=ConfigAccessor.get(source_info, "git_author_email", None),
            committerName=ConfigAccessor.get(source_info, "git_committer_name", None),
            committerEmail=ConfigAccessor.get(source_info, "git_committer_email", None),
        )

    def _build_source_code_location_facet(self, op_ctx: OpCtx) -> Any:
        from openlineage.client.facet_v2 import source_code_location_job

        source_info = ConfigAccessor.get(op_ctx.extra, "source", {}) or {}
        file_path = ConfigAccessor.get(source_info, "file_path", None)
        if not file_path:
            return None

        location_type = (
            "git" if ConfigAccessor.get(source_info, "git_commit", None) else "file"
        )
        return source_code_location_job.SourceCodeLocationJobFacet(
            type=location_type,
            url=f"file://{file_path}",
            repoUrl=ConfigAccessor.get(source_info, "repo_url", None),
            path=ConfigAccessor.get(source_info, "relative_path", None),
            version=ConfigAccessor.get(source_info, "git_commit", None),
            tag=ConfigAccessor.get(source_info, "git_tag", None),
            branch=ConfigAccessor.get(source_info, "git_branch", None),
            producer=self.producer,
        )

    def _build_input_dataset(
        self, ref: DatasetRef, snapshot: DatasetSnapshot | None
    ) -> Any:
        from openlineage.client.event_v2 import InputDataset

        return InputDataset(
            namespace=ref.namespace,
            name=ref.name,
            facets=self._build_dataset_facets(ref, snapshot),
        )

    def _build_output_dataset(
        self, ref: DatasetRef, snapshot: DatasetSnapshot | None
    ) -> Any:
        from openlineage.client.event_v2 import OutputDataset

        return OutputDataset(
            namespace=ref.namespace,
            name=ref.name,
            facets=self._build_dataset_facets(ref, snapshot),
            outputFacets=self._build_output_dataset_facets(snapshot),
        )

    def _build_dataset_facets(
        self, ref: DatasetRef, snapshot: DatasetSnapshot | None
    ) -> dict[str, Any]:
        from openlineage.client.facet_v2 import (
            dataset_type_dataset,
            datasource_dataset,
            schema_dataset,
            storage_dataset,
        )

        facets: dict[str, Any] = {
            "dataSource": datasource_dataset.DatasourceDatasetFacet(
                name=ref.source_type,
                uri=ref.uri,
                producer=self.producer,
            ),
            "datasetType": dataset_type_dataset.DatasetTypeDatasetFacet(
                datasetType="TABLE" if ref.source_type == "iceberg" else "FILES",
                subType=ref.source_type,
                producer=self.producer,
            ),
            "storage": storage_dataset.StorageDatasetFacet(
                storageLayer=ref.source_type,
                fileFormat=self._infer_file_format(ref),
                producer=self.producer,
            ),
        }
        if snapshot and snapshot.schema:
            facets["schema"] = schema_dataset.SchemaDatasetFacet(
                fields=[self._to_ol_schema_field(field) for field in snapshot.schema],
                producer=self.producer,
            )
        return facets

    def _build_output_dataset_facets(
        self, snapshot: DatasetSnapshot | None
    ) -> dict[str, Any]:
        from openlineage.client.facet_v2 import output_statistics_output_dataset

        if snapshot is None or snapshot.rows is None:
            return {}
        return {
            "outputStatistics": output_statistics_output_dataset.OutputStatisticsOutputDatasetFacet(
                rowCount=snapshot.rows,
                producer=self.producer,
            )
        }

    def _to_ol_schema_field(self, field: SchemaField) -> Any:
        from openlineage.client.facet_v2 import schema_dataset

        return schema_dataset.SchemaDatasetFacetFields(
            name=field.name,
            type=field.type,
            fields=(
                [self._to_ol_schema_field(child) for child in field.fields]
                if field.fields
                else None
            ),
        )

    @staticmethod
    def _infer_file_format(ref: DatasetRef) -> str | None:
        if ref.uri and "." in ref.uri.rsplit("/", 1)[-1]:
            return ref.uri.rsplit(".", 1)[-1]
        return None

    @staticmethod
    def _snapshot_refs(snapshot: DatasetSnapshot | None) -> list[DatasetRef]:
        if snapshot is None:
            return []
        return snapshot.refs or []

    def _job_namespace(self, ctx: Ctx) -> str:
        return ConfigAccessor.get(self.provider_cfg, "namespace", None) or ctx.namespace

    @staticmethod
    def _pipeline_job_name(ctx: Ctx) -> str:
        return ctx.job_name

    @staticmethod
    def _operator_job_name(ctx: Ctx, op_ctx: OpCtx) -> str:
        base = f"{ctx.job_name}.{op_ctx.op_index:03d}.{op_ctx.op_name}"
        if op_ctx.partition_id != 0:
            return f"{base}.partition_{op_ctx.partition_id:04d}"
        return base

    @staticmethod
    def _operator_run_id(ctx: Ctx, op_ctx: OpCtx) -> str:
        seed = f"{ctx.run_id}:{op_ctx.partition_id}:{op_ctx.op_index}:{op_ctx.op_name}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    @staticmethod
    def _run_state(event_type: str) -> Any:
        from openlineage.client.event_v2 import RunState

        mapping = {
            "START": RunState.START,
            "COMPLETE": RunState.COMPLETE,
            "FAIL": RunState.FAIL,
        }
        return mapping[event_type]

    @staticmethod
    def _ctx_duration(ctx: Ctx) -> float | None:
        if not ctx.started_at or not ctx.ended_at:
            return None
        from datetime import datetime

        try:
            return max(
                0.0,
                (
                    datetime.fromisoformat(ctx.ended_at)
                    - datetime.fromisoformat(ctx.started_at)
                ).total_seconds(),
            )
        except Exception:
            return None

    @staticmethod
    def _op_duration(op_ctx: OpCtx) -> float | None:
        if op_ctx.metrics and op_ctx.metrics.get("duration_seconds") is not None:
            return float(op_ctx.metrics["duration_seconds"])
        if not op_ctx.started_at or not op_ctx.ended_at:
            return None
        from datetime import datetime

        try:
            return max(
                0.0,
                (
                    datetime.fromisoformat(op_ctx.ended_at)
                    - datetime.fromisoformat(op_ctx.started_at)
                ).total_seconds(),
            )
        except Exception:
            return None
