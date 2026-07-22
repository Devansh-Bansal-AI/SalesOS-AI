# ============================================================
# SalesOS AI — Booking Agent
#
# Determines optimal meeting setup:
#   Type, duration, title, description, preferred time window.
# Uses lead qualification, enrichment, and conversation context.
# ============================================================

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.integrations.llm.base import LLMConfig, LLMMessage
from app.prompts.booking_v1 import BOOKING_SYSTEM_PROMPT, BOOKING_USER_PROMPT

# ── Typed I/O ───────────────────────────────────────────────


class BookingInput(BaseModel):
    """Input to the Booking Agent."""

    email: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company_name: str | None = None

    # Qualification
    score: int | None = None
    intent: str | None = None
    urgency: str | None = None
    priority: str | None = None

    # Conversation context
    objections: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    customer_stage: str = "awareness"
    conversation_summary: str = ""

    # Calendar
    timezone: str = "UTC"
    available_slots: str = "Not provided"


class BookingOutput(BaseModel):
    """Recommended meeting setup."""

    meeting_type: str = Field(..., pattern="^(discovery|demo|follow_up|onboarding|custom)$")
    duration_minutes: int = Field(..., ge=15, le=120)
    title: str = Field(..., max_length=200)
    description: str
    preferred_time_window: str | None = None
    timezone: str = "UTC"
    reasoning: str | None = None
    confidence: float = Field(..., ge=0, le=1)


# ── Agent ───────────────────────────────────────────────────


class BookingAgent(BaseAgent[BookingInput, BookingOutput]):
    """Determines optimal meeting setup for qualified leads.

    Uses qualification data, conversation context, and availability
    to recommend meeting type, duration, title, and time window.
    """

    agent_type = "booking"

    async def execute(self, input_data: BookingInput) -> BookingOutput:
        """Generate meeting recommendation."""

        # Try to get conversation context from memory
        conversation_summary = input_data.conversation_summary
        try:
            kb = self.tools.get_knowledge_base()
            memories = await kb.search(
                query=f"{input_data.company_name} meeting",
                namespace=f"lead:{input_data.email}",
                limit=3,
            )
            if memories:
                conversation_summary += "\n\nStored context:\n" + "\n".join(
                    f"- {m.get('text', '')}" for m in memories
                )
        except RuntimeError:
            pass

        user_prompt = BOOKING_USER_PROMPT.format(
            first_name=input_data.first_name or "Unknown",
            last_name=input_data.last_name or "",
            email=input_data.email,
            job_title=input_data.job_title or "Unknown",
            company_name=input_data.company_name or "Unknown",
            score=input_data.score or "N/A",
            intent=input_data.intent or "general",
            urgency=input_data.urgency or "unknown",
            priority=input_data.priority or "N/A",
            objections=", ".join(input_data.objections) if input_data.objections else "None",
            buying_signals=", ".join(input_data.buying_signals)
            if input_data.buying_signals
            else "None",
            customer_stage=input_data.customer_stage,
            conversation_summary=conversation_summary or "No prior conversation",
            timezone=input_data.timezone,
            available_slots=input_data.available_slots,
        )

        messages = [
            LLMMessage(role="system", content=BOOKING_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        config = LLMConfig(
            temperature=0.3,
            max_tokens=800,
            response_format="json",
        )

        output, response = await self.llm.generate_structured(messages, BookingOutput, config)

        return output
