# ============================================================
# SalesOS AI — Meeting Service
#
# Meeting management: book, reschedule, cancel.
# Uses CalendarProvider for external calendar integration.
# ============================================================

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.integrations import CalendarEvent, get_registry
from app.models.meeting import Meeting
from app.repositories.meeting_repo import MeetingRepository
from app.schemas.sales_execution import (
    MeetingCancelRequest,
    MeetingCreateRequest,
    MeetingListResponse,
    MeetingRescheduleRequest,
    MeetingResponse,
)
from app.services.crm_service import CRMService

logger = get_logger("meeting_service")


class MeetingService:
    """Meeting lifecycle management with calendar provider integration.

    Supports: book, reschedule, cancel, with external calendar sync.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MeetingRepository(session)
        self.crm = CRMService(session)
        self._registry = get_registry()

    # ── Book ────────────────────────────────────────────

    async def book_meeting(
        self,
        organization_id: UUID,
        request: MeetingCreateRequest,
        *,
        host_user_id: UUID | None = None,
        agent_run_id: UUID | None = None,
    ) -> MeetingResponse:
        """Book a meeting with a lead.

        Flow:
        1. Create meeting record
        2. Sync to calendar provider (if available)
        3. Log CRM activity
        4. Publish MEETING_SCHEDULED event
        """
        meeting = await self.repo.create(
            organization_id=organization_id,
            lead_id=request.lead_id,
            host_user_id=host_user_id,
            title=request.title,
            description=request.description,
            meeting_type=request.meeting_type,
            status="pending",
            scheduled_at=request.scheduled_at,
            duration_minutes=request.duration_minutes,
            timezone=request.timezone,
            agent_run_id=agent_run_id,
        )

        # Sync to external calendar
        await self._sync_to_calendar(meeting)

        # CRM activity
        await self.crm.log_activity(
            organization_id,
            request.lead_id,
            activity_type="meeting_booked",
            title=f"📅 Meeting booked: {request.title}",
            metadata={
                "meeting_id": str(meeting.id),
                "meeting_type": request.meeting_type,
                "scheduled_at": request.scheduled_at.isoformat(),
                "duration_minutes": request.duration_minutes,
            },
        )

        # Update lead status if needed
        from app.repositories.lead_repo import LeadRepository

        lead_repo = LeadRepository(self.session)
        lead = await lead_repo.get_by_id_and_org(request.lead_id, organization_id)
        if lead and lead.status in ("new", "contacted", "qualified"):
            lead.status = "meeting_booked"
            await self.session.flush()

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.MEETING_SCHEDULED,
            organization_id=organization_id,
            aggregate_type="meeting",
            aggregate_id=meeting.id,
            payload={
                "lead_id": str(request.lead_id),
                "title": request.title,
                "meeting_type": request.meeting_type,
                "scheduled_at": request.scheduled_at.isoformat(),
                "host_user_id": str(host_user_id) if host_user_id else None,
            },
        )

        logger.info(
            "meeting_booked",
            meeting_id=str(meeting.id),
            lead_id=str(request.lead_id),
            scheduled_at=request.scheduled_at.isoformat(),
        )

        return self._to_response(meeting)

    # ── Reschedule ──────────────────────────────────────

    async def reschedule_meeting(
        self,
        organization_id: UUID,
        meeting_id: UUID,
        request: MeetingRescheduleRequest,
    ) -> MeetingResponse:
        """Reschedule a meeting."""
        meeting = await self.repo.get_by_id_and_org(meeting_id, organization_id)
        if not meeting:
            raise NotFoundError("Meeting", meeting_id)

        old_time = meeting.scheduled_at

        meeting.scheduled_at = request.scheduled_at
        if request.duration_minutes:
            meeting.duration_minutes = request.duration_minutes
        if request.timezone:
            meeting.timezone = request.timezone
        meeting.status = "pending"
        meeting.confirmation_sent = False
        meeting.reminder_sent = False

        await self.session.flush()

        # Update calendar
        if meeting.calendar_event_id:
            try:
                provider = self._registry.get_calendar()
                await provider.cancel_event(meeting.calendar_event_id)
            except (ValueError, Exception) as e:
                logger.warning(
                    "calendar_cancel_failed",
                    meeting_id=str(meeting_id),
                    error=str(e),
                )
            await self._sync_to_calendar(meeting)

        # CRM activity
        await self.crm.log_activity(
            organization_id,
            meeting.lead_id,
            activity_type="meeting_rescheduled",
            title=f"🔄 Meeting rescheduled: {meeting.title}",
            metadata={
                "meeting_id": str(meeting_id),
                "old_time": old_time.isoformat(),
                "new_time": request.scheduled_at.isoformat(),
                "reason": request.reason,
            },
        )

        logger.info(
            "meeting_rescheduled",
            meeting_id=str(meeting_id),
            old_time=old_time.isoformat(),
            new_time=request.scheduled_at.isoformat(),
        )

        return self._to_response(meeting)

    # ── Cancel ──────────────────────────────────────────

    async def cancel_meeting(
        self,
        organization_id: UUID,
        meeting_id: UUID,
        request: MeetingCancelRequest,
    ) -> MeetingResponse:
        """Cancel a meeting."""
        meeting = await self.repo.get_by_id_and_org(meeting_id, organization_id)
        if not meeting:
            raise NotFoundError("Meeting", meeting_id)

        meeting.status = "cancelled"
        meeting.cancelled_at = datetime.now(UTC)
        meeting.cancel_reason = request.reason
        await self.session.flush()

        # Cancel on calendar
        if meeting.calendar_event_id:
            try:
                provider = self._registry.get_calendar()
                await provider.cancel_event(meeting.calendar_event_id)
            except (ValueError, Exception) as e:
                logger.warning(
                    "calendar_cancel_failed",
                    meeting_id=str(meeting_id),
                    error=str(e),
                )

        # CRM activity
        await self.crm.log_activity(
            organization_id,
            meeting.lead_id,
            activity_type="meeting_cancelled",
            title=f"❌ Meeting cancelled: {meeting.title}",
            metadata={
                "meeting_id": str(meeting_id),
                "reason": request.reason,
            },
        )

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.MEETING_CANCELLED,
            organization_id=organization_id,
            aggregate_type="meeting",
            aggregate_id=meeting_id,
            payload={
                "lead_id": str(meeting.lead_id),
                "reason": request.reason,
            },
        )

        logger.info("meeting_cancelled", meeting_id=str(meeting_id))

        return self._to_response(meeting)

    # ── Queries ─────────────────────────────────────────

    async def get_meeting(self, organization_id: UUID, meeting_id: UUID) -> MeetingResponse:
        meeting = await self.repo.get_by_id_and_org(meeting_id, organization_id)
        if not meeting:
            raise NotFoundError("Meeting", meeting_id)
        return self._to_response(meeting)

    async def list_by_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[MeetingListResponse], int]:
        items, total = await self.repo.find_by_lead(
            organization_id, lead_id, offset=offset, limit=limit
        )
        return [self._to_list_response(m) for m in items], total

    async def list_upcoming(
        self,
        organization_id: UUID,
        *,
        user_id: UUID | None = None,
        limit: int = 20,
    ) -> list[MeetingListResponse]:
        items = await self.repo.find_upcoming(organization_id, user_id=user_id, limit=limit)
        return [self._to_list_response(m) for m in items]

    # ── Calendar Sync ───────────────────────────────────

    async def _sync_to_calendar(self, meeting: Meeting) -> None:
        """Sync meeting to external calendar provider."""
        try:
            provider = self._registry.get_calendar()

            # Get lead email for attendee list
            from app.repositories.lead_repo import LeadRepository

            lead_repo = LeadRepository(self.session)
            lead = await lead_repo.get_by_id_and_org(meeting.lead_id, meeting.organization_id)
            attendees = [lead.email] if lead else []

            event = CalendarEvent(
                title=meeting.title,
                description=meeting.description,
                start_time=meeting.scheduled_at.isoformat(),
                end_time=(
                    meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
                ).isoformat(),
                timezone=meeting.timezone,
                attendees=attendees,
            )

            result = await provider.create_event(event)

            if result.success:
                meeting.calendar_provider = result.provider
                meeting.calendar_event_id = result.event_id
                meeting.meeting_link = result.meeting_link
                meeting.status = "confirmed"
                await self.session.flush()

        except ValueError:
            # No calendar provider registered — meeting stays as pending
            logger.debug("no_calendar_provider", meeting_id=str(meeting.id))
        except Exception as e:
            logger.error(
                "calendar_sync_failed",
                meeting_id=str(meeting.id),
                error=str(e),
            )

    # ── Helpers ─────────────────────────────────────────

    def _to_response(self, m: Meeting) -> MeetingResponse:
        return MeetingResponse(
            id=m.id,
            lead_id=m.lead_id,
            host_user_id=m.host_user_id,
            title=m.title,
            description=m.description,
            meeting_type=m.meeting_type,
            status=m.status,
            scheduled_at=m.scheduled_at,
            duration_minutes=m.duration_minutes,
            timezone=m.timezone,
            meeting_link=m.meeting_link,
            calendar_provider=m.calendar_provider,
            confirmation_sent=m.confirmation_sent,
            reminder_sent=m.reminder_sent,
            cancelled_at=m.cancelled_at,
            cancel_reason=m.cancel_reason,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def _to_list_response(self, m: Meeting) -> MeetingListResponse:
        return MeetingListResponse(
            id=m.id,
            lead_id=m.lead_id,
            title=m.title,
            meeting_type=m.meeting_type,
            status=m.status,
            scheduled_at=m.scheduled_at,
            duration_minutes=m.duration_minutes,
            meeting_link=m.meeting_link,
            created_at=m.created_at,
        )
