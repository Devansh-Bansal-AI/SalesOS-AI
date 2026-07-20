# ============================================================
# SalesOS AI — Lead Repository
# ============================================================

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: AsyncSession):
        super().__init__(Lead, session)

    async def find_by_email(self, organization_id: UUID, email: str) -> Lead | None:
        """Find an active lead by email within an organization."""
        stmt = select(Lead).where(
            Lead.organization_id == organization_id,
            Lead.email == email,
            Lead.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_duplicates(self, organization_id: UUID, email: str) -> list[Lead]:
        """Find potential duplicate leads by email."""
        stmt = select(Lead).where(
            Lead.organization_id == organization_id,
            Lead.email == email,
            Lead.deleted_at.is_(None),
            Lead.status.notin_(["disqualified", "archived"]),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        organization_id: UUID,
        query: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Lead], int]:
        """Search leads by email, name, or company name."""
        search_term = f"%{query}%"
        filters = [
            or_(
                Lead.email.ilike(search_term),
                Lead.first_name.ilike(search_term),
                Lead.last_name.ilike(search_term),
            )
        ]
        items, total = await self.list(
            organization_id, offset=offset, limit=limit, filters=filters
        )
        return list(items), total
