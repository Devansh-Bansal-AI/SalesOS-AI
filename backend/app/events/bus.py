# ============================================================
# SalesOS AI — Event Bus (v2)
#
# Formalized event bus with DDD event categories:
#   Domain Events     → Business state changes (lead.qualified)
#   Application Events → Cross-domain coordination (workflow.step_completed)
#   Integration Events → External system triggers (email.sent)
#
# Features:
#   - PostgreSQL-backed persistence (append-only log)
#   - Handler registration via @on decorator
#   - Event replay for failed handler recovery
#   - Event history queries
# ============================================================

from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.domain_event import DomainEvent

logger = get_logger("event_bus")

# Type alias for async event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]

# Global handler registry
_handlers: dict[str, list[EventHandler]] = defaultdict(list)


# ── Event Categories ────────────────────────────────────────


class EventCategory:
    """DDD event classification.

    Domain Events:      Business state changes within a bounded context.
                        e.g., lead.created, lead.qualified, meeting.scheduled

    Application Events: Cross-domain coordination and orchestration.
                        e.g., workflow.step_completed, decision.evaluated

    Integration Events: External system interactions.
                        e.g., email.sent, calendar.synced, webhook.received
    """
    DOMAIN = "domain"
    APPLICATION = "application"
    INTEGRATION = "integration"


# Classify events by their type prefix
_CATEGORY_MAP: dict[str, str] = {
    "lead.": EventCategory.DOMAIN,
    "company.": EventCategory.DOMAIN,
    "conversation.": EventCategory.DOMAIN,
    "meeting.": EventCategory.DOMAIN,
    "escalation.": EventCategory.DOMAIN,
    "workflow.": EventCategory.APPLICATION,
    "decision.": EventCategory.APPLICATION,
    "agent.": EventCategory.APPLICATION,
    "followup.": EventCategory.APPLICATION,
    "email.": EventCategory.INTEGRATION,
}


def _classify_event(event_type: str) -> str:
    """Classify an event type into its DDD category."""
    for prefix, category in _CATEGORY_MAP.items():
        if event_type.startswith(prefix):
            return category
    return EventCategory.DOMAIN  # Default


# ── Handler Registration ────────────────────────────────────


def on(event_type: str) -> Callable[[EventHandler], EventHandler]:
    """Decorator to register an event handler.

    Usage:
        @on(EventTypes.LEAD_CREATED)
        async def handle_lead_created(event: DomainEvent, session):
            ...
    """
    def decorator(func: EventHandler) -> EventHandler:
        _handlers[event_type].append(func)
        logger.debug("handler_registered", event_type=event_type, handler=func.__name__)
        return func
    return decorator


# ── Publishing ──────────────────────────────────────────────


async def publish(
    session: AsyncSession,
    *,
    event_type: str,
    organization_id: UUID,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: dict,
    metadata: dict | None = None,
) -> DomainEvent:
    """Publish a domain event.

    1. Classifies the event into its DDD category
    2. Persists the event to the domain_events table (append-only log)
    3. Dispatches to all registered in-process handlers

    Args:
        session: Database session for persisting the event
        event_type: Event type string (use EventTypes constants)
        organization_id: Tenant context
        aggregate_type: The entity type this event is about (e.g., "lead")
        aggregate_id: The entity ID this event is about
        payload: Event-specific data
        metadata: Optional context (user_id, source, etc.)
    """
    category = _classify_event(event_type)

    # Enrich metadata with category
    event_metadata = metadata or {}
    event_metadata["event_category"] = category

    # Persist event
    event = DomainEvent(
        organization_id=organization_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
        metadata_=event_metadata,
    )
    session.add(event)
    await session.flush()

    logger.info(
        "event_published",
        event_type=event_type,
        category=category,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
    )

    # Dispatch to handlers
    handlers = _handlers.get(event_type, [])
    for handler in handlers:
        try:
            await handler(event, session)
        except Exception as e:
            logger.error(
                "event_handler_error",
                event_type=event_type,
                handler=handler.__name__,
                error=str(e),
            )
            # Don't fail the parent transaction — log and continue
            continue

    return event


# ── Event Replay ────────────────────────────────────────────


async def replay_event(
    session: AsyncSession,
    event_id: UUID,
    *,
    handler_name: str | None = None,
) -> bool:
    """Replay a persisted event through its handlers.

    Useful for recovering from handler failures without re-publishing.

    Args:
        session: Database session
        event_id: The event to replay
        handler_name: If provided, replay through only this handler

    Returns:
        True if replay was successful
    """
    event = await session.get(DomainEvent, event_id)
    if not event:
        logger.warning("replay_event_not_found", event_id=str(event_id))
        return False

    logger.info(
        "event_replaying",
        event_id=str(event_id),
        event_type=event.event_type,
        handler_filter=handler_name,
    )

    handlers = _handlers.get(event.event_type, [])
    success = True

    for handler in handlers:
        if handler_name and handler.__name__ != handler_name:
            continue

        try:
            await handler(event, session)
        except Exception as e:
            logger.error(
                "event_replay_handler_error",
                event_id=str(event_id),
                handler=handler.__name__,
                error=str(e),
            )
            success = False

    return success


# ── Event History ───────────────────────────────────────────


async def get_event_history(
    session: AsyncSession,
    organization_id: UUID,
    *,
    aggregate_type: str | None = None,
    aggregate_id: UUID | None = None,
    event_type: str | None = None,
    since: datetime | None = None,
    limit: int = 50,
) -> list[DomainEvent]:
    """Query persisted event history.

    Useful for debugging, audit trails, and event sourcing patterns.
    """
    stmt = select(DomainEvent).where(
        DomainEvent.organization_id == organization_id
    )

    if aggregate_type:
        stmt = stmt.where(DomainEvent.aggregate_type == aggregate_type)
    if aggregate_id:
        stmt = stmt.where(DomainEvent.aggregate_id == aggregate_id)
    if event_type:
        stmt = stmt.where(DomainEvent.event_type == event_type)
    if since:
        stmt = stmt.where(DomainEvent.created_at >= since)

    stmt = stmt.order_by(DomainEvent.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())

