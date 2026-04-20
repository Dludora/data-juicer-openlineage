from __future__ import annotations

from typing import Any

from data_juicer.core.metadata.models import Ctx, OpCtx
from data_juicer.core.metadata.provider import MetadataProvider
from data_juicer_openlineage.builder import OpenLineageBuilder
from data_juicer_openlineage.transport import OpenLineageTransport


class OpenLineageProvider(MetadataProvider):
    name = "openlineage"

    def __init__(
        self,
        executor: Any,
        cfg: Any,
        executor_type: str,
        provider_cfg: dict[str, Any] | None = None,
        builder: OpenLineageBuilder | None = None,
        transport: OpenLineageTransport | None = None,
    ):
        super().__init__(executor, cfg, executor_type, provider_cfg)
        self.builder = builder or OpenLineageBuilder(self.provider_cfg)
        self.transport = transport or OpenLineageTransport(self.provider_cfg)

    def is_enabled(self) -> bool:
        return bool(self.transport.enabled)

    def on_pipeline_started(self, ctx: Ctx) -> None:
        self.transport.emit(self.builder.build_pipeline_event(ctx, "START"))

    def on_pipeline_completed(self, ctx: Ctx) -> None:
        self.transport.emit(self.builder.build_pipeline_event(ctx, "COMPLETE"))

    def on_pipeline_failed(self, ctx: Ctx, error: Exception) -> None:
        self.transport.emit(self.builder.build_pipeline_event(ctx, "FAIL", error=error))

    def on_operator_started(self, ctx: Ctx, op_ctx: OpCtx) -> None:
        self.transport.emit(self.builder.build_operator_event(ctx, op_ctx, "START"))

    def on_operator_completed(self, ctx: Ctx, op_ctx: OpCtx) -> None:
        self.transport.emit(self.builder.build_operator_event(ctx, op_ctx, "COMPLETE"))

    def on_operator_failed(self, ctx: Ctx, op_ctx: OpCtx, error: Exception) -> None:
        self.transport.emit(self.builder.build_operator_event(ctx, op_ctx, "FAIL", error=error))
