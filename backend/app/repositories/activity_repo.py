# ============================================================
# SalesOS AI — Activity Repository
# ============================================================

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[Activity]):
    def __init__(self, session: AsyncSession):
        super().__init__(Activity, session)

    async def get_lead_timeline(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Activity], int]:
        """Get activity timeline for a lead, most recent first."""
        filters = [Activity.lead_id == lead_id]
        items, total = await self.list(
            organization_id, offset=offset, limit=limit, filters=filters
        )
        return list(items), total
