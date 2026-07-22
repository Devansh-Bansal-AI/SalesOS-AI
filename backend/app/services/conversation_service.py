# ============================================================
# SalesOS AI — Conversation Service
#
# Manages conversation threads and messages.
# A conversation groups messages into a coherent thread
# regardless of channel (email, chat, sms).
# ============================================================

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversation_repo import ConversationRepository, MessageRepository
from app.schemas.communication import (
    ConversationAnalysis,
    ConversationListResponse,
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.crm_service import CRMService

logger = get_logger("conversation_service")


class ConversationService:
    """Manages conversation threads across all channels."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)
        self.crm = CRMService(session)

    # ── Thread Management ───────────────────────────────

    async def get_or_create_conversation(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        channel: str = "email",
        subject: str | None = None,
    ) -> Conversation:
        """Find the active conversation for a lead, or create one."""
        existing = await self.conv_repo.find_active_by_lead(organization_id, lead_id)
        if existing:
            return existing

        conversation = await self.conv_repo.create(
            organization_id=organization_id,
            lead_id=lead_id,
            channel=channel,
            subject=subject,
            status="active",
            message_count=0,
        )

        logger.info(
            "conversation_created",
            conversation_id=str(conversation.id),
            lead_id=str(lead_id),
            channel=channel,
        )

        return conversation

    async def get_conversation(
        self, organization_id: UUID, conversation_id: UUID
    ) -> ConversationResponse:
        """Get a single conversation by ID."""
        conv = await self.conv_repo.get_by_id_and_org(conversation_id, organization_id)
        if not conv:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Conversation", conversation_id)
        return self._to_response(conv)

    async def list_by_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ConversationListResponse], int]:
        """List conversations for a lead."""
        items, total = await self.conv_repo.find_by_lead(
            organization_id, lead_id, offset=offset, limit=limit
        )
        return [self._to_list_response(c) for c in items], total

    # ── Message Management ──────────────────────────────

    async def add_message(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        request: MessageCreateRequest,
        *,
        agent_run_id: UUID | None = None,
    ) -> MessageResponse:
        """Add a message to a conversation."""
        conversation = await self.conv_repo.get_by_id_and_org(conversation_id, organization_id)
        if not conversation:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Conversation", conversation_id)

        message = await self.msg_repo.create(
            conversation_id=conversation_id,
            organization_id=organization_id,
            direction=request.direction,
            channel=request.channel,
            sender_email=request.sender_email,
            recipient_email=request.recipient_email,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            agent_run_id=agent_run_id,
        )

        # Update conversation stats
        conversation.message_count += 1
        conversation.last_message_at = datetime.now(UTC)
        await self.session.flush()

        # Publish event for inbound messages (triggers analysis)
        if request.direction == "inbound":
            await publish(
                self.session,
                event_type=EventTypes.CONVERSATION_MESSAGE_RECEIVED,
                organization_id=organization_id,
                aggregate_type="conversation",
                aggregate_id=conversation_id,
                payload={
                    "message_id": str(message.id),
                    "lead_id": str(conversation.lead_id),
                    "channel": request.channel,
                    "body_text": request.body_text[:500],
                },
            )

        logger.info(
            "message_added",
            conversation_id=str(conversation_id),
            direction=request.direction,
            channel=request.channel,
        )

        return self._msg_to_response(message)

    async def get_messages(
        self,
        conversation_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[MessageResponse], int]:
        """Get messages in a conversation."""
        items, total = await self.msg_repo.get_conversation_messages(
            conversation_id, offset=offset, limit=limit
        )
        return [self._msg_to_response(m) for m in items], total

    async def get_recent_lead_messages(
        self, organization_id: UUID, lead_id: UUID, *, limit: int = 10
    ) -> list[MessageResponse]:
        """Get recent messages across all conversations for a lead."""
        messages = await self.msg_repo.get_recent_by_lead(organization_id, lead_id, limit=limit)
        return [self._msg_to_response(m) for m in messages]

    # ── Analysis Application ────────────────────────────

    async def apply_analysis(
        self,
        organization_id: UUID,
        message_id: UUID,
        analysis: ConversationAnalysis,
        *,
        agent_run_id: UUID | None = None,
    ) -> None:
        """Apply conversation intelligence analysis to a message."""
        message = await self.session.get(Message, message_id)
        if not message:
            return

        message.analysis = analysis.model_dump()
        if agent_run_id:
            message.agent_run_id = agent_run_id
        await self.session.flush()

        # Publish analysis event
        conv = await self.session.get(Conversation, message.conversation_id)
        if conv:
            await publish(
                self.session,
                event_type=EventTypes.CONVERSATION_ANALYZED,
                organization_id=organization_id,
                aggregate_type="conversation",
                aggregate_id=conv.id,
                payload={
                    "message_id": str(message_id),
                    "lead_id": str(conv.lead_id),
                    "sentiment": analysis.sentiment,
                    "risk_level": analysis.risk_level,
                    "customer_stage": analysis.customer_stage,
                    "next_best_action": analysis.next_best_action,
                    "buying_signals": analysis.buying_signals,
                    "objections": analysis.objections,
                    "competitor_mentions": analysis.competitor_mentions,
                },
            )

        logger.info(
            "analysis_applied",
            message_id=str(message_id),
            sentiment=analysis.sentiment,
            risk=analysis.risk_level,
        )

    # ── Helpers ─────────────────────────────────────────

    def _to_response(self, conv: Conversation) -> ConversationResponse:
        return ConversationResponse(
            id=conv.id,
            lead_id=conv.lead_id,
            status=conv.status,
            channel=conv.channel,
            subject=conv.subject,
            summary=conv.summary,
            message_count=conv.message_count,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    def _to_list_response(self, conv: Conversation) -> ConversationListResponse:
        return ConversationListResponse(
            id=conv.id,
            lead_id=conv.lead_id,
            status=conv.status,
            channel=conv.channel,
            subject=conv.subject,
            message_count=conv.message_count,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
        )

    def _msg_to_response(self, msg: Message) -> MessageResponse:
        return MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            direction=msg.direction,
            channel=msg.channel,
            sender_email=msg.sender_email,
            recipient_email=msg.recipient_email,
            subject=msg.subject,
            body_text=msg.body_text,
            analysis=msg.analysis,
            created_at=msg.created_at,
        )
