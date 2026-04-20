from __future__ import annotations

from typing import Any

from loguru import logger

from data_juicer.utils.config_utils import ConfigAccessor


class OpenLineageTransport:
    def __init__(self, provider_cfg: dict[str, Any] | None = None):
        self.provider_cfg = provider_cfg or {}
        self.client = None
        self.enabled = False
        self.fail_silently = bool(ConfigAccessor.get(self.provider_cfg, "fail_silently", True))
        self.strict_sdk = bool(ConfigAccessor.get(self.provider_cfg, "strict_sdk", False))
        self.client_config = None
        self._initialize()

    def _initialize(self) -> None:
        try:
            from openlineage.client import OpenLineageClient
        except Exception as e:
            if self.strict_sdk:
                raise RuntimeError("OpenLineage SDK is required but unavailable") from e
            logger.warning(f"OpenLineage SDK not available, provider disabled: {e}")
            self.enabled = False
            return

        self.client_config = build_openlineage_client_config(self.provider_cfg)
        try:
            self.client = OpenLineageClient(config=self.client_config)
            self.enabled = True
        except Exception as e:
            if self.fail_silently:
                logger.warning(f"Failed to initialize OpenLineage client, provider disabled: {e}")
                self.enabled = False
                return
            raise

    def emit(self, event: Any) -> None:
        if not self.enabled or self.client is None:
            return

        try:
            self.client.emit(event)
        except Exception as e:
            event_desc = self._describe_event(event)
            if self.fail_silently:
                logger.warning(f"OpenLineage emit failed and was ignored for [{event_desc}]: {e}")
                return
            raise RuntimeError(f"Failed to emit OpenLineage event for [{event_desc}]") from e

    @staticmethod
    def _describe_event(event: Any) -> str:
        try:
            event_type = getattr(getattr(event, "eventType", None), "value", None) or getattr(event, "eventType", None)
            job = getattr(event, "job", None)
            run = getattr(event, "run", None)
            job_ns = getattr(job, "namespace", None)
            job_name = getattr(job, "name", None)
            run_id = getattr(run, "runId", None)
            parts = [str(part) for part in [event_type, job_ns, job_name, run_id] if part]
            return " | ".join(parts) if parts else type(event).__name__
        except Exception:
            return type(event).__name__


def build_openlineage_client_config(provider_cfg: dict[str, Any] | None = None) -> dict[str, Any] | None:
    provider_cfg = provider_cfg or {}
    transport_cfg = ConfigAccessor.get(provider_cfg, "transport", None)
    if transport_cfg:
        return {"transport": transport_cfg}

    shortcut = _build_legacy_http_transport_config(provider_cfg)
    if shortcut is not None:
        return {"transport": shortcut}

    return None


def _build_legacy_http_transport_config(provider_cfg: dict[str, Any]) -> dict[str, Any] | None:
    transport_type = ConfigAccessor.get(provider_cfg, "transport_type", None)
    endpoint = ConfigAccessor.get(provider_cfg, "endpoint", None)
    url = ConfigAccessor.get(provider_cfg, "url", None)
    timeout = ConfigAccessor.get(provider_cfg, "timeout", None)
    api_key = ConfigAccessor.get(provider_cfg, "api_key", None)
    verify = ConfigAccessor.get(provider_cfg, "verify", None)
    retry_count = ConfigAccessor.get(provider_cfg, "retry_count", None)
    retry_backoff_seconds = ConfigAccessor.get(provider_cfg, "retry_backoff_seconds", None)

    if not any(
        value is not None
        for value in [transport_type, endpoint, url, timeout, api_key, verify, retry_count, retry_backoff_seconds]
    ):
        return None

    config: dict[str, Any] = {
        "type": transport_type or "http",
    }
    if url is not None:
        config["url"] = url
    if endpoint is not None:
        config["endpoint"] = endpoint
    if timeout is not None:
        config["timeout"] = float(timeout)
    if verify is not None:
        config["verify"] = bool(verify)
    if api_key:
        config["auth"] = {"type": "api_key", "apiKey": api_key}

    retry: dict[str, Any] = {}
    if retry_count is not None:
        retry["total"] = int(retry_count)
    if retry_backoff_seconds is not None:
        retry["backoff_factor"] = float(retry_backoff_seconds)
    if retry:
        config["retry"] = retry

    return config
