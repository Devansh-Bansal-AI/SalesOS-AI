# ============================================================
# SalesOS AI — Escalation Service
#
# Enterprise pattern: when AI detects risk (negative sentiment,
# high value customer, low confidence), escalate to a human.
#
# Escalation targets:
# - Dashboard notification (always)
# - Future: Slack, Email alerts, PagerDuty
# ============================================================

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.services.crm_service import CRMService

logger = get_logger("escalation_service")


class EscalationService:
    """Handles human escalation when AI identifies risk or low confidence."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.crm = CRMService(session)

    async def escalate(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        reason: str,
        severity: str = "medium",
        conversation_id: UUID | None = None,
        analysis_data: dict | None = None,
        notes: str | None = None,
    ) -> None:
        """Create a human escalation.

        Triggers:
        - CRM activity log
        - DECISION_HUMAN_REVIEW_REQUESTED event
        - Future: Slack, email, PagerDuty notifications
        """
        # Log CRM activity
        await self.crm.log_activity(
            organization_id,
            lead_id,
            activity_type="escalation_created",
            title=f"⚠️ Human review required: {reason}",
            description=notes,
            metadata={
                "severity": severity,
                "reason": reason,
                "conversation_id": str(conversation_id) if conversation_id else None,
                "analysis": analysis_data,
                "escalated_at": datetime.now(UTC).isoformat(),
            },
        )

        # Publish event (dashboard, Slack integration will subscribe)
        await publish(
            self.session,
            event_type=EventTypes.DECISION_HUMAN_REVIEW_REQUESTED,
            organization_id=organization_id,
            aggregate_type="lead",
            aggregate_id=lead_id,
            payload={
                "reason": reason,
                "severity": severity,
                "conversation_id": str(conversation_id) if conversation_id else None,
                "notes": notes,
            },
        )

        logger.warning(
            "escalation_created",
            lead_id=str(lead_id),
            reason=reason,
            severity=severity,
        )

    async def auto_escalate_from_analysis(
        self,
        organization_id: UUID,
        lead_id: UUID,
        analysis: dict,
        *,
        conversation_id: UUID | None = None,
    ) -> bool:
        """Check analysis results and auto-escalate if needed.

        Returns True if escalated.
        """
        risk_level = analysis.get("risk_level", "low")
        sentiment = analysis.get("sentiment", "neutral")
        competitor_mentions = analysis.get("competitor_mentions", [])

        reasons = []

        # High/critical risk → always escalate
        if risk_level in ("high", "critical"):
            reasons.append(f"High risk detected: {risk_level}")

        # Very negative sentiment → escalate
        if sentiment == "very_negative":
            reasons.append("Very negative customer sentiment")

        # Multiple competitor mentions → escalate
        if len(competitor_mentions) >= 2:
            reasons.append(f"Multiple competitors mentioned: {', '.join(competitor_mentions[:3])}")

        if not reasons:
            return False

        severity = "critical" if risk_level == "critical" else "high"

        await self.escalate(
            organization_id,
            lead_id,
            reason="; ".join(reasons),
            severity=severity,
            conversation_id=conversation_id,
            analysis_data=analysis,
        )

        return True
