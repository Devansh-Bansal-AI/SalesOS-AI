# ============================================================
# SalesOS AI — Unit Tests: Event Bus
# Tests handler registration (@on decorator), publishing, and categorization.
# ============================================================

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.events.bus import EventCategory, _classify_event, _handlers, on, publish


@pytest.mark.asyncio
async def test_event_category_classification():
    """Test DDD event category classification."""
    assert _classify_event("lead.created") == EventCategory.DOMAIN
    assert _classify_event("workflow.started") == EventCategory.APPLICATION
    assert _classify_event("email.sent") == EventCategory.INTEGRATION


@pytest.mark.asyncio
async def test_event_pub_sub():
    """Test subscribing to an event and publishing it."""
    received_events = []

    @on("lead.test_event")
    async def sample_handler(event, session):
        received_events.append(event)

    org_id = uuid4()
    lead_id = uuid4()

    mock_session = AsyncMock()

    await publish(
        mock_session,
        event_type="lead.test_event",
        organization_id=org_id,
        aggregate_type="lead",
        aggregate_id=lead_id,
        payload={"status": "new"},
    )

    assert len(received_events) == 1
    assert received_events[0].event_type == "lead.test_event"
    assert received_events[0].organization_id == org_id

    _handlers["lead.test_event"].clear()
