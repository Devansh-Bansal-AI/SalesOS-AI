# ============================================================
# SalesOS AI — Telemetry & Observability
#
# Every agent execution emits structured telemetry.
# This is the single source of truth for debugging,
# cost analysis, and performance optimization.
#
# Telemetry events flow to:
#   1. Structured logs (always)
#   2. Prometheus metrics (always)
#   3. OpenTelemetry spans (when configured)
# ============================================================

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger("telemetry")


# ── Telemetry Event ─────────────────────────────────────────


@dataclass
class TelemetryEvent:
    """Structured telemetry event emitted by every agent execution."""
    # Identifiers
    request_id: str = ""
    workflow_id: str = ""
    agent_run_id: str = ""

    # Agent Info
    agent_type: str = ""
    organization_id: str = ""
    lead_id: str = ""

    # LLM
    llm_provider: str = ""
    llm_model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Performance
    latency_ms: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0

    # Result
    success: bool = True
    error: str | None = None
    confidence: float | None = None

    # Custom dimensions
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Telemetry Emitter ───────────────────────────────────────


class TelemetryEmitter:
    """Central telemetry emitter that sends structured events to all sinks."""

    def __init__(self) -> None:
        self._enabled = True

    def emit(self, event: TelemetryEvent) -> None:
        """Emit a telemetry event to all configured sinks."""
        if not self._enabled:
            return

        # Sink 1: Structured log (always)
        log_data = {
            "request_id": event.request_id,
            "workflow_id": event.workflow_id,
            "agent_run_id": event.agent_run_id,
            "agent_type": event.agent_type,
            "organization_id": event.organization_id,
            "lead_id": event.lead_id,
            "llm_provider": event.llm_provider,
            "llm_model": event.llm_model,
            "prompt_tokens": event.prompt_tokens,
            "completion_tokens": event.completion_tokens,
            "total_tokens": event.total_tokens,
            "estimated_cost_usd": event.estimated_cost_usd,
            "latency_ms": event.latency_ms,
            "success": event.success,
            "confidence": event.confidence,
        }

        if event.error:
            log_data["error"] = event.error

        if event.success:
            logger.info("agent_telemetry", **log_data)
        else:
            logger.error("agent_telemetry", **log_data)

        # Sink 2: Prometheus metrics
        self._emit_prometheus(event)

    def _emit_prometheus(self, event: TelemetryEvent) -> None:
        """Update Prometheus counters/histograms."""
        try:
            from prometheus_client import Counter, Histogram

            # Agent execution counter
            agent_counter = Counter(
                "salesos_agent_executions_total",
                "Total agent executions",
                ["agent_type", "success", "organization_id"],
            )
            agent_counter.labels(
                agent_type=event.agent_type,
                success=str(event.success),
                organization_id=event.organization_id,
            ).inc()

            # Agent latency histogram
            agent_latency = Histogram(
                "salesos_agent_latency_ms",
                "Agent execution latency in milliseconds",
                ["agent_type"],
                buckets=[50, 100, 250, 500, 1000, 2500, 5000, 10000],
            )
            agent_latency.labels(agent_type=event.agent_type).observe(event.latency_ms)

            # Token usage counter
            token_counter = Counter(
                "salesos_llm_tokens_total",
                "Total LLM tokens used",
                ["agent_type", "llm_provider", "token_type"],
            )
            token_counter.labels(
                agent_type=event.agent_type,
                llm_provider=event.llm_provider,
                token_type="prompt",
            ).inc(event.prompt_tokens)
            token_counter.labels(
                agent_type=event.agent_type,
                llm_provider=event.llm_provider,
                token_type="completion",
            ).inc(event.completion_tokens)

            # Cost counter
            cost_counter = Counter(
                "salesos_llm_cost_usd_total",
                "Total estimated LLM cost in USD",
                ["agent_type", "llm_provider"],
            )
            cost_counter.labels(
                agent_type=event.agent_type,
                llm_provider=event.llm_provider,
            ).inc(event.estimated_cost_usd)

        except Exception:
            pass  # Prometheus not available — degrade gracefully

    @asynccontextmanager
    async def track(
        self,
        agent_type: str,
        *,
        organization_id: str = "",
        lead_id: str = "",
        request_id: str = "",
        workflow_id: str = "",
    ):
        """Context manager that automatically tracks agent execution telemetry.

        Usage:
            async with telemetry.track("qualification", organization_id="...") as event:
                result = await llm.generate(...)
                event.prompt_tokens = result.prompt_tokens
                event.completion_tokens = result.completion_tokens
                event.llm_provider = result.provider
                event.llm_model = result.model
                event.confidence = 0.92
        """
        event = TelemetryEvent(
            request_id=request_id or str(uuid4()),
            workflow_id=workflow_id,
            agent_run_id=str(uuid4()),
            agent_type=agent_type,
            organization_id=organization_id,
            lead_id=lead_id,
            started_at=time.perf_counter(),
        )

        try:
            yield event
            event.success = True
        except Exception as e:
            event.success = False
            event.error = str(e)
            raise
        finally:
            event.completed_at = time.perf_counter()
            event.latency_ms = int(
                (event.completed_at - event.started_at) * 1000
            )
            self.emit(event)


# ── Global Instance ─────────────────────────────────────────

_telemetry = TelemetryEmitter()


def get_telemetry() -> TelemetryEmitter:
    """Get the global telemetry emitter."""
    return _telemetry
