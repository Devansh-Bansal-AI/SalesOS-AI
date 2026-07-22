# ============================================================
# SalesOS AI — Integration Tests for Copilot & Health APIs
# ============================================================

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_liveness_endpoint():
    """Test standard liveness probe GET /api/v1/health."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_readiness_endpoint():
    """Test readiness probe GET /api/v1/health/ready."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health/ready")
        assert res.status_code in (200, 503)
        data = res.json()["data"]
        assert "postgres" in data
        assert "redis" in data
        assert "qdrant" in data
