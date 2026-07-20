# ============================================================
# SalesOS AI — Communication Schemas
#
# The Communication domain treats email as ONE channel.
# These schemas support multi-channel from day one.
# ============================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Conversation ────────────────────────────────────────────


class ConversationCreateRequest(BaseModel):
    """Start a new conversation thread."""
    lead_id: UUID
    channel: str = Field("email", pattern="^(email|chat|sms|slack|whatsapp|api)$")
    subject: str | None = None


class ConversationResponse(BaseModel):
    """Conversation thread detail."""
    id: UUID
    lead_id: UUID
    status: str
    channel: str
    subject: str | None
    summary: str | None
    message_count: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """Compact conversation for list views."""
    id: UUID
    lead_id: UUID
    status: str
    channel: str
    subject: str | None
    message_count: int
    last_message_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Message ─────────────────────────────────────────────────


class MessageCreateRequest(BaseModel):
    """Send or record a message in a conversation."""
    direction: str = Field("outbound", pattern="^(inbound|outbound)$")
    channel: str = Field("email", pattern="^(email|chat|sms|slack|whatsapp|api)$")
    sender_email: str | None = None
    recipient_email: str | None = None
    subject: str | None = None
    body_text: str
    body_html: str | None = None


class MessageResponse(BaseModel):
    """Message detail."""
    id: UUID
    conversation_id: UUID
    direction: str
    channel: str
    sender_email: str | None
    recipient_email: str | None
    subject: str | None
    body_text: str | None
    analysis: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Email ───────────────────────────────────────────────────


class EmailSendRequest(BaseModel):
    """Send an email to a lead."""
    lead_id: UUID
    subject: str = Field(..., max_length=500)
    body_text: str
    body_html: str | None = None
    from_email: str | None = None
    reply_to: str | None = None
    schedule_for: datetime | None = None  # Delayed send


class EmailResponse(BaseModel):
    """Email detail."""
    id: UUID
    lead_id: UUID
    conversation_id: UUID | None
    subject: str
    body_text: str
    from_email: str
    to_email: str
    status: str
    provider: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    opened_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Inbound Webhook ─────────────────────────────────────────


class InboundEmailPayload(BaseModel):
    """Inbound email received via webhook."""
    from_email: EmailStr
    to_email: EmailStr
    subject: str | None = None
    body_text: str
    body_html: str | None = None
    message_id: str | None = None
    in_reply_to: str | None = None
    headers: dict | None = None


# ── Conversation Analysis ───────────────────────────────────


class ConversationAnalysis(BaseModel):
    """Output from the Conversation Intelligence Agent."""
    sentiment: str = Field(..., pattern="^(very_positive|positive|neutral|negative|very_negative)$")
    intent: str
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
    memory_update: str | None = None  # What to store in Qdrant for future context


# ── Follow-Up ───────────────────────────────────────────────


class FollowUpSequenceResponse(BaseModel):
    """Follow-up sequence status."""
    id: UUID
    lead_id: UUID
    name: str | None
    status: str
    current_step: int
    max_steps: int
    next_step_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Escalation ──────────────────────────────────────────────


class EscalationRequest(BaseModel):
    """Request human escalation for a conversation."""
    lead_id: UUID
    conversation_id: UUID | None = None
    reason: str
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    notes: str | None = None
