"""
Unit tests for authentication middleware.

Tests API key validation and authentication flow.
"""
import pytest
from fastapi import HTTPException, status
from unittest.mock import MagicMock, patch

from middleware.auth import verify_api_key, authenticate_request, AuthenticationError
from config import Settings


class TestAuthentication:
    """Test suite for authentication middleware."""

    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self, test_api_key):
        """Test verification with valid API key."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys=test_api_key,
                require_auth=True
            )

            result = await verify_api_key(test_api_key)
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self, invalid_api_key):
        """Test verification with invalid API key."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys="valid-key-12345",
                require_auth=True
            )

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(invalid_api_key)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_missing(self):
        """Test verification with missing API key."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys="test-key",
                require_auth=True
            )

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(None)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_auth_disabled(self, invalid_api_key):
        """Test that invalid key is accepted when auth is disabled."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys="valid-key",
                require_auth=False
            )

            result = await verify_api_key(invalid_api_key)
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_api_key_multiple_valid_keys(self):
        """Test verification with multiple valid API keys."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys="key1,key2,key3",
                require_auth=True
            )

            result = await verify_api_key("key2")
            assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_request_with_header(self, test_api_key):
        """Test request authentication with API key header."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys=test_api_key,
                require_auth=True
            )

            # Mock request with API key header
            request = MagicMock()
            request.headers = {"X-API-Key": test_api_key}

            result = await authenticate_request(request)
            assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_request_without_header(self):
        """Test request authentication without API key header."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys="test-key",
                require_auth=True
            )

            # Mock request without API key header
            request = MagicMock()
            request.headers = {}

            with pytest.raises(HTTPException) as exc_info:
                await authenticate_request(request)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_authenticate_request_auth_disabled(self):
        """Test request authentication when auth is disabled."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys="test-key",
                require_auth=False
            )

            # Mock request without API key
            request = MagicMock()
            request.headers = {}

            result = await authenticate_request(request)
            assert result is True

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError exception."""
        error = AuthenticationError("Test error message")

        assert error.detail == "Test error message"
        assert str(error) == "Test error message"

    @pytest.mark.asyncio
    async def test_verify_api_key_with_whitespace(self):
        """Test API key validation handles whitespace."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys=" key1 , key2 , key3 ",
                require_auth=True
            )

            # Should work with trimmed key
            result = await verify_api_key("key2")
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_api_key_empty_string(self):
        """Test verification with empty string API key."""
        with patch("middleware.auth.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                api_keys="valid-key",
                require_auth=True
            )

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key("")

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
