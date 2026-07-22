# ============================================================
# SalesOS AI — Enrichment Agent
#
# Researches companies and leads to produce enriched context.
# Uses MCP tool providers for company research — never calls
# external APIs directly.
# ============================================================

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.integrations.llm.base import LLMConfig, LLMMessage
from app.prompts.enrichment_v1 import (
    ENRICHMENT_SYSTEM_PROMPT,
    ENRICHMENT_USER_PROMPT,
)

# ── Typed I/O ───────────────────────────────────────────────


class EnrichmentInput(BaseModel):
    """Input to the Enrichment Agent."""

    email: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    linkedin_url: str | None = None
    domain: str | None = None
    # Prior qualification data
    score: int | None = None
    intent: str | None = None
    urgency: str | None = None


class CompanyProfile(BaseModel):
    """Enriched company data."""

    name: str
    industry: str | None = None
    sub_industry: str | None = None
    employee_range: str | None = None
    annual_revenue: str | None = None
    headquarters: str | None = None
    description: str | None = None
    key_products: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)


class LeadContext(BaseModel):
    """Enriched lead context."""

    seniority_level: str | None = None
    department: str | None = None
    decision_authority: str | None = None
    likely_pain_points: list[str] = Field(default_factory=list)


class EnrichmentOutput(BaseModel):
    """Structured output from the Enrichment Agent."""

    company_profile: CompanyProfile
    lead_context: LeadContext
    conversation_starters: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    data_sources_used: list[str] = Field(default_factory=list)


# ── Agent ───────────────────────────────────────────────────


class EnrichmentAgent(BaseAgent[EnrichmentInput, EnrichmentOutput]):
    """Researches companies and leads for enriched sales context.

    Uses:
    - self.tools.get_company_research() for company data
    - self.llm.generate_structured() for synthesis
    """

    agent_type = "enrichment"

    async def execute(self, input_data: EnrichmentInput) -> EnrichmentOutput:
        """Run enrichment analysis on a lead."""

        # Phase 1: Gather research data from MCP tools
        research_data = await self._gather_research(input_data)

        # Phase 2: Synthesize with LLM
        domain = input_data.domain or self._extract_domain(input_data.email)

        user_prompt = ENRICHMENT_USER_PROMPT.format(
            email=input_data.email,
            first_name=input_data.first_name or "Unknown",
            last_name=input_data.last_name or "",
            job_title=input_data.job_title or "Not provided",
            company_name=input_data.company_name or "Not provided",
            domain=domain or "Unknown",
            linkedin_url=input_data.linkedin_url or "Not provided",
            score=input_data.score or "N/A",
            intent=input_data.intent or "N/A",
            urgency=input_data.urgency or "N/A",
            research_data=research_data or "No research data available",
        )

        messages = [
            LLMMessage(role="system", content=ENRICHMENT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        config = LLMConfig(
            temperature=0.3,
            max_tokens=1500,
            response_format="json",
        )

        output, response = await self.llm.generate_structured(messages, EnrichmentOutput, config)

        return output

    async def _gather_research(self, input_data: EnrichmentInput) -> str:
        """Use MCP tool providers to gather research data."""
        research_parts = []
        data_sources = []

        # Try company research tool
        try:
            company_tool = self.tools.get_company_research()
            domain = input_data.domain or self._extract_domain(input_data.email)

            if domain:
                company_info = await company_tool.research_by_domain(domain)
                if company_info:
                    research_parts.append(
                        f"Company Research (domain: {domain}):\n"
                        f"  Industry: {company_info.industry}\n"
                        f"  Employees: {company_info.employee_range}\n"
                        f"  Description: {company_info.description}\n"
                        f"  Location: {company_info.location}"
                    )
                    data_sources.append("company_research")

                # Try tech stack detection
                tech_stack = await company_tool.detect_tech_stack(domain)
                if tech_stack:
                    research_parts.append(f"Tech Stack: {', '.join(tech_stack)}")
                    data_sources.append("tech_stack_detection")

            elif input_data.company_name:
                company_info = await company_tool.research_by_name(input_data.company_name)
                if company_info:
                    research_parts.append(
                        f"Company Research (name: {input_data.company_name}):\n"
                        f"  Industry: {company_info.industry}\n"
                        f"  Employees: {company_info.employee_range}\n"
                        f"  Description: {company_info.description}"
                    )
                    data_sources.append("company_research")

        except RuntimeError:
            # Company research tool not registered yet
            research_parts.append("Company research tool not available")

        return "\n\n".join(research_parts) if research_parts else ""

    def _extract_domain(self, email: str) -> str | None:
        try:
            domain = email.split("@")[1].lower()
            # Skip common personal email domains
            personal_domains = {
                "gmail.com",
                "yahoo.com",
                "hotmail.com",
                "outlook.com",
                "aol.com",
                "icloud.com",
            }
            return None if domain in personal_domains else domain
        except (IndexError, AttributeError):
            return None
