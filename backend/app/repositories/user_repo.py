# ============================================================
# SalesOS AI — User Repository
# ============================================================

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def find_by_email(self, organization_id: UUID, email: str) -> User | None:
        """Find a user by email within an organization."""
        stmt = select(User).where(
            User.organization_id == organization_id,
            User.email == email,
            User.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_email_any_org(self, email: str) -> User | None:
        """Find a user by email across all organizations (for login)."""
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
