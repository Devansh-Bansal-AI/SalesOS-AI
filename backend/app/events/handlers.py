# ============================================================
# SalesOS AI — Event Handlers
#
# Connects domain events to workflow triggers and side effects.
# Handlers are registered with the event bus at startup.
# ============================================================

from app.core.feature_flags import get_feature_flags
from app.core.logging import get_logger
from app.events.bus import on
from app.events.types import EventTypes
from app.models.domain_event import DomainEvent
from app.workflows.engine import get_workflow_engine

logger = get_logger("event_handlers")


@on(EventTypes.LEAD_CREATED)
async def handle_lead_created(event: DomainEvent, session) -> None:
    """When a new lead is created, start the lead lifecycle workflow.

    This is the main entry point for the entire lead pipeline:
      LEAD_CREATED → lead_lifecycle workflow → validate → qualify → enrich → decide
    """
    flags = get_feature_flags()

    lead_id = event.payload.get("lead_id")
    email = event.payload.get("email")

    if not lead_id:
        logger.warning("lead_created_no_id", event_id=str(event.id))
        return

    logger.info(
        "handling_lead_created",
        lead_id=lead_id,
        email=email,
    )

    try:
        from uuid import UUID

        engine = get_workflow_engine()
        await engine.start(
            session,
            "lead_lifecycle",
            organization_id=event.organization_id,
            lead_id=UUID(lead_id),
            initial_state={
                "email": email,
                "source": event.payload.get("source"),
                "company_name": event.payload.get("company_name"),
                "message": event.payload.get("message"),
                "first_name": event.payload.get("first_name"),
                "last_name": event.payload.get("last_name"),
                "job_title": event.payload.get("job_title"),
            },
        )
    except Exception as e:
        logger.error(
            "lead_lifecycle_start_failed",
            lead_id=lead_id,
            error=str(e),
        )


@on(EventTypes.LEAD_QUALIFICATION_COMPLETED)
async def handle_qualification_completed(event: DomainEvent, session) -> None:
    """Log qualification completion for observability."""
    logger.info(
        "qualification_completed",
        lead_id=str(event.aggregate_id),
        score=event.payload.get("score"),
        priority=event.payload.get("priority"),
        intent=event.payload.get("intent"),
    )


@on(EventTypes.LEAD_ENRICHMENT_COMPLETED)
async def handle_enrichment_completed(event: DomainEvent, session) -> None:
    """Log enrichment completion for observability."""
    logger.info(
        "enrichment_completed",
        lead_id=str(event.aggregate_id),
        data_points=event.payload.get("data_points"),
        company=event.payload.get("company"),
    )


@on(EventTypes.LEAD_STATUS_CHANGED)
async def handle_status_changed(event: DomainEvent, session) -> None:
    """Track lead status transitions for analytics."""
    logger.info(
        "lead_status_changed",
        lead_id=str(event.aggregate_id),
        old_status=event.payload.get("old_status"),
        new_status=event.payload.get("new_status"),
    )


@on(EventTypes.LEAD_DUPLICATE_DETECTED)
async def handle_duplicate_detected(event: DomainEvent, session) -> None:
    """Track duplicate lead submissions for analytics."""
    logger.info(
        "duplicate_lead_detected",
        existing_lead_id=event.payload.get("existing_lead_id"),
        new_email=event.payload.get("new_email"),
        new_source=event.payload.get("new_source"),
    )


def register_event_handlers() -> None:
    """Import this module to register all event handlers.

    Called from app startup (main.py lifespan).
    The @on decorators auto-register when the module is imported.
    """
    logger.info("event_handlers_registered")
