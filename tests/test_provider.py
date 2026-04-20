import unittest

from data_juicer.core.metadata.models import Ctx, DatasetSnapshot, OpCtx
from data_juicer_openlineage.builder import OpenLineageBuilder
from data_juicer_openlineage.provider import OpenLineageProvider


class RecordingTransport:
    def __init__(self):
        self.enabled = True
        self.events = []

    def emit(self, event):
        self.events.append(event)


class TestOpenLineageProvider(unittest.TestCase):
    def setUp(self):
        self.transport = RecordingTransport()
        self.provider = OpenLineageProvider(
            executor=None,
            cfg={},
            executor_type="default",
            provider_cfg={"namespace": "ol.demo", "producer": "https://producer.example/dj"},
            builder=OpenLineageBuilder({"namespace": "ol.demo", "producer": "https://producer.example/dj"}),
            transport=self.transport,
        )
        self.ctx = Ctx(
            run_id="97d82a03-73fc-4448-9580-cb6a8cbdf117",
            job_id=None,
            executor_type="default",
            job_name="demo_job",
            namespace="data_juicer.default",
            project_name="demo",
            started_at="2026-04-20T01:00:00+00:00",
            ended_at="2026-04-20T01:00:03+00:00",
            input_snapshot=DatasetSnapshot(),
            output_snapshot=DatasetSnapshot(),
            extra={"recipe": {"process": []}, "recipe_hash": "abc", "num_operators": 2},
        )
        self.op_ctx = OpCtx(
            op_id="0:001:normalize",
            op_name="normalize",
            op_type="mapper",
            op_index=1,
            started_at="2026-04-20T01:00:01+00:00",
            ended_at="2026-04-20T01:00:02+00:00",
            input_snapshot=DatasetSnapshot(),
            output_snapshot=DatasetSnapshot(),
            extra={"op_args": {}, "op_config_hash": "h1"},
        )

    def test_provider_emits_pipeline_and_operator_events(self):
        self.provider.on_pipeline_started(self.ctx)
        self.provider.on_operator_completed(self.ctx, self.op_ctx)
        self.provider.on_pipeline_failed(self.ctx, RuntimeError("broken"))

        self.assertEqual([event.eventType.value for event in self.transport.events], ["START", "COMPLETE", "FAIL"])
        self.assertEqual(self.transport.events[0].job.name, "demo_job")
        self.assertEqual(self.transport.events[1].job.name, "demo_job.001.normalize")
        self.assertEqual(self.transport.events[2].run.facets["errorMessage"].message, "broken")


if __name__ == "__main__":
    unittest.main()
