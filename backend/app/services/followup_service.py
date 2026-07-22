# ============================================================
# SalesOS AI — Follow-Up Service
#
# State-aware follow-up instead of "wait 2 days, email."
#
# Flow:
#   Workflow Timer → Conversation State → Decision Engine →
#   Need Follow-up? → Generate → Send → Schedule Next
# ============================================================

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import get_feature_flags
from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.models.email import FollowUpSequence
from app.repositories.email_repo import FollowUpSequenceRepository
from app.services.crm_service import CRMService

logger = get_logger("followup_service")


class FollowUpService:
    """State-aware follow-up sequence management.

    Instead of blind "wait 2 days → email", each follow-up:
    1. Checks conversation state (has lead replied?)
    2. Evaluates via Decision Engine (still worth pursuing?)
    3. Generates contextual follow-up (uses conversation memory)
    4. Sends and schedules next step
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.seq_repo = FollowUpSequenceRepository(session)
        self.crm = CRMService(session)
        self.flags = get_feature_flags()

    async def start_sequence(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        name: str | None = None,
        max_steps: int = 3,
        step_delays_days: list[int] | None = None,
    ) -> FollowUpSequence:
        """Start a new follow-up sequence for a lead.

        Returns the created sequence.
        """
        if not await self.flags.is_enabled(
            "follow_up_sequences", organization_id=str(organization_id)
        ):
            raise RuntimeError("Follow-up sequences are disabled")

        # Check for existing active sequence
        existing = await self.seq_repo.get_active_for_lead(organization_id, lead_id)
        if existing:
            logger.info(
                "followup_already_active",
                lead_id=str(lead_id),
                sequence_id=str(existing.id),
            )
            return existing

        delays = step_delays_days or [2, 5, 10]

        sequence = await self.seq_repo.create(
            organization_id=organization_id,
            lead_id=lead_id,
            name=name or "automated_followup",
            status="active",
            current_step=0,
            max_steps=max_steps,
            step_delays=delays,
            next_step_at=datetime.now(UTC) + timedelta(days=delays[0]),
        )

        # CRM activity
        await self.crm.log_activity(
            organization_id,
            lead_id,
            activity_type="followup_scheduled",
            title=f"Follow-up sequence started ({max_steps} steps)",
            metadata={
                "sequence_id": str(sequence.id),
                "delays_days": delays,
                "next_step_at": sequence.next_step_at.isoformat(),
            },
        )

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.FOLLOWUP_SCHEDULED,
            organization_id=organization_id,
            aggregate_type="followup",
            aggregate_id=sequence.id,
            payload={
                "lead_id": str(lead_id),
                "max_steps": max_steps,
                "next_step_at": sequence.next_step_at.isoformat(),
            },
        )

        logger.info(
            "followup_started",
            sequence_id=str(sequence.id),
            lead_id=str(lead_id),
            max_steps=max_steps,
        )

        return sequence

    async def execute_step(
        self,
        sequence: FollowUpSequence,
    ) -> bool:
        """Execute the next step in a follow-up sequence.

        Called by the Celery beat worker.

        Returns True if the step was executed, False if skipped/cancelled.
        """
        organization_id = sequence.organization_id
        lead_id = sequence.lead_id

        # Check if lead has replied (state-aware)
        from app.services.conversation_service import ConversationService

        conv_service = ConversationService(self.session)

        recent_messages = await conv_service.get_recent_lead_messages(
            organization_id, lead_id, limit=3
        )

        # If lead has replied since the sequence started, cancel the sequence
        has_reply = any(m.direction == "inbound" for m in recent_messages)
        if has_reply:
            sequence.status = "completed"
            sequence.completed_at = datetime.now(UTC)
            sequence.cancel_reason = "lead_replied"
            await self.session.flush()

            logger.info(
                "followup_cancelled_lead_replied",
                sequence_id=str(sequence.id),
                lead_id=str(lead_id),
            )
            return False

        # Check decision engine (still worth pursuing?)
        from app.services.decision_engine import DecisionEngine

        engine = DecisionEngine()

        # Get lead data for decision
        from app.repositories.lead_repo import LeadRepository

        lead_repo = LeadRepository(self.session)
        lead = await lead_repo.get_by_id_and_org(lead_id, organization_id)

        if not lead:
            sequence.status = "cancelled"
            sequence.cancel_reason = "lead_not_found"
            await self.session.flush()
            return False

        decision = await engine.evaluate(
            {
                "score": lead.qualification.get("score", 0) if lead.qualification else 0,
                "intent": lead.qualification.get("intent", "general")
                if lead.qualification
                else "general",
                "urgency": lead.qualification.get("urgency", "unknown")
                if lead.qualification
                else "unknown",
                "confidence": lead.qualification.get("confidence", 0.5)
                if lead.qualification
                else 0.5,
                "follow_up_count": sequence.current_step,
            },
            organization_id=str(organization_id),
        )

        if decision.action in ("disqualify", "watch"):
            sequence.status = "cancelled"
            sequence.cancel_reason = f"decision_engine_{decision.action}"
            await self.session.flush()
            logger.info(
                "followup_cancelled_by_decision",
                sequence_id=str(sequence.id),
                action=decision.action,
            )
            return False

        # Generate and send follow-up (placeholder — Sprint 4 wires up FollowUp Agent)
        logger.info(
            "followup_step_executed",
            sequence_id=str(sequence.id),
            step=sequence.current_step,
        )

        # Advance sequence
        sequence.current_step += 1

        if sequence.current_step >= sequence.max_steps:
            sequence.status = "completed"
            sequence.completed_at = datetime.now(UTC)
        else:
            # Schedule next step
            delay_idx = min(sequence.current_step, len(sequence.step_delays) - 1)
            delay_days = sequence.step_delays[delay_idx]
            sequence.next_step_at = datetime.now(UTC) + timedelta(days=delay_days)

        await self.session.flush()

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.FOLLOWUP_SENT,
            organization_id=organization_id,
            aggregate_type="followup",
            aggregate_id=sequence.id,
            payload={
                "lead_id": str(lead_id),
                "step": sequence.current_step,
                "status": sequence.status,
            },
        )

        return True

    async def cancel_sequence(
        self,
        organization_id: UUID,
        sequence_id: UUID,
        *,
        reason: str = "manual",
    ) -> None:
        """Cancel an active follow-up sequence."""
        sequence = await self.seq_repo.get_by_id_and_org(sequence_id, organization_id)
        if not sequence:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("FollowUpSequence", sequence_id)

        sequence.status = "cancelled"
        sequence.cancelled_at = datetime.now(UTC)
        sequence.cancel_reason = reason
        await self.session.flush()

        logger.info(
            "followup_cancelled",
            sequence_id=str(sequence_id),
            reason=reason,
        )

    async def get_due_sequences(self) -> list[FollowUpSequence]:
        """Get all sequences due for execution (Celery worker calls this)."""
        return await self.seq_repo.get_due_sequences(datetime.now(UTC))
