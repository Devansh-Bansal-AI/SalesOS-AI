# ============================================================
# SalesOS AI — Communication Service
#
# CRITICAL DESIGN DECISION:
#   Email is ONE channel. This service abstracts communication
#   so that Slack, WhatsApp, SMS, Teams can be plugged in later
#   without changing agents or workflows.
#
#   Agent → CommunicationService.send() → Provider Registry → Channel
#
# The Communication Service:
# - Resolves the correct channel provider
# - Records the message in the conversation thread
# - Creates the Email/SMS/etc. delivery record
# - Tracks delivery status
# ============================================================

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.integrations import (
    EmailMessage,
    EmailProvider,
    get_registry,
)
from app.models.email import Email
from app.repositories.email_repo import EmailRepository
from app.schemas.communication import (
    EmailResponse,
    EmailSendRequest,
    MessageCreateRequest,
)
from app.services.conversation_service import ConversationService
from app.services.crm_service import CRMService

logger = get_logger("communication_service")


class CommunicationService:
    """Multi-channel communication orchestrator.

    Usage:
        comm = CommunicationService(session)
        email_response = await comm.send_email(org_id, request)
        # Internally: resolve provider → send → record → track
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.email_repo = EmailRepository(session)
        self.conv_service = ConversationService(session)
        self.crm = CRMService(session)
        self._registry = get_registry()

    # ── Email Channel ───────────────────────────────────

    async def send_email(
        self,
        organization_id: UUID,
        request: EmailSendRequest,
        *,
        provider_name: str | None = None,
        agent_run_id: UUID | None = None,
        generated_by: str | None = None,
        sequence_id: UUID | None = None,
        sequence_step: int | None = None,
    ) -> EmailResponse:
        """Send an email through the provider registry.

        Flow:
        1. Get or create conversation thread
        2. Create email record (status=sending)
        3. Resolve email provider
        4. Send via provider
        5. Update delivery status
        6. Record message in conversation
        7. Log CRM activity
        8. Publish EMAIL_SENT event
        """
        # Get lead email
        from app.repositories.lead_repo import LeadRepository

        lead_repo = LeadRepository(self.session)
        lead = await lead_repo.get_by_id_and_org(request.lead_id, organization_id)
        if not lead:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Lead", request.lead_id)

        to_email = lead.email
        from_email = request.from_email or self._get_default_from_email()

        # Get or create conversation
        conversation = await self.conv_service.get_or_create_conversation(
            organization_id,
            request.lead_id,
            channel="email",
            subject=request.subject,
        )

        # Create email record
        email = await self.email_repo.create(
            organization_id=organization_id,
            lead_id=request.lead_id,
            conversation_id=conversation.id,
            sequence_id=sequence_id,
            sequence_step=sequence_step,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            from_email=from_email,
            to_email=to_email,
            reply_to=request.reply_to,
            status="sending",
            generated_by=generated_by,
            agent_run_id=agent_run_id,
        )

        # Handle scheduled sends
        if request.schedule_for and request.schedule_for > datetime.now(UTC):
            email.status = "scheduled"
            email.scheduled_for = request.schedule_for
            await self.session.flush()

            logger.info(
                "email_scheduled",
                email_id=str(email.id),
                scheduled_for=request.schedule_for.isoformat(),
            )

            return self._email_to_response(email)

        # Resolve provider and send
        try:
            provider: EmailProvider = self._registry.get_email(provider_name)

            message = EmailMessage(
                to=to_email,
                subject=request.subject,
                body_text=request.body_text,
                body_html=request.body_html,
                from_email=from_email,
                reply_to=request.reply_to,
            )

            result = await provider.send(message)

            if result.success:
                email.status = "sent"
                email.provider = result.provider
                email.provider_id = result.message_id
                email.sent_at = datetime.now(UTC)
            else:
                email.status = "failed"
                email.error_message = result.error

            await self.session.flush()

        except ValueError:
            # No email provider registered — mark as queued
            email.status = "queued"
            await self.session.flush()

            logger.warning("no_email_provider", email_id=str(email.id))

            return self._email_to_response(email)

        except Exception as e:
            email.status = "failed"
            email.error_message = str(e)
            await self.session.flush()

            logger.error(
                "email_send_failed",
                email_id=str(email.id),
                error=str(e),
            )
            raise ExternalServiceError("email", str(e))

        # Record outbound message in conversation
        await self.conv_service.add_message(
            organization_id,
            conversation.id,
            MessageCreateRequest(
                direction="outbound",
                channel="email",
                sender_email=from_email,
                recipient_email=to_email,
                subject=request.subject,
                body_text=request.body_text,
                body_html=request.body_html,
            ),
            agent_run_id=agent_run_id,
        )

        # CRM activity
        await self.crm.log_activity(
            organization_id,
            request.lead_id,
            activity_type="email_sent",
            title=f"Email sent: {request.subject}",
            metadata={
                "email_id": str(email.id),
                "subject": request.subject,
                "provider": email.provider,
            },
        )

        # Update lead contact timestamp
        lead.last_contacted_at = datetime.now(UTC)
        await self.session.flush()

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.EMAIL_SENT,
            organization_id=organization_id,
            aggregate_type="email",
            aggregate_id=email.id,
            payload={
                "lead_id": str(request.lead_id),
                "to": to_email,
                "subject": request.subject,
                "provider": email.provider,
            },
        )

        logger.info(
            "email_sent",
            email_id=str(email.id),
            to=to_email,
            provider=email.provider,
        )

        return self._email_to_response(email)

    # ── Inbound Processing ──────────────────────────────

    async def process_inbound_email(
        self,
        organization_id: UUID,
        *,
        from_email: str,
        to_email: str,
        subject: str | None,
        body_text: str,
        body_html: str | None = None,
        message_id: str | None = None,
        in_reply_to: str | None = None,
    ) -> UUID:
        """Process an inbound email from a webhook.

        Flow:
        1. Find lead by email
        2. Get or create conversation
        3. Record message
        4. Update lead contact time
        5. Publish event (triggers conversation analysis)
        """
        from app.repositories.lead_repo import LeadRepository

        lead_repo = LeadRepository(self.session)
        lead = await lead_repo.find_by_email(organization_id, from_email)

        if not lead:
            logger.warning("inbound_email_no_lead", from_email=from_email)
            # Create minimal lead for unknown senders
            from app.schemas.lead import LeadCreateRequest
            from app.services.lead_service import LeadService

            lead_service = LeadService(self.session)
            lead_response = await lead_service.create_lead(
                organization_id,
                LeadCreateRequest(
                    email=from_email,
                    source="email",
                    message=body_text[:500] if body_text else None,
                ),
            )
            lead = await lead_repo.get_by_id_and_org(lead_response.id, organization_id)

        conversation = await self.conv_service.get_or_create_conversation(
            organization_id,
            lead.id,
            channel="email",
            subject=subject,
        )

        msg_response = await self.conv_service.add_message(
            organization_id,
            conversation.id,
            MessageCreateRequest(
                direction="inbound",
                channel="email",
                sender_email=from_email,
                recipient_email=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
            ),
        )

        # Update lead
        lead.last_contacted_at = datetime.now(UTC)
        await self.session.flush()

        logger.info(
            "inbound_email_processed",
            lead_id=str(lead.id),
            from_email=from_email,
            conversation_id=str(conversation.id),
        )

        return msg_response.id

    # ── Helpers ─────────────────────────────────────────

    def _get_default_from_email(self) -> str:
        from app.core.config import get_settings

        return get_settings().SMTP_FROM_EMAIL

    def _email_to_response(self, email: Email) -> EmailResponse:
        return EmailResponse(
            id=email.id,
            lead_id=email.lead_id,
            conversation_id=email.conversation_id,
            subject=email.subject,
            body_text=email.body_text,
            from_email=email.from_email,
            to_email=email.to_email,
            status=email.status,
            provider=email.provider,
            sent_at=email.sent_at,
            delivered_at=email.delivered_at,
            opened_at=email.opened_at,
            created_at=email.created_at,
        )
