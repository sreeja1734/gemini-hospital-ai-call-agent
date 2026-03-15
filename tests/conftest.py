"""
Pytest configuration and shared fixtures.
"""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

# Patch settings before importing app
import os
os.environ["GOOGLE_API_KEY"] = "test-api-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-signing-only"
os.environ["DEBUG"] = "True"


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_db():
    """Mock AsyncSession for database operations."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def auth_headers():
    """Return valid JWT auth headers for testing protected endpoints."""
    from backend.auth import create_access_token
    token = create_access_token(username="test_admin", role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for API testing."""
    # Mock the database dependency
    from database.connection import get_db
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()

    async def mock_get_db():
        yield mock_session

    from backend.main import app
    app.dependency_overrides[get_db] = mock_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
