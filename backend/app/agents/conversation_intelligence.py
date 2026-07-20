# ============================================================
# SalesOS AI — Conversation Intelligence Agent
#
# Enterprise-grade message analysis with 9 dimensions:
#   Intent, Sentiment, Buying Signals, Objections,
#   Competitor Mentions, Risk, Customer Stage,
#   Next Best Action, Memory Update
#
# After analysis:
#   1. Results stored on the message record
#   2. Memory update → Qdrant (when enabled)
#   3. High risk → auto-escalation
# ============================================================

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.integrations.llm.base import LLMConfig, LLMMessage
from app.prompts.conversation_intelligence_v1 import (
    CONVERSATION_INTELLIGENCE_SYSTEM_PROMPT,
    CONVERSATION_INTELLIGENCE_USER_PROMPT,
)

# ── Typed I/O ───────────────────────────────────────────────


class ConversationIntelligenceInput(BaseModel):
    """Input to the Conversation Intelligence Agent."""
    message_id: str
    sender_email: str
    subject: str | None = None
    body_text: str

    # Lead context
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    current_stage: str = "awareness"
    score: int | None = None

    # History
    conversation_history: str = ""
    memory_context: str = ""


class ConversationIntelligenceOutput(BaseModel):
    """Structured output with all 9 analysis dimensions."""
    sentiment: str = Field(
        ..., pattern="^(very_positive|positive|neutral|negative|very_negative)$"
    )
    intent: str = Field(
        ...,
        pattern="^(question|feedback|objection|interest|commitment|complaint|cancellation|referral)$",
    )
    buying_signals: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    competitor_mentions: list[str] = Field(default_factory=list)
    risk_level: str = Field("low", pattern="^(low|medium|high|critical)$")
    customer_stage: str = Field(
        "awareness",
        pattern="^(awareness|consideration|evaluation|decision|negotiation|closed)$",
    )
    next_best_action: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    summary: str | None = None
    memory_update: str | None = None


# ── Agent ───────────────────────────────────────────────────


class ConversationIntelligenceAgent(
    BaseAgent[ConversationIntelligenceInput, ConversationIntelligenceOutput]
):
    """Analyzes inbound customer messages across 9 intelligence dimensions.

    After execution:
    - Results are stored on the Message.analysis field
    - memory_update is sent to Qdrant (when conversation_memory flag is enabled)
    - High risk or very negative sentiment triggers auto-escalation
    """

    agent_type = "conversation_intelligence"

    async def execute(
        self, input_data: ConversationIntelligenceInput
    ) -> ConversationIntelligenceOutput:
        """Run conversation intelligence analysis."""

        # Retrieve stored memory from Qdrant (if available)
        memory_context = input_data.memory_context
        try:
            kb = self.tools.get_knowledge_base()
            memories = await kb.search(
                query=input_data.body_text,
                namespace=f"lead:{input_data.email}",
                limit=3,
            )
            if memories:
                memory_context = "\n".join(
                    f"- {m.get('text', '')}" for m in memories
                )
        except RuntimeError:
            # Knowledge base not registered yet
            pass

        # Build prompt
        user_prompt = CONVERSATION_INTELLIGENCE_USER_PROMPT.format(
            sender_email=input_data.sender_email,
            subject=input_data.subject or "(no subject)",
            body_text=input_data.body_text,
            first_name=input_data.first_name or "Unknown",
            last_name=input_data.last_name or "",
            email=input_data.email,
            company_name=input_data.company_name or "Unknown",
            job_title=input_data.job_title or "Unknown",
            current_stage=input_data.current_stage,
            score=input_data.score or "N/A",
            history_count="5",
            conversation_history=input_data.conversation_history or "No prior messages",
            memory_context=memory_context or "No stored memory",
        )

        messages = [
            LLMMessage(role="system", content=CONVERSATION_INTELLIGENCE_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        config = LLMConfig(
            temperature=0.2,
            max_tokens=1500,
            response_format="json",
        )

        output, response = await self.llm.generate_structured(
            messages, ConversationIntelligenceOutput, config
        )

        # Store memory update in Qdrant (if enabled and if there's a memory update)
        if output.memory_update:
            try:
                from app.core.feature_flags import get_feature_flags
                flags = get_feature_flags()
                if await flags.is_enabled(
                    "conversation_memory",
                    organization_id=str(self.organization_id),
                ):
                    kb = self.tools.get_knowledge_base()
                    await kb.store(
                        text=output.memory_update,
                        namespace=f"lead:{input_data.email}",
                        metadata={
                            "message_id": input_data.message_id,
                            "timestamp": "now",
                        },
                    )
            except RuntimeError:
                pass  # Knowledge base not configured yet

        return output
