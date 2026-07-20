# ============================================================
# SalesOS AI — CRM Service (Activity Logging)
#
# Records every meaningful interaction on a lead's timeline.
# This is the source of truth for "what happened to this lead."
# ============================================================

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.activity_repo import ActivityRepository

logger = get_logger("crm_service")


class CRMService:
    """Records lead activities for CRM timeline and analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.activity_repo = ActivityRepository(session)

    async def log_activity(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        activity_type: str,
        title: str,
        description: str | None = None,
        metadata: dict | None = None,
        performed_by: UUID | None = None,
    ) -> None:
        """Log a single activity on a lead's timeline.

        activity_type should be one of:
          lead_created, lead_qualified, lead_enriched, lead_scored,
          lead_assigned, lead_status_changed, email_sent, email_opened,
          email_replied, meeting_scheduled, meeting_completed,
          note_added, call_logged, followup_scheduled, followup_sent
        """
        await self.activity_repo.create(
            organization_id=organization_id,
            lead_id=lead_id,
            activity_type=activity_type,
            title=title,
            description=description,
            metadata_=metadata or {},
            user_id=performed_by,
        )

        logger.info(
            "activity_logged",
            lead_id=str(lead_id),
            type=activity_type,
            title=title,
        )

    async def log_lead_created(
        self, organization_id: UUID, lead_id: UUID, source: str, email: str
    ) -> None:
        await self.log_activity(
            organization_id,
            lead_id,
            activity_type="lead_created",
            title=f"Lead created from {source}",
            description=f"New lead {email} submitted via {source}",
            metadata={"source": source, "email": email},
        )

    async def log_lead_qualified(
        self,
        organization_id: UUID,
        lead_id: UUID,
        score: int,
        priority: str,
        intent: str,
    ) -> None:
        await self.log_activity(
            organization_id,
            lead_id,
            activity_type="lead_qualified",
            title=f"Qualified: {priority} priority (score {score})",
            description=f"AI qualification: {intent} intent, score {score}/100",
            metadata={"score": score, "priority": priority, "intent": intent},
        )

    async def log_lead_enriched(
        self,
        organization_id: UUID,
        lead_id: UUID,
        company_name: str | None,
        data_points: int,
    ) -> None:
        await self.log_activity(
            organization_id,
            lead_id,
            activity_type="lead_enriched",
            title=f"Enriched with {data_points} data points",
            description=f"Company: {company_name or 'Unknown'}",
            metadata={"company": company_name, "data_points": data_points},
        )

    async def log_lead_assigned(
        self,
        organization_id: UUID,
        lead_id: UUID,
        assigned_to: UUID,
        assigned_by: UUID | None,
    ) -> None:
        await self.log_activity(
            organization_id,
            lead_id,
            activity_type="lead_assigned",
            title="Lead assigned",
            metadata={"assigned_to": str(assigned_to)},
            performed_by=assigned_by,
        )

    async def log_status_change(
        self,
        organization_id: UUID,
        lead_id: UUID,
        old_status: str,
        new_status: str,
        changed_by: UUID | None = None,
    ) -> None:
        await self.log_activity(
            organization_id,
            lead_id,
            activity_type="lead_status_changed",
            title=f"Status: {old_status} → {new_status}",
            metadata={"old_status": old_status, "new_status": new_status},
            performed_by=changed_by,
        )

    async def get_timeline(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ):
        """Get the activity timeline for a lead."""
        return await self.activity_repo.get_lead_timeline(
            organization_id, lead_id, offset=offset, limit=limit
        )
