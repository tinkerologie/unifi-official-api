"""Tests for authentication module."""

from __future__ import annotations

import pytest

from unifi_official_api import ApiKeyAuth, ApiKeyType, LocalAuth


class TestApiKeyAuth:
    """Tests for ApiKeyAuth."""

    def test_create_api_key_auth(self) -> None:
        """Test creating API key authentication."""
        auth = ApiKeyAuth(api_key="test-key")
        assert auth.api_key == "test-key"
        assert auth.key_type is None

    def test_create_api_key_auth_with_type(self) -> None:
        """Test creating API key authentication with type."""
        auth = ApiKeyAuth(api_key="test-key", key_type=ApiKeyType.NETWORK)
        assert auth.api_key == "test-key"
        assert auth.key_type == ApiKeyType.NETWORK

    def test_get_headers(self) -> None:
        """Test getting authentication headers."""
        auth = ApiKeyAuth(api_key="my-secret-key")
        headers = auth.get_headers()
        assert headers == {"X-API-Key": "my-secret-key"}

    def test_api_key_auth_is_frozen(self) -> None:
        """Test that ApiKeyAuth is immutable."""
        auth = ApiKeyAuth(api_key="test-key")
        with pytest.raises(AttributeError):
            auth.api_key = "new-key"  # type: ignore[misc]


class TestLocalAuth:
    """Tests for LocalAuth."""

    def test_create_local_auth(self) -> None:
        """Test creating local authentication."""
        auth = LocalAuth(api_key="local-key")
        assert auth.api_key == "local-key"
        assert auth.verify_ssl is True

    def test_create_local_auth_no_ssl_verify(self) -> None:
        """Test creating local auth without SSL verification."""
        auth = LocalAuth(api_key="local-key", verify_ssl=False)
        assert auth.verify_ssl is False

    def test_get_headers(self) -> None:
        """Test getting authentication headers."""
        auth = LocalAuth(api_key="local-key")
        headers = auth.get_headers()
        assert headers == {"X-API-Key": "local-key"}
