# ============================================================
# SalesOS AI — Test Configuration
# ============================================================

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Mock database session for integration tests.

    The schema uses PostgreSQL-specific types (JSONB, ARRAY) that cannot
    be rendered by SQLite. Tests that need a db_session receive an
    explicitly-mocked AsyncSession. This is intentional and documented —
    these tests validate API routing, serialization, and auth logic,
    not raw SQL execution.

    For tests that exercise actual SQL queries, use a real PostgreSQL
    test database (see conftest_pg.py or run via docker-compose).
    """
    mock_session = AsyncMock(spec=AsyncSession)
    # Provide reasonable defaults for common operations
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    yield mock_session
