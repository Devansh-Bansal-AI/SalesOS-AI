# ============================================================
# SalesOS AI — Unit Tests for Copilot Service
# ============================================================

from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.copilot import CopilotQueryRequest, EmailDraftRequest
from app.services.copilot_service import CopilotService


@pytest.mark.asyncio
async def test_copilot_query(db_session):
    """Test querying the copilot service with fallback response."""
    service = CopilotService(db_session)
    req = CopilotQueryRequest(prompt="How do I handle pricing objections?")
    org_id = uuid4()

    response = await service.query_copilot(org_id, req)

    assert response.answer is not None
    assert len(response.suggested_actions) > 0
    assert response.confidence >= 0.8


@pytest.mark.asyncio
async def test_copilot_deal_prep(db_session):
    """Test preparing a deal brief for a lead."""
    service = CopilotService(db_session)
    lead_id = uuid4()
    org_id = uuid4()

    # Mock lead retrieval
    mock_lead = AsyncMock()
    mock_lead.id = lead_id
    mock_lead.company.name = "Acme Corp"
    mock_lead.qualification = {"score": 85}

    with patch.object(service.lead_repo, "get_by_id_and_org", return_value=mock_lead):
        prep = await service.prepare_deal_brief(org_id, lead_id)

        assert prep.lead_id == lead_id
        assert prep.company_name == "Acme Corp"
        assert prep.deal_health_score == 85
        assert len(prep.key_pain_points) > 0
        assert len(prep.recommended_agenda) > 0
        assert "Budget Constraints" in prep.objection_playbook
