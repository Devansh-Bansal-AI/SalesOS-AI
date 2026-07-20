# ============================================================
# SalesOS AI — Base Repository
# Generic CRUD operations for all models. Repositories handle
# data access only — no business logic.
# ============================================================

from collections.abc import Sequence
from datetime import UTC
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing standard CRUD operations.

    Subclass this for each model and add domain-specific queries.

    Usage:
        class LeadRepository(BaseRepository[Lead]):
            def __init__(self, session: AsyncSession):
                super().__init__(Lead, session)

            async def find_by_email(self, org_id: UUID, email: str) -> Lead | None:
                ...
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Get a single record by ID."""
        return await self.session.get(self.model, id)

    async def get_by_id_and_org(
        self, id: UUID, organization_id: UUID
    ) -> ModelType | None:
        """Get a record scoped to an organization."""
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.organization_id == organization_id,
        )
        # Apply soft delete filter if model has deleted_at
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        organization_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: Any = None,
        filters: list[Any] | None = None,
    ) -> tuple[Sequence[ModelType], int]:
        """List records with pagination. Returns (items, total_count)."""
        # Base query scoped to organization
        base_filter = [self.model.organization_id == organization_id]
        if hasattr(self.model, "deleted_at"):
            base_filter.append(self.model.deleted_at.is_(None))

        if filters:
            base_filter.extend(filters)

        # Count query
        count_stmt = select(func.count()).select_from(self.model).where(*base_filter)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Data query
        stmt = select(self.model).where(*base_filter).offset(offset).limit(limit)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())

        result = await self.session.execute(stmt)
        items = result.scalars().all()

        return items, total

    async def update_by_id(
        self, id: UUID, organization_id: UUID, **kwargs: Any
    ) -> ModelType | None:
        """Update a record by ID. Returns updated instance or None."""
        instance = await self.get_by_id_and_org(id, organization_id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def soft_delete(
        self, id: UUID, organization_id: UUID
    ) -> bool:
        """Soft delete a record by setting deleted_at."""
        from datetime import datetime

        if not hasattr(self.model, "deleted_at"):
            raise ValueError(f"{self.model.__name__} does not support soft delete")

        instance = await self.get_by_id_and_org(id, organization_id)
        if instance is None:
            return False

        instance.deleted_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def exists(self, **kwargs: Any) -> bool:
        """Check if a record matching the criteria exists."""
        stmt = select(func.count()).select_from(self.model).where(
            *[getattr(self.model, k) == v for k, v in kwargs.items()]
        )
        count = (await self.session.execute(stmt)).scalar() or 0
        return count > 0
