# ============================================================
# SalesOS AI — Conversation & Communication API Routes
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_perm
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.communication import (
    ConversationListResponse,
    ConversationResponse,
    EmailResponse,
    EmailSendRequest,
    InboundEmailPayload,
    MessageResponse,
)

router = APIRouter(tags=["Communication"])
logger = get_logger("api.conversations")


# ── Conversations ───────────────────────────────────────────


@router.get(
    "/leads/{lead_id}/conversations",
    response_model=APIResponse[list[ConversationListResponse]],
    dependencies=[Depends(require_perm("conversations:read"))],
)
async def list_lead_conversations(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all conversations for a lead."""
    from app.services.conversation_service import ConversationService

    service = ConversationService(db)
    offset = (page - 1) * per_page
    items, total = await service.list_by_lead(
        user.organization_id, lead_id, offset=offset, limit=per_page
    )
    total_pages = (total + per_page - 1) // per_page
    return APIResponse(
        data=items,
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=APIResponse[ConversationResponse],
    dependencies=[Depends(require_perm("conversations:read"))],
)
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single conversation with metadata."""
    from app.services.conversation_service import ConversationService

    service = ConversationService(db)
    result = await service.get_conversation(user.organization_id, conversation_id)
    return APIResponse(data=result)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=APIResponse[list[MessageResponse]],
    dependencies=[Depends(require_perm("conversations:read"))],
)
async def get_conversation_messages(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    """Get messages in a conversation."""
    from app.services.conversation_service import ConversationService

    service = ConversationService(db)
    offset = (page - 1) * per_page
    items, total = await service.get_messages(conversation_id, offset=offset, limit=per_page)
    total_pages = (total + per_page - 1) // per_page
    return APIResponse(
        data=items,
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    )


# ── Email ───────────────────────────────────────────────────


@router.post(
    "/emails/send",
    response_model=APIResponse[EmailResponse],
    status_code=201,
    dependencies=[Depends(require_perm("emails:send"))],
)
async def send_email(
    request: EmailSendRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send an email to a lead. Creates conversation thread if needed."""
    from app.services.communication_service import CommunicationService

    service = CommunicationService(db)
    result = await service.send_email(user.organization_id, request)
    return APIResponse(data=result)


# ── Inbound Webhook ─────────────────────────────────────────


@router.post(
    "/webhooks/email/inbound",
    response_model=APIResponse,
    status_code=200,
)
async def receive_inbound_email(
    payload: InboundEmailPayload,
    db: AsyncSession = Depends(get_db),
):
    """Receive an inbound email from an email provider webhook.

    Matches the sender to a lead, creates/updates conversation,
    records the message, and triggers conversation analysis.

    This endpoint does NOT require JWT auth — it uses webhook
    signature validation (provider-specific, added in production).
    """
    # FIXME(v1.1): Validate webhook signature per provider (SendGrid, Postmark, etc.)
    # Currently no signature verification — all inbound emails are processed.
    # In production, implement HMAC/RSA signature validation before processing.
    logger.warning("webhook_signature_not_validated", provider="email")

    # Resolve organization from the to_email domain
    # In production, this would be a lookup table mapping
    # receiving addresses to organizations
    from app.core.config import get_settings
    from app.services.communication_service import CommunicationService

    settings = get_settings()

    # FIXME(v1.1): Resolve organization_id from to_email domain.
    # Requires an org-email mapping table (e.g., org_email_domains).
    # Until then, inbound webhooks cannot route to the correct tenant.
    service = CommunicationService(db)

    # Process the inbound message
    # The conversation event handler will trigger analysis
    message_id = await service.process_inbound_email(
        # FIXME(v1.1): organization_id must come from domain lookup
        organization_id=None,  # type: ignore
        from_email=payload.from_email,
        to_email=payload.to_email,
        subject=payload.subject,
        body_text=payload.body_text,
        body_html=payload.body_html,
        message_id=payload.message_id,
        in_reply_to=payload.in_reply_to,
    )

    return APIResponse(data={"message_id": str(message_id)})
