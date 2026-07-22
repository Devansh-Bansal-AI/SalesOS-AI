# ============================================================
# SalesOS AI — Base Agent (v2)
#
# Architectural role of agents:
#   FastAPI → Workflow Engine → Decision Engine → LangGraph → Agent → Tool
#
# Agents:
# - Receive typed input (Pydantic)
# - Return typed output (Pydantic)
# - Use LLM via the provider abstraction (never directly)
# - Access tools via MCP tool registry (never import implementations)
# - Emit structured telemetry for every execution
# - Never touch the database directly
# ============================================================

import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import ToolRegistry, get_tool_registry
from app.core.logging import get_logger
from app.core.telemetry import TelemetryEvent, get_telemetry
from app.integrations.llm import get_llm_provider
from app.integrations.llm.base import LLMConfig, LLMProvider, LLMResponse
from app.models.agent_run import AgentRun

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

logger = get_logger("agent")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Abstract base class that all AI agents must implement.

    Provides:
    - LLM provider abstraction (llm.generate / llm.generate_structured)
    - MCP tool registry access (self.tools)
    - Automatic AgentRun record creation and completion
    - Structured telemetry emission
    - Error handling and retry support

    Usage:
        class QualificationAgent(BaseAgent[QualificationInput, QualificationOutput]):
            agent_type = "qualification"

            async def execute(self, input_data: QualificationInput) -> QualificationOutput:
                # Use self.llm for LLM calls
                response = await self.llm.generate([...])

                # Use self.tools for MCP tool access
                existing = await self.tools.get_crm().find_contact(input_data.email)

                return QualificationOutput(...)
    """

    agent_type: str = "base"

    def __init__(
        self,
        session: AsyncSession,
        organization_id: UUID,
        *,
        llm_provider: str | None = None,
        llm_config: LLMConfig | None = None,
    ):
        self.session = session
        self.organization_id = organization_id
        self.llm: LLMProvider = get_llm_provider(llm_provider)
        self.llm_config = llm_config or LLMConfig()
        self.tools: ToolRegistry = get_tool_registry()
        self._telemetry = get_telemetry()

    async def run(
        self,
        input_data: InputT,
        *,
        lead_id: UUID | None = None,
        workflow_id: UUID | None = None,
        request_id: str = "",
    ) -> tuple[OutputT, AgentRun]:
        """Execute the agent with full lifecycle management.

        Returns:
            Tuple of (agent output, agent run record)
        """
        # Create agent run record
        agent_run = AgentRun(
            organization_id=self.organization_id,
            agent_type=self.agent_type,
            lead_id=lead_id,
            workflow_id=workflow_id,
            status="running",
            input_data=input_data.model_dump(),
            started_at=datetime.now(UTC),
        )
        self.session.add(agent_run)
        await self.session.flush()

        # Telemetry tracking
        telemetry_event = TelemetryEvent(
            request_id=request_id,
            workflow_id=str(workflow_id) if workflow_id else "",
            agent_run_id=str(agent_run.id),
            agent_type=self.agent_type,
            organization_id=str(self.organization_id),
            lead_id=str(lead_id) if lead_id else "",
        )

        start_time = time.perf_counter()

        # Bind context variables for RAG/CRM/other tools
        from app.agents.tools import current_org_id, current_session

        token_org = current_org_id.set(self.organization_id)
        token_session = current_session.set(self.session)

        try:
            # Execute agent logic (implemented by subclasses)
            output = await self.execute(input_data)

            # Update run record
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            agent_run.status = "completed"
            agent_run.output_data = output.model_dump()
            agent_run.completed_at = datetime.now(UTC)
            agent_run.duration_ms = duration_ms
            agent_run.confidence = getattr(output, "confidence", None)
            agent_run.model_used = self.llm.provider_name

            await self.session.flush()

            # Emit telemetry
            telemetry_event.success = True
            telemetry_event.latency_ms = duration_ms
            telemetry_event.confidence = agent_run.confidence
            telemetry_event.llm_provider = self.llm.provider_name
            self._telemetry.emit(telemetry_event)

            logger.info(
                "agent_completed",
                agent_type=self.agent_type,
                agent_run_id=str(agent_run.id),
                duration_ms=duration_ms,
                confidence=agent_run.confidence,
                provider=self.llm.provider_name,
            )

            return output, agent_run

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            agent_run.status = "failed"
            agent_run.error_message = str(e)
            agent_run.completed_at = datetime.now(UTC)
            agent_run.duration_ms = duration_ms
            await self.session.flush()

            # Emit failure telemetry
            telemetry_event.success = False
            telemetry_event.error = str(e)
            telemetry_event.latency_ms = duration_ms
            self._telemetry.emit(telemetry_event)

            logger.error(
                "agent_failed",
                agent_type=self.agent_type,
                agent_run_id=str(agent_run.id),
                error=str(e),
            )
            raise
        finally:
            current_org_id.reset(token_org)
            current_session.reset(token_session)

    def _update_telemetry_from_response(
        self, telemetry: TelemetryEvent, response: LLMResponse
    ) -> None:
        """Helper to update telemetry with LLM response data."""
        telemetry.llm_provider = response.provider
        telemetry.llm_model = response.model
        telemetry.prompt_tokens += response.prompt_tokens
        telemetry.completion_tokens += response.completion_tokens
        telemetry.total_tokens += response.total_tokens
        telemetry.estimated_cost_usd += response.estimated_cost

    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """Implement agent-specific logic. Subclasses must override this.

        Use:
        - self.llm.generate([...]) for text generation
        - self.llm.generate_structured([...], OutputSchema) for structured output
        - self.tools.get_crm() for CRM operations
        - self.tools.get_company_research() for enrichment
        - etc.
        """
        ...
