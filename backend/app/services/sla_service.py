# ============================================================
# SalesOS AI — SLA Service
#
# Standalone SLA engine — NOT inside LeadService.
#
# Responsibilities:
#   - Track response time obligations
#   - Detect violations
#   - Trigger reminders before deadline
#   - Escalate on violation
#   - Notify managers
# ============================================================

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.models.lead import Lead
from app.schemas.sales_execution import SLAConfig, SLAStatus
from app.services.crm_service import CRMService

logger = get_logger("sla_service")


class SLAService:
    """Standalone SLA engine for response time management.

    Usage:
        sla = SLAService(session)
        status = await sla.check_lead_sla(org_id, lead_id, config)
        violations = await sla.find_violations(org_id, config)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.crm = CRMService(session)

    async def check_lead_sla(
        self,
        organization_id: UUID,
        lead_id: UUID,
        config: SLAConfig | None = None,
    ) -> SLAStatus:
        """Check SLA status for a specific lead."""
        config = config or SLAConfig()
        lead = await self.session.get(Lead, lead_id)

        if not lead:
            return SLAStatus(lead_id=lead_id, is_violated=False)

        now = datetime.now(UTC)

        # Determine which SLA applies
        if lead.last_contacted_at is None:
            # Never contacted → first response SLA
            sla_minutes = config.first_response_minutes
            reference_time = lead.created_at
            violation_type = "first_response"
        else:
            # Has been contacted → follow-up response SLA
            sla_minutes = config.follow_up_response_minutes
            reference_time = lead.last_contacted_at
            violation_type = "follow_up_response"

        deadline = reference_time + timedelta(minutes=sla_minutes)
        minutes_remaining = int((deadline - now).total_seconds() / 60)

        return SLAStatus(
            lead_id=lead_id,
            is_violated=minutes_remaining < 0,
            violation_type=violation_type if minutes_remaining < 0 else None,
            minutes_remaining=max(minutes_remaining, 0) if minutes_remaining >= 0 else None,
            minutes_overdue=abs(minutes_remaining) if minutes_remaining < 0 else None,
            last_contact_at=lead.last_contacted_at,
            sla_deadline=deadline,
        )

    async def find_violations(
        self,
        organization_id: UUID,
        config: SLAConfig | None = None,
    ) -> list[SLAStatus]:
        """Find all leads currently violating SLA."""
        config = config or SLAConfig()
        now = datetime.now(UTC)

        # First response violations: leads never contacted, created > threshold ago
        first_response_cutoff = now - timedelta(minutes=config.first_response_minutes)

        stmt_first = select(Lead).where(
            Lead.organization_id == organization_id,
            Lead.last_contacted_at.is_(None),
            Lead.created_at <= first_response_cutoff,
            Lead.status.in_(["new", "contacted", "qualified"]),
            Lead.deleted_at.is_(None),
        )
        result_first = await self.session.execute(stmt_first)
        first_violations = list(result_first.scalars().all())

        # Follow-up violations: leads contacted but not within threshold
        followup_cutoff = now - timedelta(minutes=config.follow_up_response_minutes)

        stmt_followup = select(Lead).where(
            Lead.organization_id == organization_id,
            Lead.last_contacted_at.isnot(None),
            Lead.last_contacted_at <= followup_cutoff,
            Lead.status.in_(["contacted", "qualified", "nurture"]),
            Lead.deleted_at.is_(None),
        )
        result_followup = await self.session.execute(stmt_followup)
        followup_violations = list(result_followup.scalars().all())

        violations: list[SLAStatus] = []

        for lead in first_violations:
            deadline = lead.created_at + timedelta(minutes=config.first_response_minutes)
            violations.append(
                SLAStatus(
                    lead_id=lead.id,
                    is_violated=True,
                    violation_type="first_response",
                    minutes_overdue=int((now - deadline).total_seconds() / 60),
                    last_contact_at=None,
                    sla_deadline=deadline,
                )
            )

        for lead in followup_violations:
            deadline = lead.last_contacted_at + timedelta(minutes=config.follow_up_response_minutes)
            violations.append(
                SLAStatus(
                    lead_id=lead.id,
                    is_violated=True,
                    violation_type="follow_up_response",
                    minutes_overdue=int((now - deadline).total_seconds() / 60),
                    last_contact_at=lead.last_contacted_at,
                    sla_deadline=deadline,
                )
            )

        return violations

    async def find_approaching_deadline(
        self,
        organization_id: UUID,
        config: SLAConfig | None = None,
    ) -> list[SLAStatus]:
        """Find leads approaching SLA deadline (for reminders)."""
        config = config or SLAConfig()
        now = datetime.now(UTC)
        reminder_window = timedelta(minutes=config.reminder_before_minutes)

        # Leads that will violate first response within reminder window
        approaching_cutoff = (
            now + reminder_window - timedelta(minutes=config.first_response_minutes)
        )

        stmt = select(Lead).where(
            Lead.organization_id == organization_id,
            Lead.last_contacted_at.is_(None),
            Lead.created_at <= approaching_cutoff,
            Lead.status.in_(["new"]),
            Lead.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        approaching = list(result.scalars().all())

        statuses: list[SLAStatus] = []
        for lead in approaching:
            deadline = lead.created_at + timedelta(minutes=config.first_response_minutes)
            remaining = int((deadline - now).total_seconds() / 60)
            if remaining > 0:
                statuses.append(
                    SLAStatus(
                        lead_id=lead.id,
                        is_violated=False,
                        violation_type=None,
                        minutes_remaining=remaining,
                        last_contact_at=None,
                        sla_deadline=deadline,
                    )
                )

        return statuses

    async def process_violations(
        self,
        organization_id: UUID,
        config: SLAConfig | None = None,
    ) -> int:
        """Process all SLA violations — escalate and notify.

        Called by Celery beat. Returns count of violations processed.
        """
        violations = await self.find_violations(organization_id, config)

        for violation in violations:
            # Log CRM activity
            await self.crm.log_activity(
                organization_id,
                violation.lead_id,
                activity_type="sla_violation",
                title=f"⏰ SLA Violation: {violation.violation_type} ({violation.minutes_overdue} min overdue)",
                metadata={
                    "violation_type": violation.violation_type,
                    "minutes_overdue": violation.minutes_overdue,
                    "sla_deadline": violation.sla_deadline.isoformat()
                    if violation.sla_deadline
                    else None,
                },
            )

            # Publish escalation event
            await publish(
                self.session,
                event_type=EventTypes.DECISION_HUMAN_REVIEW_REQUESTED,
                organization_id=organization_id,
                aggregate_type="lead",
                aggregate_id=violation.lead_id,
                payload={
                    "reason": f"SLA violation: {violation.violation_type}",
                    "severity": "high",
                    "minutes_overdue": violation.minutes_overdue,
                },
            )

        if violations:
            logger.warning(
                "sla_violations_processed",
                organization_id=str(organization_id),
                count=len(violations),
            )

        return len(violations)
