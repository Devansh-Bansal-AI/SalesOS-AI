# ============================================================
# SalesOS AI — PostgreSQL CRM Tool Provider
# ============================================================

from typing import Any
from uuid import UUID

from app.agents.tools import CRMContact, CRMToolProvider, current_org_id, current_session
from app.repositories.lead_repo import LeadRepository
from app.schemas.lead import LeadCreateRequest, LeadUpdateRequest
from app.services.lead_service import LeadService


class PostgresCRMProvider(CRMToolProvider):
    """Concrete implementation of CRMToolProvider using PostgreSQL database."""

    def _get_context(self) -> tuple[Any, UUID]:
        session = current_session.get()
        org_id = current_org_id.get()
        if not session or not org_id:
            raise RuntimeError("Database session or Organization ID not found in context")
        return session, org_id

    async def find_contact(self, email: str) -> CRMContact | None:
        """Look up an existing contact by email."""
        session, org_id = self._get_context()
        lead_repo = LeadRepository(session)
        lead = await lead_repo.find_by_email(org_id, email)
        if not lead:
            return None
        return CRMContact(
            id=str(lead.id),
            email=lead.email,
            name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
            company=lead.company.name if lead.company else None,
            status=lead.status,
            last_contacted=lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
            metadata={
                "source": lead.source,
                "qualification": lead.qualification,
                "enrichment": lead.enrichment,
            }
        )

    async def create_contact(self, data: dict[str, Any]) -> CRMContact:
        """Create a new CRM contact (Lead)."""
        session, org_id = self._get_context()
        req = LeadCreateRequest(
            email=data["email"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            company_name=data.get("company_name"),
            phone=data.get("phone"),
            job_title=data.get("job_title"),
            linkedin_url=data.get("linkedin_url"),
            source=data.get("source", "api"),
            source_detail=data.get("source_detail"),
            message=data.get("message"),
            tags=data.get("tags", []),
            custom_fields=data.get("custom_fields", {}),
        )
        lead_service = LeadService(session)
        lead_response = await lead_service.create_lead(org_id, req)

        # Get lead model to retrieve fully populated company
        lead_repo = LeadRepository(session)
        lead = await lead_repo.get_by_id_and_org(lead_response.id, org_id)
        if not lead:
            raise RuntimeError(f"Created lead {lead_response.id} not found")

        return CRMContact(
            id=str(lead.id),
            email=lead.email,
            name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
            company=lead.company.name if lead.company else None,
            status=lead.status,
            last_contacted=lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
            metadata={
                "source": lead.source,
                "qualification": lead.qualification,
                "enrichment": lead.enrichment,
            }
        )

    async def update_contact(self, id: str, data: dict[str, Any]) -> CRMContact:
        """Update an existing CRM contact."""
        session, org_id = self._get_context()
        lead_id = UUID(id)
        req = LeadUpdateRequest(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone=data.get("phone"),
            job_title=data.get("job_title"),
            linkedin_url=data.get("linkedin_url"),
            status=data.get("status"),
            priority=data.get("priority"),
            tags=data.get("tags"),
            custom_fields=data.get("custom_fields"),
            notes=data.get("notes"),
        )
        lead_service = LeadService(session)
        await lead_service.update_lead(org_id, lead_id, req)

        # Get updated lead model to retrieve company
        lead_repo = LeadRepository(session)
        lead = await lead_repo.get_by_id_and_org(lead_id, org_id)
        if not lead:
            raise RuntimeError(f"Updated lead {lead_id} not found")

        return CRMContact(
            id=str(lead.id),
            email=lead.email,
            name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
            company=lead.company.name if lead.company else None,
            status=lead.status,
            last_contacted=lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
            metadata={
                "source": lead.source,
                "qualification": lead.qualification,
                "enrichment": lead.enrichment,
            }
        )

    async def get_interaction_history(self, email: str) -> list[dict[str, Any]]:
        """Get interaction history (activities + messages) for a contact."""
        session, org_id = self._get_context()
        lead_repo = LeadRepository(session)
        lead = await lead_repo.find_by_email(org_id, email)
        if not lead:
            return []

        from sqlalchemy import select

        from app.models.activity import Activity
        from app.models.conversation import Conversation
        from app.models.message import Message

        # Fetch activities
        act_stmt = select(Activity).where(
            Activity.organization_id == org_id,
            Activity.lead_id == lead.id
        ).order_by(Activity.created_at.desc())
        act_res = await session.execute(act_stmt)
        activities = act_res.scalars().all()

        history = []
        for act in activities:
            history.append({
                "type": "activity",
                "subtype": act.activity_type,
                "timestamp": act.created_at.isoformat(),
                "summary": act.title,
                "description": act.description,
                "metadata": act.metadata_,
            })

        # Fetch messages
        msg_stmt = select(Message).join(Conversation).where(
            Conversation.organization_id == org_id,
            Conversation.lead_id == lead.id
        ).order_by(Message.created_at.desc())
        msg_res = await session.execute(msg_stmt)
        messages = msg_res.scalars().all()

        for msg in messages:
            history.append({
                "type": "message",
                "subtype": msg.direction,
                "timestamp": msg.created_at.isoformat(),
                "summary": f"Subject: {msg.subject}" if msg.subject else f"Message via {msg.channel}",
                "description": msg.body_text,
                "metadata": {
                    "channel": msg.channel,
                    "sender": msg.sender_email,
                    "recipient": msg.recipient_email,
                }
            })

        # Sort history by timestamp descending
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return history
