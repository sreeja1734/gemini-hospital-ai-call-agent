"""
API integration tests for the FastAPI routes.
Tests authentication, system endpoints, and core call flow.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSystemEndpoints:
    """Test unauthenticated system endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "docs" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_calls" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client):
        response = await client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "password"
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_endpoint_authenticated(self, client, auth_headers):
        response = await client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "test_admin"
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthenticated(self, client):
        response = await client.get("/auth/me")
        assert response.status_code == 401


class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client):
        response = await client.get("/get-dashboard-data")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_appointments_requires_auth(self, client):
        response = await client.get("/appointments/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_transcripts_requires_auth(self, client):
        response = await client.get("/transcripts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_emergency_alerts_requires_auth(self, client):
        response = await client.get("/emergency-alerts")
        assert response.status_code == 401


class TestCallEndpoints:
    """Test call-related endpoints (unauthenticated — these are webhook/voice endpoints)."""

    @pytest.mark.asyncio
    async def test_start_conversation(self, client):
        response = await client.post("/start-conversation", json={
            "caller_phone": "+1234567890",
            "language": "en-US"
        })
        assert response.status_code == 200
        data = response.json()
        assert "call_id" in data
        assert "greeting_text" in data
        assert data["session_started"] is True

    @pytest.mark.asyncio
    async def test_process_speech_no_session(self, client):
        response = await client.post("/process-user-speech", json={
            "call_id": "nonexistent-call-id",
            "text_input": "Hello"
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_end_call_no_session(self, client):
        response = await client.post("/end-call", json={
            "call_id": "nonexistent-call-id"
        })
        assert response.status_code == 404
