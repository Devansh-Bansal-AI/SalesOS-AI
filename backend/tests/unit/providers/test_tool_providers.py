# ============================================================
# SalesOS AI — Unit Tests: Tool Providers
# Tests Qdrant, CompanyResearch, Calendar, and CRM providers.
# ============================================================

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.tools.calendar import SalesOSCalendarProvider
from app.agents.tools.company_research import SalesOSCompanyResearchProvider
from app.agents.tools.qdrant_kb import QdrantKnowledgeBaseProvider


@pytest.mark.asyncio
async def test_company_research_provider():
    """Test SalesOSCompanyResearchProvider firmographic & technographic research."""
    provider = SalesOSCompanyResearchProvider()
    caps = provider.capabilities()
    assert caps["firmographics"] is True
    assert caps["technographics"] is True

    # Known domain lookup
    info = await provider.research_by_domain("acme.com")
    assert info is not None
    assert info.name == "Acme Corporation"
    assert info.domain == "acme.com"
    assert "FastAPI" in info.tech_stack

    # Unseen domain fallback
    fallback_info = await provider.research_by_domain("unknownstartup.io")
    assert fallback_info is not None
    assert "Unknownstartup" in fallback_info.name
    assert fallback_info.confidence == 0.70


@pytest.mark.asyncio
async def test_calendar_provider():
    """Test SalesOSCalendarProvider slot calculation and meeting creation."""
    provider = SalesOSCalendarProvider()

    slots = await provider.get_available_slots(
        host_email="rep@salesos.ai",
        start_date="2026-08-01T00:00:00Z",
        end_date="2026-08-03T00:00:00Z",
        duration_minutes=30,
    )
    assert len(slots) > 0
    assert "start_time" in slots[0]
    assert "end_time" in slots[0]

    meeting = await provider.create_meeting(
        host_email="rep@salesos.ai",
        attendee_email="lead@acme.com",
        title="SalesOS AI Demo",
        start_time=slots[0]["start_time"],
    )
    assert meeting["status"] == "confirmed"
    assert meeting["host_email"] == "rep@salesos.ai"
    assert meeting["attendee_email"] == "lead@acme.com"

    cancelled = await provider.cancel_meeting(meeting["event_id"])
    assert cancelled is True


@pytest.mark.asyncio
async def test_qdrant_kb_provider_mocked():
    """Test QdrantKnowledgeBaseProvider store & search with mocked Qdrant client."""
    provider = QdrantKnowledgeBaseProvider(default_collection="test_kb")

    # Mock qdrant client inside provider
    mock_client = AsyncMock()
    mock_collections = MagicMock()
    mock_collections.collections = []
    mock_client.get_collections.return_value = mock_collections

    mock_search_res = MagicMock()
    mock_search_res.id = "point_123"
    mock_search_res.score = 0.92
    mock_search_res.payload = {
        "text": "Acme Corp is interested in enterprise automation.",
        "organization_id": "org_1",
    }
    mock_client.search.return_value = [mock_search_res]

    with patch.object(provider, "_get_client", return_value=mock_client):
        await provider.store(
            text="Acme Corp is interested in enterprise automation.",
            metadata={"organization_id": "org_1", "lead_id": "lead_100"},
        )
        assert mock_client.upsert.called is True

        results = await provider.search("enterprise automation", top_k=3)
        assert len(results) == 1
        assert results[0]["id"] == "point_123"
        assert results[0]["score"] == 0.92
        assert "automation" in results[0]["text"]
