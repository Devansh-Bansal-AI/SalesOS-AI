# ============================================================
# SalesOS AI — Unit Tests: Plugin Registries
# Tests AgentRegistry, PromptRegistry, and ToolRegistry registration and lookup.
# ============================================================

import pytest

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.tools import ToolRegistry
from app.agents.tools.calendar import SalesOSCalendarProvider
from app.agents.tools.company_research import SalesOSCompanyResearchProvider
from app.agents.tools.postgres_crm import PostgresCRMProvider
from app.agents.tools.qdrant_kb import QdrantKnowledgeBaseProvider
from app.prompts.registry import PromptRegistry


def test_agent_registry():
    """Test registering and retrieving agents from AgentRegistry."""
    registry = AgentRegistry()

    class TestDummyAgent(BaseAgent):
        name = "dummy_agent"
        description = "Dummy test agent"

        async def _execute(self, input_data, context):
            return {"status": "ok"}

    registry.register("dummy_agent", TestDummyAgent, description="Dummy test agent")
    assert registry.is_registered("dummy_agent") is True

    retrieved_cls = registry.get_class("dummy_agent")
    assert retrieved_cls == TestDummyAgent

    list_agents = registry.list_agents()
    assert len(list_agents) == 1
    assert list_agents[0].agent_type == "dummy_agent"


def test_prompt_registry():
    """Test storing and rendering versioned prompt templates."""
    registry = PromptRegistry()
    registry.register(
        name="qualification",
        version="v1",
        system_prompt="You are an AI assistant for {company}.",
        user_prompt_template="Analyze lead {email}.",
    )

    system, user = registry.get("qualification", "v1")
    assert "company" in system
    assert "email" in user


def test_tool_registry():
    """Test registering concrete MCP Tool Providers."""
    registry = ToolRegistry()

    crm_provider = PostgresCRMProvider()
    kb_provider = QdrantKnowledgeBaseProvider()
    research_provider = SalesOSCompanyResearchProvider()
    calendar_provider = SalesOSCalendarProvider()

    registry.register_crm(crm_provider)
    registry.register_knowledge_base(kb_provider)
    registry.register_company_research(research_provider)
    registry.register_calendar(calendar_provider)

    assert registry.get_crm() == crm_provider
    assert registry.get_knowledge_base() == kb_provider
    assert registry.get_company_research() == research_provider
    assert registry.get_calendar() == calendar_provider
