# ============================================================
# SalesOS AI — Sales Execution Schemas
#
# The Sales Execution domain formalizes:
# - Activity types (Meeting, Task, Reminder, Call, Note, etc.)
# - Meetings (book, reschedule, cancel)
# - Assignment strategies
# - SLA configuration
# ============================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Activity Types ──────────────────────────────────────────


class ActivityTypes:
    """Formal activity types for the CRM timeline."""

    MEETING = "meeting"
    TASK = "task"
    REMINDER = "reminder"
    CALL = "call"
    NOTE = "note"
    EMAIL = "email_sent"
    EMAIL_RECEIVED = "email_received"
    FOLLOWUP = "follow_up"
    QUALIFICATION = "qualification_completed"
    ENRICHMENT = "enrichment_completed"
    ASSIGNMENT = "lead_assigned"
    ESCALATION = "escalation_created"
    STATUS_CHANGE = "status_changed"
    SCORE_CHANGE = "score_changed"


# ── Activity Schemas ────────────────────────────────────────


class ActivityCreateRequest(BaseModel):
    """Create a CRM activity."""

    lead_id: UUID
    activity_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    description: str | None = None
    metadata: dict = Field(default_factory=dict)
    due_at: datetime | None = None  # For tasks and reminders


class ActivityResponse(BaseModel):
    """Activity detail for CRM timeline."""

    id: UUID
    lead_id: UUID
    user_id: UUID | None
    activity_type: str
    title: str
    description: str | None
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    is_ai_generated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Meeting Schemas ─────────────────────────────────────────


class MeetingCreateRequest(BaseModel):
    """Book a meeting with a lead."""

    lead_id: UUID
    title: str = Field(..., max_length=500)
    description: str | None = None
    meeting_type: str = Field("demo", pattern="^(demo|discovery|follow_up|onboarding|custom)$")
    scheduled_at: datetime
    duration_minutes: int = Field(30, ge=15, le=480)
    timezone: str = "UTC"


class MeetingRescheduleRequest(BaseModel):
    """Reschedule a meeting."""

    scheduled_at: datetime
    duration_minutes: int | None = None
    timezone: str | None = None
    reason: str | None = None


class MeetingCancelRequest(BaseModel):
    """Cancel a meeting."""

    reason: str = "cancelled_by_user"


class MeetingResponse(BaseModel):
    """Meeting detail."""

    id: UUID
    lead_id: UUID
    host_user_id: UUID | None
    title: str
    description: str | None
    meeting_type: str
    status: str
    scheduled_at: datetime
    duration_minutes: int
    timezone: str
    meeting_link: str | None
    calendar_provider: str | None
    confirmation_sent: bool
    reminder_sent: bool
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingListResponse(BaseModel):
    """Compact meeting for list views."""

    id: UUID
    lead_id: UUID
    title: str
    meeting_type: str
    status: str
    scheduled_at: datetime
    duration_minutes: int
    meeting_link: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Assignment Schemas ──────────────────────────────────────


class AssignmentStrategy:
    """Available assignment strategies."""

    ROUND_ROBIN = "round_robin"
    LOAD_BASED = "load_based"
    TERRITORY = "territory"
    SKILL_BASED = "skill_based"
    MANUAL = "manual"


class AssignmentConfig(BaseModel):
    """Organization-level assignment configuration."""

    strategy: str = Field(
        AssignmentStrategy.ROUND_ROBIN,
        pattern="^(round_robin|load_based|territory|skill_based|manual)$",
    )
    max_leads_per_rep: int = Field(50, ge=1, le=500)
    auto_assign_enabled: bool = True
    fallback_user_id: UUID | None = None


class AssignmentResult(BaseModel):
    """Result from the Assignment Engine."""

    assigned_to: UUID
    strategy_used: str
    reason: str
    candidates_evaluated: int


# ── SLA Schemas ─────────────────────────────────────────────


class SLAConfig(BaseModel):
    """SLA configuration for an organization."""

    first_response_minutes: int = Field(120, ge=1)  # 2 hours default
    follow_up_response_minutes: int = Field(480, ge=1)  # 8 hours default
    escalation_after_minutes: int = Field(240, ge=1)  # 4 hours default
    reminder_before_minutes: int = Field(30, ge=1)  # 30 min before violation


class SLAStatus(BaseModel):
    """SLA status for a lead."""

    lead_id: UUID
    is_violated: bool
    violation_type: str | None = None  # first_response, follow_up_response
    minutes_remaining: int | None = None
    minutes_overdue: int | None = None
    last_contact_at: datetime | None = None
    sla_deadline: datetime | None = None


# ── Dashboard Schemas ───────────────────────────────────────


class PipelineMetrics(BaseModel):
    """Pipeline overview metrics."""

    total_leads: int = 0
    new_leads: int = 0
    qualified_leads: int = 0
    in_conversation: int = 0
    meetings_booked: int = 0
    converted: int = 0
    disqualified: int = 0
    avg_qualification_score: float = 0.0
    avg_time_to_qualify_hours: float = 0.0


class ConversionMetrics(BaseModel):
    """Conversion funnel metrics."""

    lead_to_qualified_rate: float = 0.0
    qualified_to_meeting_rate: float = 0.0
    meeting_to_conversion_rate: float = 0.0
    overall_conversion_rate: float = 0.0
    avg_deal_velocity_days: float = 0.0


class RepPerformance(BaseModel):
    """Individual sales rep performance."""

    user_id: UUID
    user_name: str
    active_leads: int = 0
    meetings_booked: int = 0
    conversions: int = 0
    avg_response_time_minutes: float = 0.0
    sla_compliance_rate: float = 0.0
