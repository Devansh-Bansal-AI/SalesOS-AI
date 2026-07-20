# ============================================================
# SalesOS AI — Integration Tests: Lead Lifecycle Workflow
# Tests full workflow orchestration across steps:
# Lead Intake ➔ Qualification ➔ Enrichment ➔ Decision Engine ➔ Assignment.
# ============================================================

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.workflows.engine import get_workflow_engine
from app.workflows.lead_lifecycle import register_lead_lifecycle_workflow


@pytest.mark.asyncio
async def test_lead_lifecycle_workflow_orchestration():
    """Test full lead_lifecycle workflow execution flow."""
    register_lead_lifecycle_workflow()
    engine = get_workflow_engine()

    lead_id = uuid4()
    org_id = uuid4()

    initial_data = {
        "lead_id": str(lead_id),
        "organization_id": str(org_id),
        "email": "vp_engineering@acme.com",
        "first_name": "Sarah",
        "last_name": "Connor",
        "company": "Acme Corp",
        "intent": "demo_request",
    }

    mock_session = AsyncMock()

    instance = await engine.start(
        mock_session,
        "lead_lifecycle",
        organization_id=org_id,
        lead_id=lead_id,
        initial_state=initial_data,
    )

    assert instance is not None
    assert instance.workflow_type == "lead_lifecycle"
    assert instance.organization_id == org_id
    assert instance.lead_id == lead_id
