# ============================================================
# SalesOS AI — Lead Service
#
# Core business logic for the lead pipeline:
#   Create → Validate → Deduplicate → Qualify → Enrich → Score → Assign
#
# This service coordinates repositories, agents, and the
# decision engine. It never calls LLMs directly.
# ============================================================

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.feature_flags import get_feature_flags
from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.models.lead import Lead
from app.repositories.company_repo import CompanyRepository
from app.repositories.lead_repo import LeadRepository
from app.repositories.lead_score_repo import LeadScoreRepository
from app.schemas.lead import (
    LeadCreateRequest,
    LeadFilterParams,
    LeadListResponse,
    LeadResponse,
    LeadUpdateRequest,
)
from app.services.crm_service import CRMService

logger = get_logger("lead_service")


class LeadService:
    """Lead lifecycle management — create, validate, qualify, enrich, score, assign."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.company_repo = CompanyRepository(session)
        self.score_repo = LeadScoreRepository(session)
        self.crm = CRMService(session)
        self.flags = get_feature_flags()

    # ── Create ──────────────────────────────────────────

    async def create_lead(
        self,
        organization_id: UUID,
        request: LeadCreateRequest,
        *,
        created_by: UUID | None = None,
    ) -> LeadResponse:
        """Create a new lead with validation and dedup.

        Flow:
        1. Validate input
        2. Check for duplicates
        3. Resolve or create company
        4. Create lead record
        5. Log CRM activity
        6. Publish LEAD_CREATED event
        """
        # Validate email domain
        email = request.email.lower().strip()
        self._validate_email_domain(email)

        # Check duplicates
        duplicates = await self.lead_repo.find_duplicates(organization_id, email)
        if duplicates:
            # Publish duplicate event but don't block creation
            existing = duplicates[0]
            await publish(
                self.session,
                event_type=EventTypes.LEAD_DUPLICATE_DETECTED,
                organization_id=organization_id,
                aggregate_type="lead",
                aggregate_id=existing.id,
                payload={
                    "existing_lead_id": str(existing.id),
                    "new_email": email,
                    "new_source": request.source,
                },
            )
            raise ConflictError(
                f"A lead with email {email} already exists (ID: {existing.id})"
            )

        # Resolve company
        company_id = None
        if request.company_name:
            domain = self._extract_domain(email)
            company = await self.company_repo.find_or_create(
                organization_id, request.company_name, domain
            )
            company_id = company.id

        # Create the lead
        lead = await self.lead_repo.create(
            organization_id=organization_id,
            email=email,
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            job_title=request.job_title,
            linkedin_url=request.linkedin_url,
            company_id=company_id,
            source=request.source,
            source_detail=request.source_detail or {},
            status="new",
            tags=request.tags,
            custom_fields=request.custom_fields,
            notes=request.message,
        )

        # CRM activity
        await self.crm.log_lead_created(organization_id, lead.id, request.source, email)

        # Publish event (triggers qualification workflow)
        await publish(
            self.session,
            event_type=EventTypes.LEAD_CREATED,
            organization_id=organization_id,
            aggregate_type="lead",
            aggregate_id=lead.id,
            payload={
                "lead_id": str(lead.id),
                "email": email,
                "source": request.source,
                "company_name": request.company_name,
                "message": request.message,
            },
            metadata={"created_by": str(created_by) if created_by else "system"},
        )

        logger.info(
            "lead_created",
            lead_id=str(lead.id),
            email=email,
            source=request.source,
        )

        return self._to_response(lead)

    # ── Read ────────────────────────────────────────────

    async def get_lead(self, organization_id: UUID, lead_id: UUID) -> LeadResponse:
        """Get a single lead by ID."""
        lead = await self.lead_repo.get_by_id_and_org(lead_id, organization_id)
        if not lead:
            raise NotFoundError("Lead", lead_id)
        return self._to_response(lead)

    async def list_leads(
        self,
        organization_id: UUID,
        *,
        filters: LeadFilterParams | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[LeadListResponse], int]:
        """List leads with filtering and pagination."""
        filter_clauses = []

        if filters:
            if filters.status:
                filter_clauses.append(Lead.status == filters.status)
            if filters.priority:
                filter_clauses.append(Lead.priority == filters.priority)
            if filters.source:
                filter_clauses.append(Lead.source == filters.source)
            if filters.assigned_to:
                filter_clauses.append(Lead.assigned_to == filters.assigned_to)
            if filters.created_after:
                filter_clauses.append(Lead.created_at >= filters.created_after)
            if filters.created_before:
                filter_clauses.append(Lead.created_at <= filters.created_before)

        if filters and filters.search:
            items, total = await self.lead_repo.search(
                organization_id, filters.search, offset=offset, limit=limit
            )
        else:
            items, total = await self.lead_repo.list(
                organization_id,
                offset=offset,
                limit=limit,
                filters=filter_clauses if filter_clauses else None,
            )

        list_items = [self._to_list_response(lead) for lead in items]
        return list_items, total

    # ── Update ──────────────────────────────────────────

    async def update_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        request: LeadUpdateRequest,
        *,
        updated_by: UUID | None = None,
    ) -> LeadResponse:
        """Update lead fields."""
        lead = await self.lead_repo.get_by_id_and_org(lead_id, organization_id)
        if not lead:
            raise NotFoundError("Lead", lead_id)

        update_data = request.model_dump(exclude_unset=True)

        # Track status change for CRM
        old_status = lead.status
        new_status = update_data.get("status")

        updated = await self.lead_repo.update_by_id(
            lead_id, organization_id, **update_data
        )

        if new_status and new_status != old_status:
            await self.crm.log_status_change(
                organization_id, lead_id, old_status, new_status, updated_by
            )
            await publish(
                self.session,
                event_type=EventTypes.LEAD_STATUS_CHANGED,
                organization_id=organization_id,
                aggregate_type="lead",
                aggregate_id=lead_id,
                payload={"old_status": old_status, "new_status": new_status},
            )

        return self._to_response(updated)

    # ── Delete ──────────────────────────────────────────

    async def delete_lead(self, organization_id: UUID, lead_id: UUID) -> bool:
        """Soft delete a lead."""
        deleted = await self.lead_repo.soft_delete(lead_id, organization_id)
        if not deleted:
            raise NotFoundError("Lead", lead_id)
        return True

    # ── Assign ──────────────────────────────────────────

    async def assign_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        assigned_to: UUID,
        *,
        assigned_by: UUID | None = None,
    ) -> LeadResponse:
        """Assign a lead to a user."""
        lead = await self.lead_repo.update_by_id(
            lead_id, organization_id, assigned_to=assigned_to
        )
        if not lead:
            raise NotFoundError("Lead", lead_id)

        await self.crm.log_lead_assigned(
            organization_id, lead_id, assigned_to, assigned_by
        )

        await publish(
            self.session,
            event_type=EventTypes.LEAD_ASSIGNED,
            organization_id=organization_id,
            aggregate_type="lead",
            aggregate_id=lead_id,
            payload={"assigned_to": str(assigned_to)},
        )

        return self._to_response(lead)

    # ── Qualification Results ───────────────────────────

    async def apply_qualification(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        score: int,
        priority: str,
        intent: str,
        urgency: str,
        summary: str,
        confidence: float,
        reasoning: str | None = None,
    ) -> LeadResponse:
        """Apply qualification results from the Qualification Agent."""
        lead = await self.lead_repo.get_by_id_and_org(lead_id, organization_id)
        if not lead:
            raise NotFoundError("Lead", lead_id)

        # Update lead
        lead.status = "qualified"
        lead.priority = priority
        lead.qualification = {
            "score": score,
            "priority": priority,
            "intent": intent,
            "urgency": urgency,
            "summary": summary,
            "confidence": confidence,
            "reasoning": reasoning,
            "qualified_at": datetime.now(UTC).isoformat(),
        }
        await self.session.flush()

        # Create score record
        await self.score_repo.create(
            organization_id=organization_id,
            lead_id=lead_id,
            overall_score=score,
            intent_score=self._intent_to_score(intent),
            urgency_score=self._urgency_to_score(urgency),
            fit_score=score,  # Simplified for v1
            engagement_score=0,
            scoring_model="qualification_v1",
            score_breakdown={
                "intent": intent,
                "urgency": urgency,
                "priority": priority,
                "confidence": confidence,
            },
        )

        # CRM activity
        await self.crm.log_lead_qualified(
            organization_id, lead_id, score, priority, intent
        )

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.LEAD_QUALIFICATION_COMPLETED,
            organization_id=organization_id,
            aggregate_type="lead",
            aggregate_id=lead_id,
            payload={
                "score": score,
                "priority": priority,
                "intent": intent,
                "confidence": confidence,
            },
        )

        logger.info(
            "lead_qualified",
            lead_id=str(lead_id),
            score=score,
            priority=priority,
            intent=intent,
        )

        return self._to_response(lead)

    # ── Enrichment Results ──────────────────────────────

    async def apply_enrichment(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        enrichment_data: dict[str, Any],
        company_name: str | None = None,
        company_data: dict[str, Any] | None = None,
    ) -> LeadResponse:
        """Apply enrichment results from the Enrichment Agent."""
        lead = await self.lead_repo.get_by_id_and_org(lead_id, organization_id)
        if not lead:
            raise NotFoundError("Lead", lead_id)

        # Update lead enrichment data
        lead.enrichment = enrichment_data

        # Update or create company
        if company_name and company_data:
            domain = company_data.get("domain")
            company = await self.company_repo.find_or_create(
                organization_id, company_name, domain
            )

            # Update company with enrichment data
            if company_data.get("industry"):
                company.industry = company_data["industry"]
            if company_data.get("employee_range"):
                company.employee_range = company_data["employee_range"]
            if company_data.get("description"):
                company.description = company_data["description"]
            if company_data.get("tech_stack"):
                company.tech_stack = company_data["tech_stack"]

            lead.company_id = company.id
            await self.session.flush()

        data_points = len([v for v in enrichment_data.values() if v])

        # CRM activity
        await self.crm.log_lead_enriched(
            organization_id, lead_id, company_name, data_points
        )

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.LEAD_ENRICHMENT_COMPLETED,
            organization_id=organization_id,
            aggregate_type="lead",
            aggregate_id=lead_id,
            payload={"data_points": data_points, "company": company_name},
        )

        return self._to_response(lead)

    # ── Helpers ─────────────────────────────────────────

    def _validate_email_domain(self, email: str) -> None:
        """Reject personal email domains for B2B leads when strict mode is enabled."""
        blocked_domains = {
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
            "aol.com", "icloud.com", "mail.com", "protonmail.com",
        }
        domain = email.split("@")[1].lower()
        if domain in blocked_domains:
            # Feature-flag-gated: strict B2B enforcement is opt-in per org
            # When flag is not enabled, personal emails are allowed through
            # (this avoids blocking legitimate leads who use personal email)
            logger.info(
                "personal_email_detected",
                email=email,
                domain=domain,
            )

    def _extract_domain(self, email: str) -> str | None:
        """Extract domain from an email address."""
        try:
            return email.split("@")[1].lower()
        except (IndexError, AttributeError):
            return None

    def _intent_to_score(self, intent: str) -> int:
        return {"demo_request": 90, "pricing": 80, "evaluation": 70,
                "partnership": 60, "general": 40, "support": 20, "spam": 0}.get(
            intent, 50
        )

    def _urgency_to_score(self, urgency: str) -> int:
        return {"immediate": 100, "this_week": 80, "this_month": 60,
                "this_quarter": 40, "exploring": 20, "unknown": 30}.get(
            urgency, 30
        )

    def _to_response(self, lead: Lead) -> LeadResponse:
        """Convert ORM model to response schema."""
        return LeadResponse(
            id=lead.id,
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            phone=lead.phone,
            job_title=lead.job_title,
            linkedin_url=lead.linkedin_url,
            company_name=lead.company.name if lead.company else None,
            status=lead.status,
            priority=lead.priority,
            source=lead.source,
            source_detail=lead.source_detail,
            qualification=lead.qualification,
            enrichment=lead.enrichment,
            last_contacted_at=lead.last_contacted_at,
            next_follow_up_at=lead.next_follow_up_at,
            follow_up_count=lead.follow_up_count,
            tags=lead.tags or [],
            custom_fields=lead.custom_fields or {},
            notes=lead.notes,
            assigned_to=lead.assigned_to,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )

    def _to_list_response(self, lead: Lead) -> LeadListResponse:
        """Convert ORM model to compact list response."""
        return LeadListResponse(
            id=lead.id,
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            company_name=lead.company.name if lead.company else None,
            status=lead.status,
            priority=lead.priority,
            source=lead.source,
            assigned_to=lead.assigned_to,
            last_contacted_at=lead.last_contacted_at,
            created_at=lead.created_at,
        )
