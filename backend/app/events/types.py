# ============================================================
# SalesOS AI — Event Types
# Domain event type definitions used across the system.
# ============================================================


class EventTypes:
    """Centralized event type constants. Never use raw strings."""

    # Lead events
    LEAD_CREATED = "lead.created"
    LEAD_VALIDATED = "lead.validated"
    LEAD_DUPLICATE_DETECTED = "lead.duplicate_detected"
    LEAD_QUALIFICATION_STARTED = "lead.qualification.started"
    LEAD_QUALIFICATION_COMPLETED = "lead.qualification.completed"
    LEAD_ENRICHMENT_COMPLETED = "lead.enrichment.completed"
    LEAD_SCORED = "lead.scored"
    LEAD_ASSIGNED = "lead.assigned"
    LEAD_STATUS_CHANGED = "lead.status_changed"
    LEAD_DISQUALIFIED = "lead.disqualified"
    LEAD_CONVERTED = "lead.converted"
    LEAD_LOST = "lead.lost"

    # Email events
    EMAIL_GENERATED = "email.generated"
    EMAIL_SENT = "email.sent"
    EMAIL_DELIVERED = "email.delivered"
    EMAIL_OPENED = "email.opened"
    EMAIL_BOUNCED = "email.bounced"

    # Conversation events
    CONVERSATION_MESSAGE_RECEIVED = "conversation.message_received"
    CONVERSATION_ANALYZED = "conversation.analyzed"
    CONVERSATION_REPLY_RECEIVED = "conversation.reply_received"

    # Meeting events
    MEETING_SCHEDULED = "meeting.scheduled"
    MEETING_CONFIRMED = "meeting.confirmed"
    MEETING_CANCELLED = "meeting.cancelled"
    MEETING_COMPLETED = "meeting.completed"

    # Follow-up events
    FOLLOWUP_SCHEDULED = "followup.scheduled"
    FOLLOWUP_SENT = "followup.sent"
    FOLLOWUP_COMPLETED = "followup.completed"
    FOLLOWUP_CANCELLED = "followup.cancelled"

    # Decision events
    DECISION_EVALUATED = "decision.evaluated"
    DECISION_HUMAN_REVIEW_REQUESTED = "decision.human_review_requested"

    # Escalation events
    ESCALATION_CREATED = "escalation.created"
    ESCALATION_RESOLVED = "escalation.resolved"

    # Agent events
    AGENT_RUN_STARTED = "agent.run.started"
    AGENT_RUN_COMPLETED = "agent.run.completed"
    AGENT_RUN_FAILED = "agent.run.failed"
