"""
Unit tests for the JWT authentication module.
"""
import pytest
from datetime import timedelta
from backend.auth import (
    create_access_token,
    verify_token,
    TokenPayload,
)
from fastapi import HTTPException


class TestJWTAuth:
    """Tests for JWT token creation and verification."""

    def test_create_and_verify_token(self):
        token = create_access_token(username="testuser", role="admin")
        payload = verify_token(token)
        assert payload.sub == "testuser"
        assert payload.role == "admin"

    def test_verify_token_default_role(self):
        token = create_access_token(username="basic_user")
        payload = verify_token(token)
        assert payload.role == "user"

    def test_verify_invalid_token(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.jwt.token")
        assert exc_info.value.status_code == 401

    def test_verify_expired_token(self):
        token = create_access_token(
            username="expireduser",
            expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_custom_expiry(self):
        token = create_access_token(
            username="custom",
            expires_delta=timedelta(hours=48)
        )
        payload = verify_token(token)
        assert payload.sub == "custom"
