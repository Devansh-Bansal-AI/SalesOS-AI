# ============================================================
# SalesOS AI — Email Repository
# ============================================================

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email, FollowUpSequence
from app.repositories.base import BaseRepository


class EmailRepository(BaseRepository[Email]):
    def __init__(self, session: AsyncSession):
        super().__init__(Email, session)

    async def find_by_provider_id(self, provider_id: str) -> Email | None:
        """Find an email by its external provider ID."""
        stmt = select(Email).where(Email.provider_id == provider_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_scheduled(self, before: datetime) -> list[Email]:
        """Get emails scheduled for sending before a given time."""
        stmt = (
            select(Email)
            .where(
                Email.status == "scheduled",
                Email.scheduled_for <= before,
            )
            .order_by(Email.scheduled_for.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_lead_emails(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Email], int]:
        """Get emails for a specific lead."""
        filters = [Email.lead_id == lead_id]
        return await self.list(organization_id, offset=offset, limit=limit, filters=filters)


class FollowUpSequenceRepository(BaseRepository[FollowUpSequence]):
    def __init__(self, session: AsyncSession):
        super().__init__(FollowUpSequence, session)

    async def get_active_for_lead(
        self, organization_id: UUID, lead_id: UUID
    ) -> FollowUpSequence | None:
        """Get the active follow-up sequence for a lead."""
        stmt = (
            select(FollowUpSequence)
            .where(
                FollowUpSequence.organization_id == organization_id,
                FollowUpSequence.lead_id == lead_id,
                FollowUpSequence.status == "active",
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_due_sequences(self, before: datetime) -> list[FollowUpSequence]:
        """Get sequences that are due for their next step."""
        stmt = (
            select(FollowUpSequence)
            .where(
                FollowUpSequence.status == "active",
                FollowUpSequence.next_step_at <= before,
            )
            .order_by(FollowUpSequence.next_step_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
