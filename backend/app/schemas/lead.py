# ============================================================
# SalesOS AI — Lead Schemas
# ============================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Create ──────────────────────────────────────────────────


class LeadCreateRequest(BaseModel):
    """Create a new lead."""

    email: EmailStr
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    company_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    job_title: str | None = Field(None, max_length=200)
    linkedin_url: str | None = Field(None, max_length=500)
    source: str = Field(..., pattern="^(website|marketplace|email|form|api|import|referral)$")
    source_detail: dict | None = None
    message: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


# ── Update ──────────────────────────────────────────────────


class LeadUpdateRequest(BaseModel):
    """Update lead fields."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    job_title: str | None = None
    linkedin_url: str | None = None
    status: str | None = None
    priority: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    notes: str | None = None


# ── Assign ──────────────────────────────────────────────────


class LeadAssignRequest(BaseModel):
    """Assign lead to a user."""

    user_id: UUID


# ── Response ────────────────────────────────────────────────


class LeadResponse(BaseModel):
    """Lead detail response."""

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    phone: str | None
    job_title: str | None
    linkedin_url: str | None
    company_name: str | None = None
    status: str
    priority: str | None
    source: str
    source_detail: dict | None
    qualification: dict | None
    enrichment: dict | None
    last_contacted_at: datetime | None
    next_follow_up_at: datetime | None
    follow_up_count: int
    tags: list[str]
    custom_fields: dict
    notes: str | None
    assigned_to: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    """Compact lead for list views."""

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    company_name: str | None = None
    status: str
    priority: str | None
    source: str
    score: int | None = None
    assigned_to: UUID | None
    last_contacted_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Qualification ───────────────────────────────────────────


class QualificationResponse(BaseModel):
    """Qualification agent output."""

    score: int = Field(..., ge=0, le=100)
    priority: str
    intent: str
    urgency: str
    summary: str
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str | None = None


# ── Filters ─────────────────────────────────────────────────


class LeadFilterParams(BaseModel):
    """Query parameters for filtering leads."""

    status: str | None = None
    priority: str | None = None
    source: str | None = None
    assigned_to: UUID | None = None
    search: str | None = None  # Search email, name, company
    created_after: datetime | None = None
    created_before: datetime | None = None
