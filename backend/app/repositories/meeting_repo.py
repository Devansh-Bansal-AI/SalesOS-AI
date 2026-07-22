# ============================================================
# SalesOS AI — Meeting Repository
# ============================================================

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.repositories.base import BaseRepository


class MeetingRepository(BaseRepository[Meeting]):
    def __init__(self, session: AsyncSession):
        super().__init__(Meeting, session)

    async def find_by_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Meeting], int]:
        """Get meetings for a specific lead."""
        filters = [Meeting.lead_id == lead_id]
        items, total = await self.list(organization_id, offset=offset, limit=limit, filters=filters)
        return list(items), total

    async def find_upcoming(
        self,
        organization_id: UUID,
        *,
        user_id: UUID | None = None,
        after: datetime | None = None,
        limit: int = 20,
    ) -> list[Meeting]:
        """Get upcoming meetings."""

        after = after or datetime.now(UTC)
        stmt = select(Meeting).where(
            Meeting.organization_id == organization_id,
            Meeting.scheduled_at >= after,
            Meeting.status.in_(["pending", "confirmed"]),
        )
        if user_id:
            stmt = stmt.where(Meeting.host_user_id == user_id)

        stmt = stmt.order_by(Meeting.scheduled_at.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_needing_reminders(
        self,
        reminder_before: datetime,
        reminder_after: datetime,
    ) -> list[Meeting]:
        """Find meetings that need reminder notifications."""
        stmt = select(Meeting).where(
            Meeting.scheduled_at.between(reminder_after, reminder_before),
            Meeting.status.in_(["pending", "confirmed"]),
            Meeting.reminder_sent.is_(False),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_host(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        after: datetime | None = None,
    ) -> int:
        """Count meetings hosted by a user (for load balancing)."""

        after = after or datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(Meeting)
            .where(
                Meeting.organization_id == organization_id,
                Meeting.host_user_id == user_id,
                Meeting.scheduled_at >= after,
                Meeting.status.in_(["pending", "confirmed"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
