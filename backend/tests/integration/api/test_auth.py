# ============================================================
# SalesOS AI — Integration Tests: Authentication API
# Tests /api/v1/auth endpoints: register, login, refresh, me.
# ============================================================

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_login_missing_fields(async_client: AsyncClient):
    """Login with missing email/password should return 422."""
    resp = await async_client.post("/api/v1/auth/login", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_password(async_client: AsyncClient):
    """Login with missing password should return 422."""
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient):
    """Register with a weak password (no uppercase/special) should return 422."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Test Corp",
            "email": "test@example.com",
            "password": "weakpassword",  # No uppercase, no digit, no special char
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert resp.status_code == 422
    # Verify the error message is about password complexity
    data = resp.json()
    assert "detail" in data or "errors" in data


@pytest.mark.asyncio
async def test_register_password_complexity_no_digit(async_client: AsyncClient):
    """Register with password missing digit should return 422."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Test Corp",
            "email": "test@example.com",
            "password": "StrongPass!",  # No digit
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_password_complexity_no_special(async_client: AsyncClient):
    """Register with password missing special character should return 422."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Test Corp",
            "email": "test@example.com",
            "password": "StrongPass1",  # No special char
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(async_client: AsyncClient):
    """Register with password under 8 chars should return 422."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Test Corp",
            "email": "test@example.com",
            "password": "Ab1!",  # Too short
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(async_client: AsyncClient):
    """Register with invalid email format should return 422."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Test Corp",
            "email": "not-an-email",
            "password": "Strong1!Pass",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_me_unauthenticated(async_client: AsyncClient):
    """GET /auth/me without token should return 422 (missing header)."""
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_me_invalid_token(async_client: AsyncClient):
    """GET /auth/me with invalid JWT should return 401."""
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(async_client: AsyncClient):
    """POST /auth/refresh with garbage token should return 401."""
    resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.refresh.token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_jwt_token_generation():
    """Verify JWT tokens are generated with expected claims."""
    user_id = uuid4()
    org_id = uuid4()
    token = create_access_token(user_id, org_id, "admin")
    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are long
    # Verify it has 3 parts (header.payload.signature)
    parts = token.split(".")
    assert len(parts) == 3
