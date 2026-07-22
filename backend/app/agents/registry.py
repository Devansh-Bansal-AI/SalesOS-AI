# ============================================================
# SalesOS AI — Agent Registry
#
# Agents as plugins. New agents register themselves instead
# of being hardcoded into services or workflows.
#
# Registry pattern:
#   1. Agent classes register via @register_agent decorator
#   2. Workflows resolve agents by type name
#   3. New agents become plugins — zero core changes
# ============================================================

from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger("agent_registry")


class AgentRegistration(BaseModel):
    """Metadata about a registered agent."""

    agent_type: str
    agent_class_name: str
    module_path: str
    description: str = ""
    version: str = "1.0"
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None


class AgentRegistry:
    """Central registry for all AI agents.

    Usage:
        # Register (typically via decorator):
        registry.register("qualification", QualificationAgent)

        # Resolve + execute:
        agent = registry.create("qualification", session, org_id)
        output, run = await agent.run(input_data, lead_id=lead_id)

        # List all:
        agents = registry.list_agents()
    """

    def __init__(self):
        self._agents: dict[str, type] = {}
        self._metadata: dict[str, AgentRegistration] = {}

    def register(
        self,
        agent_type: str,
        agent_class: type,
        *,
        description: str = "",
        version: str = "1.0",
    ) -> None:
        """Register an agent class by type name."""
        self._agents[agent_type] = agent_class
        self._metadata[agent_type] = AgentRegistration(
            agent_type=agent_type,
            agent_class_name=agent_class.__name__,
            module_path=f"{agent_class.__module__}.{agent_class.__name__}",
            description=description or agent_class.__doc__ or "",
            version=version,
            input_schema=self._extract_schema(agent_class, "Input"),
            output_schema=self._extract_schema(agent_class, "Output"),
        )
        logger.info(
            "agent_registered",
            agent_type=agent_type,
            class_name=agent_class.__name__,
            version=version,
        )

    def create(
        self,
        agent_type: str,
        session: AsyncSession,
        organization_id: Any,
        **kwargs,
    ):
        """Create an agent instance by type name.

        Returns:
            An instance of the registered agent class.

        Raises:
            KeyError: If agent_type is not registered.
        """
        if agent_type not in self._agents:
            available = ", ".join(sorted(self._agents.keys()))
            raise KeyError(f"Agent '{agent_type}' not registered. Available: {available}")

        agent_class = self._agents[agent_type]
        return agent_class(session, organization_id, **kwargs)

    def get_class(self, agent_type: str) -> type:
        """Get the agent class without instantiation."""
        if agent_type not in self._agents:
            raise KeyError(f"Agent '{agent_type}' not registered")
        return self._agents[agent_type]

    def list_agents(self) -> list[AgentRegistration]:
        """List all registered agents with metadata."""
        return list(self._metadata.values())

    def is_registered(self, agent_type: str) -> bool:
        """Check if an agent type is registered."""
        return agent_type in self._agents

    def get_metadata(self, agent_type: str) -> AgentRegistration | None:
        """Get metadata for a registered agent."""
        return self._metadata.get(agent_type)

    def _extract_schema(self, agent_class: type, suffix: str) -> dict | None:
        """Try to extract Pydantic schema from agent's generic type params."""
        try:
            # Look for InputT/OutputT in the agent's __orig_bases__
            for base in getattr(agent_class, "__orig_bases__", []):
                args = getattr(base, "__args__", ())
                for arg in args:
                    if (
                        isinstance(arg, type)
                        and issubclass(arg, BaseModel)
                        and arg.__name__.endswith(suffix)
                    ):
                        return arg.model_json_schema()
        except Exception:
            pass
        return None


# ── Global singleton ────────────────────────────────────────

_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry."""
    return _registry


def register_agent(
    agent_type: str | None = None,
    *,
    description: str = "",
    version: str = "1.0",
):
    """Decorator to register an agent class.

    Usage:
        @register_agent("qualification", description="Qualifies leads")
        class QualificationAgent(BaseAgent[QualificationInput, QualificationOutput]):
            ...
    """

    def decorator(cls):
        name = agent_type or getattr(cls, "agent_type", cls.__name__.lower())
        _registry.register(name, cls, description=description, version=version)
        return cls

    return decorator


def register_all_agents() -> None:
    """Import and register all built-in agents.

    Called at application startup.
    """
    # Import triggers @register_agent decorators
    from app.agents.booking import BookingAgent
    from app.agents.conversation_intelligence import ConversationIntelligenceAgent
    from app.agents.enrichment import EnrichmentAgent
    from app.agents.outreach import OutreachAgent
    from app.agents.qualification import QualificationAgent

    # Register agents that don't use the decorator
    if not _registry.is_registered("qualification"):
        _registry.register(
            "qualification",
            QualificationAgent,
            description="Scores and qualifies inbound leads",
        )
    if not _registry.is_registered("enrichment"):
        _registry.register(
            "enrichment",
            EnrichmentAgent,
            description="Enriches leads with company and contact data",
        )
    if not _registry.is_registered("conversation_intelligence"):
        _registry.register(
            "conversation_intelligence",
            ConversationIntelligenceAgent,
            description="9-dimension conversation analysis with memory",
        )
    if not _registry.is_registered("outreach"):
        _registry.register(
            "outreach",
            OutreachAgent,
            description="Generates personalized outreach emails",
        )
    if not _registry.is_registered("booking"):
        _registry.register(
            "booking",
            BookingAgent,
            description="Determines optimal meeting setup",
        )

    logger.info(
        "all_agents_registered",
        count=len(_registry.list_agents()),
        types=[a.agent_type for a in _registry.list_agents()],
    )
