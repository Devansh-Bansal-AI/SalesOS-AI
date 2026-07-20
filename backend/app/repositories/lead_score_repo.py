# ============================================================
# SalesOS AI — Lead Score Repository
# ============================================================

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import LeadScore
from app.repositories.base import BaseRepository


class LeadScoreRepository(BaseRepository[LeadScore]):
    def __init__(self, session: AsyncSession):
        super().__init__(LeadScore, session)

    async def get_latest_score(
        self, organization_id: UUID, lead_id: UUID
    ) -> LeadScore | None:
        """Get the most recent score for a lead."""
        stmt = (
            select(LeadScore)
            .where(
                LeadScore.organization_id == organization_id,
                LeadScore.lead_id == lead_id,
            )
            .order_by(LeadScore.scored_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_score_history(
        self, organization_id: UUID, lead_id: UUID
    ) -> list[LeadScore]:
        """Get all historical scores for a lead."""
        stmt = (
            select(LeadScore)
            .where(
                LeadScore.organization_id == organization_id,
                LeadScore.lead_id == lead_id,
            )
            .order_by(LeadScore.scored_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
