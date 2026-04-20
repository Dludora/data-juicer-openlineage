import unittest
from unittest.mock import MagicMock, patch

from data_juicer_openlineage.transport import OpenLineageTransport, build_openlineage_client_config


class TestOpenLineageTransport(unittest.TestCase):
    def test_passthrough_transport_config(self):
        config = build_openlineage_client_config(
            {
                "transport": {
                    "type": "composite",
                    "transports": {
                        "primary": {"type": "console"},
                        "secondary": {"type": "http", "url": "http://localhost:5000"},
                    },
                }
            }
        )
        self.assertEqual(config["transport"]["type"], "composite")
        self.assertIn("primary", config["transport"]["transports"])

    def test_build_http_shortcut_config(self):
        config = build_openlineage_client_config(
            {
                "transport_type": "http",
                "url": "http://localhost:5000",
                "endpoint": "api/v1/lineage",
                "api_key": "secret",
                "timeout": 3.5,
                "verify": False,
                "retry_count": 2,
                "retry_backoff_seconds": 0.5,
            }
        )
        self.assertEqual(config["transport"]["type"], "http")
        self.assertEqual(config["transport"]["auth"]["apiKey"], "secret")
        self.assertEqual(config["transport"]["retry"]["total"], 2)
        self.assertEqual(config["transport"]["retry"]["backoff_factor"], 0.5)

    def test_transport_uses_openlineage_client_and_emits(self):
        with patch("openlineage.client.OpenLineageClient") as client_cls:
            client = MagicMock()
            client_cls.return_value = client
            transport = OpenLineageTransport({"transport": {"type": "console"}})
            event = object()
            transport.emit(event)

            client_cls.assert_called_once_with(config={"transport": {"type": "console"}})
            client.emit.assert_called_once_with(event)
            self.assertTrue(transport.enabled)

    def test_emit_is_swallowed_when_fail_silently(self):
        with patch("openlineage.client.OpenLineageClient") as client_cls:
            client = MagicMock()
            client.emit.side_effect = RuntimeError("boom")
            client_cls.return_value = client
            transport = OpenLineageTransport({"transport": {"type": "console"}, "fail_silently": True})
            transport.emit(object())
            self.assertTrue(transport.enabled)

    def test_describe_event_extracts_basic_identity(self):
        transport = OpenLineageTransport.__new__(OpenLineageTransport)
        event = type(
            "Event",
            (),
            {
                "eventType": type("EventType", (), {"value": "COMPLETE"})(),
                "job": type("Job", (), {"namespace": "ns", "name": "job"})(),
                "run": type("Run", (), {"runId": "run-1"})(),
            },
        )()

        self.assertEqual(
            transport._describe_event(event),
            "COMPLETE | ns | job | run-1",
        )


if __name__ == "__main__":
    unittest.main()
