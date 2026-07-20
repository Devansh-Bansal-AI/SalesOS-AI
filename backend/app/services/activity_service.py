# ============================================================
# SalesOS AI — Activity Service
#
# Unified CRUD across all formal activity types:
#   Meeting, Task, Reminder, Call, Note, Email, Follow-up
#
# All activities appear on the CRM timeline regardless of type.
# ============================================================

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.activity import Activity
from app.repositories.activity_repo import ActivityRepository
from app.schemas.sales_execution import (
    ActivityCreateRequest,
    ActivityResponse,
    ActivityTypes,
)

logger = get_logger("activity_service")


class ActivityService:
    """Unified activity management for the CRM timeline.

    Every interaction — human or AI — becomes an activity.
    This keeps the CRM timeline clean and queryable.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ActivityRepository(session)

    async def create_activity(
        self,
        organization_id: UUID,
        request: ActivityCreateRequest,
        *,
        user_id: UUID | None = None,
        is_ai_generated: bool = False,
        agent_run_id: UUID | None = None,
    ) -> ActivityResponse:
        """Create a new CRM activity."""
        activity = await self.repo.create(
            organization_id=organization_id,
            lead_id=request.lead_id,
            user_id=user_id,
            activity_type=request.activity_type,
            title=request.title,
            description=request.description,
            metadata_=request.metadata,
            is_ai_generated=is_ai_generated,
            agent_run_id=agent_run_id,
        )

        logger.info(
            "activity_created",
            activity_id=str(activity.id),
            lead_id=str(request.lead_id),
            type=request.activity_type,
        )

        return self._to_response(activity)

    async def get_lead_timeline(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        activity_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ActivityResponse], int]:
        """Get the full CRM timeline for a lead, optionally filtered by type."""
        filters = [Activity.lead_id == lead_id]
        if activity_type:
            filters.append(Activity.activity_type == activity_type)

        items, total = await self.repo.list(
            organization_id, offset=offset, limit=limit, filters=filters
        )
        return [self._to_response(a) for a in items], total

    async def get_user_activities(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ActivityResponse], int]:
        """Get activities created by or assigned to a user."""
        filters = [Activity.user_id == user_id]
        items, total = await self.repo.list(
            organization_id, offset=offset, limit=limit, filters=filters
        )
        return [self._to_response(a) for a in items], total

    async def get_activity_counts(
        self,
        organization_id: UUID,
        lead_id: UUID,
    ) -> dict[str, int]:
        """Get activity counts grouped by type for a lead."""
        stmt = (
            select(
                Activity.activity_type,
                func.count(Activity.id),
            )
            .where(
                Activity.organization_id == organization_id,
                Activity.lead_id == lead_id,
            )
            .group_by(Activity.activity_type)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    # ── Convenience Methods ─────────────────────────────

    async def log_note(
        self,
        organization_id: UUID,
        lead_id: UUID,
        title: str,
        description: str | None = None,
        *,
        user_id: UUID | None = None,
    ) -> ActivityResponse:
        """Quick method to add a note to a lead."""
        return await self.create_activity(
            organization_id,
            ActivityCreateRequest(
                lead_id=lead_id,
                activity_type=ActivityTypes.NOTE,
                title=title,
                description=description,
            ),
            user_id=user_id,
        )

    async def log_call(
        self,
        organization_id: UUID,
        lead_id: UUID,
        title: str,
        *,
        duration_seconds: int | None = None,
        outcome: str | None = None,
        user_id: UUID | None = None,
    ) -> ActivityResponse:
        """Log a phone call activity."""
        return await self.create_activity(
            organization_id,
            ActivityCreateRequest(
                lead_id=lead_id,
                activity_type=ActivityTypes.CALL,
                title=title,
                metadata={
                    "duration_seconds": duration_seconds,
                    "outcome": outcome,
                },
            ),
            user_id=user_id,
        )

    async def create_task(
        self,
        organization_id: UUID,
        lead_id: UUID,
        title: str,
        *,
        description: str | None = None,
        due_at: datetime | None = None,
        user_id: UUID | None = None,
    ) -> ActivityResponse:
        """Create a task for a lead."""
        return await self.create_activity(
            organization_id,
            ActivityCreateRequest(
                lead_id=lead_id,
                activity_type=ActivityTypes.TASK,
                title=title,
                description=description,
                due_at=due_at,
                metadata={"due_at": due_at.isoformat() if due_at else None},
            ),
            user_id=user_id,
        )

    async def create_reminder(
        self,
        organization_id: UUID,
        lead_id: UUID,
        title: str,
        remind_at: datetime,
        *,
        user_id: UUID | None = None,
    ) -> ActivityResponse:
        """Create a reminder for a lead."""
        return await self.create_activity(
            organization_id,
            ActivityCreateRequest(
                lead_id=lead_id,
                activity_type=ActivityTypes.REMINDER,
                title=title,
                metadata={"remind_at": remind_at.isoformat()},
            ),
            user_id=user_id,
        )

    # ── Helpers ─────────────────────────────────────────

    def _to_response(self, activity: Activity) -> ActivityResponse:
        return ActivityResponse(
            id=activity.id,
            lead_id=activity.lead_id,
            user_id=activity.user_id,
            activity_type=activity.activity_type,
            title=activity.title,
            description=activity.description,
            metadata_=activity.metadata_,
            is_ai_generated=activity.is_ai_generated,
            created_at=activity.created_at,
        )
