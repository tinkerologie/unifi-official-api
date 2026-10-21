"""Tests for exceptions module."""

from __future__ import annotations

from unifi_official_api import (
    UniFiAuthenticationError,
    UniFiConnectionError,
    UniFiError,
    UniFiGlobalAlarmManagerError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiResponseError,
    UniFiRuleNotEditableError,
    UniFiTimeoutError,
    UniFiUnsupportedError,
    UniFiValidationError,
)


class TestUniFiError:
    """Tests for base UniFiError."""

    def test_create_error(self) -> None:
        """Test creating a basic error."""
        error = UniFiError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"

    def test_error_inheritance(self) -> None:
        """Test that UniFiError inherits from Exception."""
        error = UniFiError("Test")
        assert isinstance(error, Exception)


class TestUniFiAuthenticationError:
    """Tests for UniFiAuthenticationError."""

    def test_create_auth_error(self) -> None:
        """Test creating authentication error."""
        error = UniFiAuthenticationError("Invalid API key")
        assert str(error) == "Invalid API key"
        assert isinstance(error, UniFiError)


class TestUniFiConnectionError:
    """Tests for UniFiConnectionError."""

    def test_create_connection_error(self) -> None:
        """Test creating connection error."""
        error = UniFiConnectionError("Connection refused")
        assert str(error) == "Connection refused"
        assert isinstance(error, UniFiError)


class TestUniFiUnsupportedError:
    """Tests for UniFiUnsupportedError."""

    def test_create_unsupported_error(self) -> None:
        """Test creating unsupported error."""
        error = UniFiUnsupportedError("Operation not supported")
        assert str(error) == "Operation not supported"
        assert isinstance(error, UniFiError)


class TestUniFiRuleNotEditableError:
    """Tests for UniFiRuleNotEditableError."""

    def test_create_rule_not_editable_error(self) -> None:
        """Test creating rule not editable error."""
        error = UniFiRuleNotEditableError("Rule managed by console")
        assert str(error) == "Rule managed by console"
        assert isinstance(error, UniFiError)


class TestUniFiResponseError:
    """Tests for UniFiResponseError."""

    def test_create_response_error(self) -> None:
        """Test creating response error."""
        error = UniFiResponseError(
            "Bad request",
            status_code=400,
            response_body='{"error": "invalid"}',
        )
        assert str(error) == "UniFiResponseError(status=400)"
        assert error.message == "Bad request"
        assert error.status_code == 400
        assert error.response_body == '{"error": "invalid"}'
        assert isinstance(error, UniFiError)


class TestUniFiNotFoundError:
    """Tests for UniFiNotFoundError."""

    def test_create_not_found_error(self) -> None:
        """Test creating not found error."""
        error = UniFiNotFoundError("Device not found", status_code=404)
        assert str(error) == "UniFiNotFoundError(status=404)"
        assert error.status_code == 404
        assert isinstance(error, UniFiResponseError)


class TestUniFiGlobalAlarmManagerError:
    """Tests for UniFiGlobalAlarmManagerError."""

    def test_create_alarm_manager_error(self) -> None:
        """Test creating global alarm manager error."""
        error = UniFiGlobalAlarmManagerError("Alarm arming refused", status_code=400)
        assert str(error) == "UniFiGlobalAlarmManagerError(status=400)"
        assert error.status_code == 400
        assert isinstance(error, UniFiResponseError)


class TestUniFiRateLimitError:
    """Tests for UniFiRateLimitError."""

    def test_create_rate_limit_error(self) -> None:
        """Test creating rate limit error."""
        error = UniFiRateLimitError(
            "Rate limited",
            status_code=429,
            retry_after=60,
        )
        assert str(error) == "UniFiRateLimitError(status=429)"
        assert error.status_code == 429
        assert error.retry_after == 60
        assert isinstance(error, UniFiResponseError)


class TestUniFiValidationError:
    """Tests for UniFiValidationError."""

    def test_create_validation_error(self) -> None:
        """Test creating validation error."""
        error = UniFiValidationError("Invalid parameter")
        assert str(error) == "Invalid parameter"
        assert isinstance(error, UniFiError)


class TestUniFiTimeoutError:
    """Tests for UniFiTimeoutError."""

    def test_create_timeout_error(self) -> None:
        """Test creating timeout error."""
        error = UniFiTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, UniFiError)
