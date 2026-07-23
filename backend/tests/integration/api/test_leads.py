# ============================================================
# SalesOS AI — Integration Tests: Leads REST API
# Tests /api/v1/leads endpoints: auth enforcement, RBAC, validation.
# ============================================================

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.deps import CurrentUser
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app


def _make_auth_headers(user_id=None, org_id=None, role="admin"):
    """Helper to create JWT auth headers."""
    user_id = user_id or uuid4()
    org_id = org_id or uuid4()
    token = create_access_token(user_id, org_id, role)
    return {"Authorization": f"Bearer {token}"}, user_id, org_id


@pytest.mark.asyncio
async def test_list_leads_unauthenticated(async_client: AsyncClient):
    """GET /leads without auth should fail."""
    resp = await async_client.get("/api/v1/leads")
    # Should be 422 (missing header) or 401
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_create_lead_unauthenticated(async_client: AsyncClient):
    """POST /leads without auth should fail."""
    resp = await async_client.post(
        "/api/v1/leads",
        json={"email": "test@example.com", "source": "website"},
    )
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_get_lead_unauthenticated(async_client: AsyncClient):
    """GET /leads/{id} without auth should fail."""
    fake_id = uuid4()
    resp = await async_client.get(f"/api/v1/leads/{fake_id}")
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_delete_lead_unauthenticated(async_client: AsyncClient):
    """DELETE /leads/{id} without auth should fail."""
    fake_id = uuid4()
    resp = await async_client.delete(f"/api/v1/leads/{fake_id}")
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_rbac_viewer_cannot_delete(async_client: AsyncClient):
    """Viewer role should not be able to delete leads (403)."""
    headers, user_id, org_id = _make_auth_headers(role="viewer")
    mock_user = CurrentUser(id=user_id, organization_id=org_id, role="viewer")

    with patch("app.api.deps.get_current_user", return_value=mock_user):
        fake_id = uuid4()
        resp = await async_client.delete(f"/api/v1/leads/{fake_id}", headers=headers)
        # Viewer should get 403 Forbidden
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_viewer_cannot_create(async_client: AsyncClient):
    """Viewer role should not be able to create leads (403)."""
    headers, user_id, org_id = _make_auth_headers(role="viewer")
    mock_user = CurrentUser(id=user_id, organization_id=org_id, role="viewer")

    with patch("app.api.deps.get_current_user", return_value=mock_user):
        resp = await async_client.post(
            "/api/v1/leads",
            json={"email": "test@example.com", "source": "website"},
            headers=headers,
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_admin_can_access_leads(async_client: AsyncClient, db_session):
    """Admin role should pass RBAC check for lead listing."""
    headers, user_id, org_id = _make_auth_headers(role="admin")
    mock_user = CurrentUser(id=user_id, organization_id=org_id, role="admin")

    # Mock the DB to return empty list
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0
    mock_list_result = MagicMock()
    mock_list_result.scalars.return_value.all.return_value = []

    call_count = 0

    async def mock_execute(stmt, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_count_result
        return mock_list_result

    db_session.execute = AsyncMock(side_effect=mock_execute)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.deps.get_current_user", return_value=mock_user):
            resp = await async_client.get("/api/v1/leads", headers=headers)
            assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invalid_lead_id_format(async_client: AsyncClient):
    """GET /leads/{invalid-uuid} should return 422."""
    headers, _, _ = _make_auth_headers(role="admin")
    resp = await async_client.get("/api/v1/leads/not-a-uuid", headers=headers)
    assert resp.status_code == 422
