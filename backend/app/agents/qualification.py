# ============================================================
# SalesOS AI — Qualification Agent
#
# First AI agent. Uses the LLM provider abstraction.
# Receives typed input, returns typed output.
# Never touches the database directly.
#
# Execution path:
#   Workflow Engine → Decision Engine → QualificationAgent
#   Agent uses: self.llm (provider abstraction)
#                self.tools.get_crm() (MCP tool)
# ============================================================

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.integrations.llm.base import LLMConfig, LLMMessage
from app.prompts.qualification_v1 import (
    QUALIFICATION_SYSTEM_PROMPT,
    QUALIFICATION_USER_PROMPT,
)

# ── Typed I/O ───────────────────────────────────────────────


class QualificationInput(BaseModel):
    """Input to the Qualification Agent."""

    email: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    source: str = "website"
    message: str | None = None
    additional_context: str = ""


class QualificationOutput(BaseModel):
    """Structured output from the Qualification Agent."""

    score: int = Field(..., ge=0, le=100)
    priority: str = Field(..., pattern="^(critical|high|medium|low|none)$")
    intent: str = Field(
        ...,
        pattern="^(demo_request|pricing|evaluation|partnership|general|support|spam)$",
    )
    urgency: str = Field(
        ...,
        pattern="^(immediate|this_week|this_month|this_quarter|exploring|unknown)$",
    )
    summary: str
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str | None = None
    talking_points: list[str] = Field(default_factory=list)


# ── Agent ───────────────────────────────────────────────────


class QualificationAgent(BaseAgent[QualificationInput, QualificationOutput]):
    """Analyzes inbound leads and produces qualification assessments.

    Uses:
    - self.llm.generate_structured() for LLM reasoning
    - self.tools.get_crm() (optional) for interaction history
    """

    agent_type = "qualification"

    async def execute(self, input_data: QualificationInput) -> QualificationOutput:
        """Run qualification analysis on a lead."""

        # Optional: Check CRM for existing interaction history
        additional_context = input_data.additional_context
        try:
            crm = self.tools.get_crm()
            history = await crm.get_interaction_history(input_data.email)
            if history:
                additional_context += (
                    f"\n\nExisting interaction history ({len(history)} records):\n"
                    + "\n".join(
                        f"- {h.get('type', 'unknown')}: {h.get('summary', '')}" for h in history[:5]
                    )
                )
        except RuntimeError:
            # CRM tool not registered yet — that's OK
            pass

        # Build prompt
        user_prompt = QUALIFICATION_USER_PROMPT.format(
            email=input_data.email,
            first_name=input_data.first_name or "Unknown",
            last_name=input_data.last_name or "",
            job_title=input_data.job_title or "Not provided",
            company_name=input_data.company_name or "Not provided",
            source=input_data.source,
            message=input_data.message or "No message provided",
            additional_context=additional_context or "None",
        )

        messages = [
            LLMMessage(role="system", content=QUALIFICATION_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        # Call LLM via provider abstraction
        config = LLMConfig(
            temperature=0.2,  # Low temperature for consistency
            max_tokens=1024,
            response_format="json",
        )

        output, response = await self.llm.generate_structured(messages, QualificationOutput, config)

        # Update agent run with LLM costs
        # (BaseAgent tracks these via the telemetry event)

        return output
