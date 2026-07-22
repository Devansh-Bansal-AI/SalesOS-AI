# ============================================================
# SalesOS AI — Conversation Repository
# ============================================================

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def find_active_by_lead(
        self, organization_id: UUID, lead_id: UUID
    ) -> Conversation | None:
        """Find the most recent active conversation for a lead."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.lead_id == lead_id,
                Conversation.status.in_(["active", "waiting"]),
            )
            .order_by(Conversation.last_message_at.desc().nullsfirst())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Conversation], int]:
        """List all conversations for a lead."""
        filters = [Conversation.lead_id == lead_id]
        items, total = await self.list(organization_id, offset=offset, limit=limit, filters=filters)
        return list(items), total

    async def get_with_messages(
        self, organization_id: UUID, conversation_id: UUID
    ) -> Conversation | None:
        """Get a conversation with all its messages loaded."""
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Message], int]:
        """Get messages for a conversation, ordered chronologically."""
        count_stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_recent_by_lead(
        self, organization_id: UUID, lead_id: UUID, *, limit: int = 10
    ) -> list[Message]:
        """Get recent messages across all conversations for a lead."""
        from app.models.conversation import Conversation

        stmt = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.lead_id == lead_id,
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
