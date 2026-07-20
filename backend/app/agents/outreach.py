# ============================================================
# SalesOS AI — Outreach Agent
#
# Generates personalized outreach emails using lead enrichment
# data, qualification context, and conversation starters.
# ============================================================

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.integrations.llm.base import LLMConfig, LLMMessage
from app.prompts.outreach_v1 import (
    OUTREACH_SYSTEM_PROMPT,
    OUTREACH_USER_PROMPT,
)

# ── Typed I/O ───────────────────────────────────────────────


class OutreachInput(BaseModel):
    """Input to the Outreach Agent."""
    email: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company_name: str | None = None

    # Qualification
    score: int | None = None
    intent: str | None = None
    urgency: str | None = None

    # Enrichment
    industry: str | None = None
    employee_range: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    conversation_starters: list[str] = Field(default_factory=list)

    # Context
    template_type: str = "warm_lead"  # hot_lead, warm_lead, cold_lead, follow_up
    additional_context: str = ""


class OutreachOutput(BaseModel):
    """Generated outreach email."""
    subject: str = Field(..., max_length=100)
    body_text: str
    body_html: str | None = None
    reasoning: str | None = None
    confidence: float = Field(..., ge=0, le=1)


# ── Agent ───────────────────────────────────────────────────


class OutreachAgent(BaseAgent[OutreachInput, OutreachOutput]):
    """Generates personalized outreach emails.

    Uses enrichment data and qualification context for personalization.
    Emails follow strict style guide: 80-150 words, value-first, specific CTA.
    """

    agent_type = "outreach"

    async def execute(self, input_data: OutreachInput) -> OutreachOutput:
        """Generate a personalized outreach email."""

        # Retrieve conversation context if available
        additional_context = input_data.additional_context
        try:
            kb = self.tools.get_knowledge_base()
            memories = await kb.search(
                query=f"{input_data.company_name} {input_data.job_title}",
                namespace=f"lead:{input_data.email}",
                limit=3,
            )
            if memories:
                additional_context += "\n\nStored context:\n" + "\n".join(
                    f"- {m.get('text', '')}" for m in memories
                )
        except RuntimeError:
            pass

        user_prompt = OUTREACH_USER_PROMPT.format(
            first_name=input_data.first_name or "there",
            last_name=input_data.last_name or "",
            email=input_data.email,
            job_title=input_data.job_title or "Professional",
            company_name=input_data.company_name or "your company",
            score=input_data.score or "N/A",
            intent=input_data.intent or "general",
            urgency=input_data.urgency or "unknown",
            industry=input_data.industry or "Unknown",
            employee_range=input_data.employee_range or "Unknown",
            pain_points="\n".join(
                f"- {p}" for p in input_data.pain_points
            ) if input_data.pain_points else "Not identified",
            conversation_starters="\n".join(
                f"- {c}" for c in input_data.conversation_starters
            ) if input_data.conversation_starters else "None available",
            template_type=input_data.template_type,
            additional_context=additional_context or "None",
        )

        messages = [
            LLMMessage(role="system", content=OUTREACH_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        config = LLMConfig(
            temperature=0.7,   # Higher creativity for email writing
            max_tokens=1000,
            response_format="json",
        )

        output, response = await self.llm.generate_structured(
            messages, OutreachOutput, config
        )

        return output
