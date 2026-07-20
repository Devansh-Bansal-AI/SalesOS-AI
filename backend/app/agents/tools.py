# ============================================================
# SalesOS AI — MCP Tool Providers
#
# Agent tools are formalized as typed interfaces.
# Each agent declares which tool providers it needs.
# Tool providers are injected, not imported.
#
# This keeps agents independent from implementation details.
# The CRM MCP doesn't know if data comes from PostgreSQL,
# HubSpot, or Salesforce.
# ============================================================

import contextvars
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

current_org_id = contextvars.ContextVar("current_org_id", default=None)
current_session = contextvars.ContextVar("current_session", default=None)


# ── CRM Tool Provider ──────────────────────────────────────


@dataclass
class CRMContact:
    """Contact record from any CRM source."""
    id: str
    email: str
    name: str | None = None
    company: str | None = None
    status: str | None = None
    last_contacted: str | None = None
    metadata: dict[str, Any] | None = None


class CRMToolProvider(ABC):
    """Tools for CRM operations. Used by Qualification and CRM agents."""

    @abstractmethod
    async def find_contact(self, email: str) -> CRMContact | None:
        """Look up an existing contact by email."""
        ...

    @abstractmethod
    async def create_contact(self, data: dict[str, Any]) -> CRMContact:
        """Create a new CRM contact."""
        ...

    @abstractmethod
    async def update_contact(self, id: str, data: dict[str, Any]) -> CRMContact:
        """Update an existing CRM contact."""
        ...

    @abstractmethod
    async def get_interaction_history(self, email: str) -> list[dict[str, Any]]:
        """Get interaction history for a contact."""
        ...


# ── Company Research Tool Provider ──────────────────────────


@dataclass
class CompanyInfo:
    """Enriched company information from any research source."""
    name: str
    domain: str | None = None
    industry: str | None = None
    employee_range: str | None = None
    description: str | None = None
    location: str | None = None
    tech_stack: list[str] | None = None
    annual_revenue: str | None = None
    linkedin_url: str | None = None
    confidence: float = 0.0


class CompanyResearchToolProvider(ABC):
    """Tools for company enrichment. Used by Enrichment Agent."""

    @abstractmethod
    async def research_by_domain(self, domain: str) -> CompanyInfo | None:
        """Research a company by its domain."""
        ...

    @abstractmethod
    async def research_by_name(self, name: str) -> CompanyInfo | None:
        """Research a company by its name."""
        ...

    @abstractmethod
    async def detect_tech_stack(self, domain: str) -> list[str]:
        """Detect technology stack from a domain."""
        ...

    def capabilities(self) -> dict[str, bool]:
        """Return provider capabilities (e.g. firmographics, technographics, revenue)."""
        return {
            "firmographics": True,
            "technographics": True,
            "revenue": True,
            "employees": True,
        }



# ── Calendar Tool Provider ──────────────────────────────────


class CalendarToolProvider(ABC):
    """Tools for calendar operations. Used by Booking Agent."""

    @abstractmethod
    async def get_available_slots(
        self,
        host_email: str,
        start_date: str,
        end_date: str,
        duration_minutes: int = 30,
        timezone: str = "UTC",
    ) -> list[dict[str, str]]:
        """Get available meeting slots for a host."""
        ...

    @abstractmethod
    async def create_meeting(
        self,
        host_email: str,
        attendee_email: str,
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a calendar meeting."""
        ...

    @abstractmethod
    async def cancel_meeting(self, event_id: str) -> bool:
        """Cancel a calendar meeting."""
        ...


# ── Email Tool Provider ─────────────────────────────────────


class EmailToolProvider(ABC):
    """Tools for email operations. Used by Outreach and Follow-up Agents."""

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        from_email: str | None = None,
    ) -> dict[str, Any]:
        """Send an email."""
        ...

    @abstractmethod
    async def get_delivery_status(self, message_id: str) -> str:
        """Check email delivery status."""
        ...


# ── Policy Tool Provider ────────────────────────────────────


@dataclass
class PolicyRule:
    """A business policy rule."""
    name: str
    condition: str
    action: str
    priority: int = 0
    enabled: bool = True


class PolicyToolProvider(ABC):
    """Tools for business policy evaluation. Used by Decision Engine."""

    @abstractmethod
    async def get_rules(self, organization_id: str) -> list[PolicyRule]:
        """Get active business rules for an organization."""
        ...

    @abstractmethod
    async def evaluate_rule(
        self, rule: PolicyRule, context: dict[str, Any]
    ) -> bool:
        """Evaluate a single rule against a context."""
        ...

    @abstractmethod
    async def get_confidence_threshold(self, organization_id: str) -> float:
        """Get the minimum confidence threshold for auto-actions."""
        ...


# ── Knowledge Base Tool Provider ────────────────────────────


class KnowledgeBaseToolProvider(ABC):
    """Tools for RAG / knowledge retrieval. Used by Outreach and Conversation Agents."""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        organization_id: str | None = None,
        namespace: str | None = None,
        limit: int | None = None,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over the knowledge base."""
        ...

    @abstractmethod
    async def get_similar_conversations(
        self,
        text: str,
        top_k: int = 3,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar past conversations."""
        ...

    @abstractmethod
    async def store(
        self,
        text: str,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Store a text entry in the knowledge base."""
        ...

    @abstractmethod
    async def delete(
        self,
        point_id: str,
        collection_name: str | None = None,
    ) -> bool:
        """Delete a vector entry by ID from the knowledge base."""
        ...



# ── Tool Registry ──────────────────────────────────────────


class ToolRegistry:
    """Central registry for MCP tool providers.

    Usage:
        registry = ToolRegistry()
        registry.register_crm(PostgresCRMProvider(session))
        registry.register_company_research(WebSearchProvider())

        # Agents get their tools from the registry
        crm = registry.get_crm()
        company = registry.get_company_research()
    """

    def __init__(self) -> None:
        self._crm: CRMToolProvider | None = None
        self._company_research: CompanyResearchToolProvider | None = None
        self._calendar: CalendarToolProvider | None = None
        self._email: EmailToolProvider | None = None
        self._policy: PolicyToolProvider | None = None
        self._knowledge_base: KnowledgeBaseToolProvider | None = None

    def register_crm(self, provider: CRMToolProvider) -> None:
        self._crm = provider

    def register_company_research(self, provider: CompanyResearchToolProvider) -> None:
        self._company_research = provider

    def register_calendar(self, provider: CalendarToolProvider) -> None:
        self._calendar = provider

    def register_email(self, provider: EmailToolProvider) -> None:
        self._email = provider

    def register_policy(self, provider: PolicyToolProvider) -> None:
        self._policy = provider

    def register_knowledge_base(self, provider: KnowledgeBaseToolProvider) -> None:
        self._knowledge_base = provider

    def get_crm(self) -> CRMToolProvider:
        if not self._crm:
            raise RuntimeError("CRM tool provider not registered")
        return self._crm

    def get_company_research(self) -> CompanyResearchToolProvider:
        if not self._company_research:
            raise RuntimeError("Company research tool provider not registered")
        return self._company_research

    def get_calendar(self) -> CalendarToolProvider:
        if not self._calendar:
            raise RuntimeError("Calendar tool provider not registered")
        return self._calendar

    def get_email(self) -> EmailToolProvider:
        if not self._email:
            raise RuntimeError("Email tool provider not registered")
        return self._email

    def get_policy(self) -> PolicyToolProvider:
        if not self._policy:
            raise RuntimeError("Policy tool provider not registered")
        return self._policy

    def get_knowledge_base(self) -> KnowledgeBaseToolProvider:
        if not self._knowledge_base:
            raise RuntimeError("Knowledge base tool provider not registered")
        return self._knowledge_base


# ── Global Instance ─────────────────────────────────────────

_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global MCP tool registry."""
    return _tool_registry
