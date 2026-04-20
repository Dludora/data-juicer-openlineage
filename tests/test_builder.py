import unittest

from data_juicer.core.metadata.models import Ctx, DatasetRef, DatasetSnapshot, OpCtx, SchemaField
from data_juicer_openlineage.builder import OpenLineageBuilder


class TestOpenLineageBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = OpenLineageBuilder({"namespace": "ol.demo", "producer": "https://producer.example/dj"})
        self.input_snapshot = DatasetSnapshot(
            refs=[
                DatasetRef(
                    namespace="s3://bucket",
                    name="raw/input.jsonl",
                    role="input",
                    source_type="s3",
                    uri="s3://bucket/raw/input.jsonl",
                )
            ],
            rows=10,
            schema=[SchemaField(name="text", type="string")],
            storage_kind="s3",
        )
        self.output_snapshot = DatasetSnapshot(
            refs=[
                DatasetRef(
                    namespace="inmemory://run-1",
                    name="partition_0_op_000_clean_output",
                    role="output",
                    source_type="inmemory",
                    uri="inmemory://run-1/partition_0_op_000_clean_output",
                )
            ],
            rows=8,
            schema=[SchemaField(name="meta", type="struct", fields=[SchemaField(name="lang", type="string")])],
            storage_kind="inmemory",
        )
        self.ctx = Ctx(
            run_id="c8408d80-6ef5-4a80-9736-a79c70ecb4d0",
            job_id="job-1",
            executor_type="default",
            job_name="demo_job",
            namespace="data_juicer.default",
            project_name="demo_project",
            started_at="2026-04-20T01:00:00+00:00",
            ended_at="2026-04-20T01:00:03+00:00",
            input_snapshot=self.input_snapshot,
            output_snapshot=self.output_snapshot,
            extra={
                "recipe": {
                    "project_name": "demo_project",
                    "process": [{"clean_text": {"text_key": "text"}}],
                    "metadata": {"enabled": True},
                },
                "recipe_hash": "recipe-hash",
                "num_operators": 1,
                "operator_names": ["clean_text"],
                "work_dir": "/tmp/dj",
                "config_path": "/tmp/config.yaml",
                "dag": {"enabled": True},
            },
        )
        self.op_ctx = OpCtx(
            op_id="0:000:clean_text",
            op_name="clean_text",
            op_type="mapper",
            op_index=0,
            partition_id=2,
            started_at="2026-04-20T01:00:01+00:00",
            ended_at="2026-04-20T01:00:02+00:00",
            input_snapshot=self.input_snapshot,
            output_snapshot=self.output_snapshot,
            metrics={"duration_seconds": 1.0},
            extra={
                "op_args": {"text_key": "text"},
                "op_config_hash": "op-hash",
                "dag": {"node_id": "n1"},
                "source": {
                    "file_path": "/repo/data_juicer/ops/mapper/clean_text.py",
                    "relative_path": "data_juicer/ops/mapper/clean_text.py",
                    "repo_url": "https://github.com/datajuicer/data-juicer.git",
                    "repo_owner": "datajuicer",
                    "git_commit": "abcdef1234567890",
                    "git_tag": "v1.5.1",
                    "git_branch": "main",
                    "git_author_name": "Alice",
                    "git_author_email": "alice@example.com",
                    "git_committer_name": "Bob",
                    "git_committer_email": "bob@example.com",
                    "dirty": False,
                },
            },
        )

    def test_build_pipeline_event_includes_dataset_and_custom_facets(self):
        event = self.builder.build_pipeline_event(self.ctx, "COMPLETE")

        self.assertEqual(event.eventType.value, "COMPLETE")
        self.assertEqual(event.job.namespace, "ol.demo")
        self.assertEqual(event.job.name, "demo_job")
        self.assertEqual(event.run.runId, self.ctx.run_id)
        self.assertEqual(event.inputs[0].facets["datasetType"].datasetType, "FILES")
        self.assertEqual(event.outputs[0].facets["datasetType"].subType, "inmemory")
        self.assertEqual(event.outputs[0].outputFacets["outputStatistics"].rowCount, 8)
        self.assertEqual(event.outputs[0].facets["schema"].fields[0].fields[0].name, "lang")
        self.assertEqual(event.job.facets["datajuicerPipeline"].projectName, "demo_project")
        self.assertEqual(event.job.facets["datajuicerPipeline"].recipeHash, "recipe-hash")
        self.assertEqual(event.job.facets["datajuicerPipeline"].recipe["project_name"], "demo_project")
        self.assertEqual(event.job.facets["datajuicerPipeline"].operatorNames, ["clean_text"])
        self.assertEqual(event.run.facets["datajuicer"].executorType, "default")

    def test_build_operator_event_adds_parent_facet_and_deterministic_run_id(self):
        event = self.builder.build_operator_event(self.ctx, self.op_ctx, "START")

        self.assertEqual(event.job.name, "demo_job.000.clean_text.partition_0002")
        self.assertEqual(event.run.facets["parent"].run.runId, self.ctx.run_id)
        self.assertEqual(event.run.facets["parent"].job.name, "demo_job")
        self.assertEqual(event.producer, "https://producer.example/dj")
        self.assertRegex(event.run.runId, r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        self.assertEqual(event.job.facets["datajuicerOperator"].opName, "clean_text")
        self.assertEqual(event.job.facets["datajuicerOperator"].opType, "mapper")
        self.assertEqual(event.job.facets["datajuicerOperator"].opIndex, 0)
        self.assertEqual(event.job.facets["datajuicerOperator"].recipeHash, "op-hash")
        self.assertEqual(event.job.facets["datajuicerOperator"].recipe, [{"clean_text": {"text_key": "text"}}])
        self.assertEqual(event.job.facets["datajuicerOperator"].code.repoOwner, "datajuicer")
        self.assertEqual(event.job.facets["datajuicerOperator"].code.commit, "abcdef1234567890")
        self.assertEqual(event.job.facets["datajuicerOperator"].code.branch, "main")
        self.assertEqual(event.job.facets["datajuicerOperator"].code.authorName, "Alice")
        self.assertEqual(event.job.facets["datajuicerOperator"].code.authorEmail, "alice@example.com")
        self.assertEqual(event.job.facets["datajuicerOperator"].code.committerName, "Bob")
        self.assertEqual(event.job.facets["datajuicerOperator"].code.committerEmail, "bob@example.com")
        self.assertEqual(event.job.facets["datajuicerOperator"].code.repoUrl, "https://github.com/datajuicer/data-juicer.git")
        self.assertEqual(event.job.facets["sourceCodeLocation"].version, "abcdef1234567890")
        self.assertEqual(event.job.facets["sourceCodeLocation"].path, "data_juicer/ops/mapper/clean_text.py")

    def test_fail_event_adds_error_facet(self):
        event = self.builder.build_operator_event(self.ctx, self.op_ctx, "FAIL", error=RuntimeError("boom"))

        self.assertEqual(event.eventType.value, "FAIL")
        self.assertEqual(event.run.facets["errorMessage"].message, "boom")
        self.assertEqual(event.run.facets["errorMessage"].programmingLanguage, "python")


if __name__ == "__main__":
    unittest.main()
