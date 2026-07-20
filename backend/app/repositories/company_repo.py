# ============================================================
# SalesOS AI — Company Repository
# ============================================================

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

    async def find_by_domain(self, organization_id: UUID, domain: str) -> Company | None:
        """Find a company by its domain within an organization."""
        stmt = select(Company).where(
            Company.organization_id == organization_id,
            Company.domain == domain.lower(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_name(self, organization_id: UUID, name: str) -> Company | None:
        """Find a company by name (case-insensitive)."""
        stmt = select(Company).where(
            Company.organization_id == organization_id,
            Company.name.ilike(name),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_or_create(
        self, organization_id: UUID, name: str, domain: str | None = None
    ) -> Company:
        """Find existing company or create a new one."""
        if domain:
            existing = await self.find_by_domain(organization_id, domain)
            if existing:
                return existing

        existing = await self.find_by_name(organization_id, name)
        if existing:
            return existing

        return await self.create(
            organization_id=organization_id,
            name=name,
            domain=domain.lower() if domain else None,
        )
