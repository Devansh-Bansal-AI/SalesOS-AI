# ============================================================
# SalesOS AI — Copilot Pydantic Schemas
# ============================================================

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CopilotQueryRequest(BaseModel):
    """Request schema for asking the SDR AI Copilot a question."""

    prompt: str = Field(..., min_length=1, max_length=2000, description="User prompt or question")
    lead_id: UUID | None = Field(default=None, description="Optional lead ID for scoped context")
    conversation_id: UUID | None = Field(
        default=None, description="Optional conversation ID for scoped context"
    )


class CopilotQueryResponse(BaseModel):
    """Response schema for SDR AI Copilot queries."""

    answer: str
    sources: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EmailDraftRequest(BaseModel):
    """Request schema for generating customized email drafts."""

    lead_id: UUID = Field(..., description="Target lead ID for email drafting")
    instructions: str | None = Field(default=None, description="Custom SDR instructions or notes")
    tone: Literal["professional", "friendly", "persuasive", "concise", "urgent"] = Field(
        default="professional", description="Desired copy tone"
    )
    max_length: Literal["short", "medium", "detailed"] = Field(
        default="medium", description="Length constraint"
    )


class EmailDraftResponse(BaseModel):
    """Response schema for generated email drafts."""

    subject: str
    body_text: str
    body_html: str
    reasoning: str | None = None


class DealPrepResponse(BaseModel):
    """Response schema for synthesized deal briefing and meeting prep."""

    lead_id: UUID
    company_name: str | None = None
    buyer_sentiment: str
    deal_health_score: int = Field(ge=0, le=100)
    key_pain_points: list[str] = Field(default_factory=list)
    recommended_agenda: list[str] = Field(default_factory=list)
    objection_playbook: dict[str, str] = Field(default_factory=dict)
