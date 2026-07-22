# ============================================================
# SalesOS AI — Workflow Engine
#
# CRITICAL ARCHITECTURAL BOUNDARY:
#
#   Business workflows are DETERMINISTIC.
#   AI reasoning happens INSIDE agents.
#   LangGraph orchestrates AI, not business logic.
#
# Execution path:
#   FastAPI → Workflow Engine → Decision Engine → LangGraph → Agent → Tool → Event Bus
#
# Workflows are configuration-driven. An admin can modify
# workflow behavior without redeploying the application.
# ============================================================

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.workflow import WorkflowInstance

logger = get_logger("workflow_engine")


# ── Workflow Types ──────────────────────────────────────────


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"  # Waiting for external event (e.g., customer reply)


class WorkflowStatus(StrEnum):
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Step Definition ─────────────────────────────────────────


StepHandler = Callable[["WorkflowContext"], Coroutine[Any, Any, "StepResult"]]


@dataclass
class StepResult:
    """Result from executing a workflow step."""

    status: StepStatus = StepStatus.COMPLETED
    data: dict[str, Any] = field(default_factory=dict)
    next_step: str | None = None  # Override the default next step
    error: str | None = None
    wait_for_event: str | None = None  # Event type to wait for before resuming


@dataclass
class StepDefinition:
    """A single step in a workflow definition."""

    name: str
    handler: StepHandler
    next_step: str | None = None  # Default next step (None = end)
    condition: str | None = None  # Optional condition expression
    on_error: str | None = None  # Step to jump to on error
    timeout_seconds: int = 300  # Max execution time
    retries: int = 0  # Number of retry attempts


# ── Workflow Context ────────────────────────────────────────


@dataclass
class WorkflowContext:
    """Mutable context passed through all steps of a workflow.

    Steps read input from and write output to this context.
    The context is persisted as JSONB in the workflow_instances table.
    """

    workflow_id: UUID
    workflow_type: str
    organization_id: UUID
    lead_id: UUID | None = None

    # Accumulated state from previous steps
    state: dict[str, Any] = field(default_factory=dict)

    # Current step info
    current_step: str = ""
    step_history: list[str] = field(default_factory=list)

    # Session for DB operations (not serialized)
    session: AsyncSession | None = field(default=None, repr=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the workflow state."""
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the workflow state."""
        self.state[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Serialize context for persistence (excludes session)."""
        return {
            "workflow_id": str(self.workflow_id),
            "workflow_type": self.workflow_type,
            "organization_id": str(self.organization_id),
            "lead_id": str(self.lead_id) if self.lead_id else None,
            "state": self.state,
            "current_step": self.current_step,
            "step_history": self.step_history,
        }


# ── Workflow Definition ─────────────────────────────────────


@dataclass
class WorkflowDefinition:
    """A complete workflow definition with ordered steps.

    Workflows are defined declaratively and registered with the engine.
    An admin can override step order and conditions per-organization.
    """

    name: str
    workflow_type: str
    description: str = ""
    steps: dict[str, StepDefinition] = field(default_factory=dict)
    initial_step: str = ""

    def add_step(
        self,
        name: str,
        handler: StepHandler,
        *,
        next_step: str | None = None,
        condition: str | None = None,
        on_error: str | None = None,
        timeout_seconds: int = 300,
        retries: int = 0,
    ) -> "WorkflowDefinition":
        """Add a step to the workflow. Returns self for chaining."""
        self.steps[name] = StepDefinition(
            name=name,
            handler=handler,
            next_step=next_step,
            condition=condition,
            on_error=on_error,
            timeout_seconds=timeout_seconds,
            retries=retries,
        )
        if not self.initial_step:
            self.initial_step = name
        return self


# ── Workflow Engine ─────────────────────────────────────────


class WorkflowEngine:
    """Deterministic workflow execution engine.

    Responsibilities:
    - Execute workflows step by step
    - Persist state between steps
    - Handle errors and retries
    - Support pause/resume for async operations
    - Coordinate with the Decision Engine and LangGraph

    This engine does NOT:
    - Make AI decisions (that's the Decision Engine + LangGraph)
    - Call LLMs directly (that's the agents)
    - Contain business logic (that's the services)
    """

    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._definitions[definition.workflow_type] = definition
        logger.info(
            "workflow_registered",
            type=definition.workflow_type,
            steps=list(definition.steps.keys()),
        )

    async def start(
        self,
        session: AsyncSession,
        workflow_type: str,
        *,
        organization_id: UUID,
        lead_id: UUID | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        """Start a new workflow instance."""
        definition = self._definitions.get(workflow_type)
        if not definition:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # Create persistence record
        instance = WorkflowInstance(
            organization_id=organization_id,
            workflow_type=workflow_type,
            lead_id=lead_id,
            status=WorkflowStatus.RUNNING,
            current_step=definition.initial_step,
            state=initial_state or {},
        )
        session.add(instance)
        await session.flush()

        # Build context
        context = WorkflowContext(
            workflow_id=instance.id,
            workflow_type=workflow_type,
            organization_id=organization_id,
            lead_id=lead_id,
            state=initial_state or {},
            current_step=definition.initial_step,
            session=session,
        )

        logger.info(
            "workflow_started",
            workflow_id=str(instance.id),
            type=workflow_type,
            initial_step=definition.initial_step,
        )

        # Execute steps
        await self._execute(session, instance, definition, context)

        return instance

    async def resume(
        self,
        session: AsyncSession,
        workflow_id: UUID,
        *,
        event_data: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        """Resume a paused workflow (e.g., after receiving a customer reply)."""
        instance = await session.get(WorkflowInstance, workflow_id)
        if not instance:
            raise ValueError(f"Workflow {workflow_id} not found")

        if instance.status != WorkflowStatus.WAITING:
            raise ValueError(f"Workflow {workflow_id} is not in waiting state")

        definition = self._definitions.get(instance.workflow_type)
        if not definition:
            raise ValueError(f"Unknown workflow type: {instance.workflow_type}")

        # Rebuild context from persisted state
        context = WorkflowContext(
            workflow_id=instance.id,
            workflow_type=instance.workflow_type,
            organization_id=instance.organization_id,
            lead_id=instance.lead_id,
            state=instance.state,
            current_step=instance.current_step or "",
            session=session,
        )

        # Inject event data
        if event_data:
            context.set("resume_event_data", event_data)

        instance.status = WorkflowStatus.RUNNING
        await session.flush()

        logger.info(
            "workflow_resumed",
            workflow_id=str(workflow_id),
            step=instance.current_step,
        )

        await self._execute(session, instance, definition, context)
        return instance

    async def _execute(
        self,
        session: AsyncSession,
        instance: WorkflowInstance,
        definition: WorkflowDefinition,
        context: WorkflowContext,
    ) -> None:
        """Execute workflow steps sequentially until completion, error, or wait."""
        current_step_name = context.current_step

        while current_step_name:
            step_def = definition.steps.get(current_step_name)
            if not step_def:
                logger.error("step_not_found", step=current_step_name)
                instance.status = WorkflowStatus.FAILED
                instance.error_message = f"Step '{current_step_name}' not found"
                break

            context.current_step = current_step_name
            context.step_history.append(current_step_name)

            logger.info(
                "step_executing",
                workflow_id=str(instance.id),
                step=current_step_name,
            )

            try:
                # Execute the step handler
                result = await step_def.handler(context)

                if result.status == StepStatus.WAITING:
                    # Pause workflow — will be resumed when event arrives
                    instance.status = WorkflowStatus.WAITING
                    instance.current_step = result.next_step or step_def.next_step
                    instance.state = context.state
                    await session.flush()

                    logger.info(
                        "workflow_paused",
                        workflow_id=str(instance.id),
                        waiting_for=result.wait_for_event,
                    )
                    return

                elif result.status == StepStatus.FAILED:
                    if step_def.on_error:
                        current_step_name = step_def.on_error
                        continue
                    instance.status = WorkflowStatus.FAILED
                    instance.error_message = result.error
                    break

                elif result.status == StepStatus.SKIPPED:
                    current_step_name = result.next_step or step_def.next_step
                    continue

                # Step completed — merge result data into context
                context.state.update(result.data)

                # Determine next step
                current_step_name = result.next_step or step_def.next_step

            except Exception as e:
                logger.error(
                    "step_failed",
                    workflow_id=str(instance.id),
                    step=current_step_name,
                    error=str(e),
                )
                if step_def.on_error:
                    current_step_name = step_def.on_error
                else:
                    instance.status = WorkflowStatus.FAILED
                    instance.error_message = str(e)
                    break

        # Workflow completed (no more steps)
        if instance.status == WorkflowStatus.RUNNING:
            instance.status = WorkflowStatus.COMPLETED
            instance.completed_at = datetime.now(UTC)

        instance.current_step = current_step_name
        instance.state = context.state
        await session.flush()

        logger.info(
            "workflow_finished",
            workflow_id=str(instance.id),
            status=instance.status,
            steps_executed=len(context.step_history),
        )

    def list_workflows(self) -> dict[str, list[str]]:
        """List all registered workflows and their steps."""
        return {wf_type: list(wf_def.steps.keys()) for wf_type, wf_def in self._definitions.items()}


# ── Global Instance ─────────────────────────────────────────

_engine = WorkflowEngine()


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine."""
    return _engine
