# ============================================================
# SalesOS AI — Integration Tests: Analytics REST API
# Tests /api/v1/analytics endpoints with authenticated JWT headers.
# ============================================================

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.api.deps import CurrentUser
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_analytics_endpoints(async_client: AsyncClient, db_session):
    """Test domain-focused analytics endpoints."""
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    org_id = UUID("00000000-0000-0000-0000-000000000001")

    token = create_access_token(
        user_id=user_id,
        organization_id=org_id,
        role="admin",
    )
    headers = {"Authorization": f"Bearer {token}"}

    mock_user = CurrentUser(
        id=user_id,
        organization_id=org_id,
        role="admin",
    )

    # Mock DB execute results for DashboardService queries
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.scalar_one_or_none.return_value = 0.0
    db_session.execute = AsyncMock(return_value=mock_result)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("app.api.deps.get_current_user", return_value=mock_user):
            # 1. Overview KPI Endpoint
            resp = await async_client.get("/api/v1/analytics/overview?days=30", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "total_leads" in data
            assert "overall_conversion_rate" in data
            assert "sla_health_percentage" in data

            # 2. Pipeline Analytics Endpoint
            resp_pipe = await async_client.get(
                "/api/v1/analytics/pipeline?days=30", headers=headers
            )
            assert resp_pipe.status_code == 200
            data_pipe = resp_pipe.json()
            assert "stage_counts" in data_pipe
            assert "funnel_conversion_rates" in data_pipe

            # 3. Agent Analytics Endpoint
            resp_agents = await async_client.get(
                "/api/v1/analytics/agents?days=30", headers=headers
            )
            assert resp_agents.status_code == 200
            data_agents = resp_agents.json()
            assert "agents" in data_agents

            # 4. SLA Analytics Endpoint
            resp_sla = await async_client.get("/api/v1/analytics/sla?days=30", headers=headers)
            assert resp_sla.status_code == 200
            data_sla = resp_sla.json()
            assert "compliance_percentage" in data_sla
    finally:
        app.dependency_overrides.clear()
