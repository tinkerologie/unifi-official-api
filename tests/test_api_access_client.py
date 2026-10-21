# Copyright 2026 UniFi Insights contributors
"""Tests for the UniFi Access client: transport, auth, errors and logging."""

import json
import logging
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientSession
from yarl import URL

from unifi_official_api.access import (
    ACCESS_API_PORT,
    AccessTokenAuth,
    UniFiAccessClient,
)
from unifi_official_api.exceptions import (
    UniFiAuthenticationError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiResponseError,
    UniFiValidationError,
)

if TYPE_CHECKING:
    from unifi_official_api.base import BaseUniFiClient

_TOKEN = "super-secret-access-token"


class FakeResponse:
    """Minimal aiohttp response double for the base client."""

    def __init__(
        self,
        status: int,
        body: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._body = body
        self.headers = headers or {}
        self.url = URL("https://192.168.1.1:12445/api/v1/developer/doors")
        self.method = "GET"
        self.history: tuple[Any, ...] = ()
        self.content_type = "application/json"

    async def text(self) -> str:
        return self._body

    async def json(self) -> Any:
        return json.loads(self._body)


class FakeRequest:
    """Async context manager returned by ``FakeSession.request``."""

    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> FakeResponse:
        return self._response

    async def __aexit__(self, *exc: object) -> None:
        return None


class FakeSession:
    """Records requests and replays canned responses in order."""

    closed = False

    def __init__(self, *responses: FakeResponse) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: URL,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> FakeRequest:
        self.calls.append(
            {
                "method": method,
                "url": str(url),
                "params": params,
                "json": json,
                "headers": headers or {},
                "kwargs": kwargs,
            }
        )
        return FakeRequest(self._responses.pop(0))


def fake_session(*responses: FakeResponse) -> ClientSession:
    """``ClientSession`` spec double that replays ``responses`` via ``FakeSession``."""
    fake = FakeSession(*responses)
    session = MagicMock(spec=ClientSession)
    session.closed = False
    session.request.side_effect = fake.request
    session.calls = fake.calls
    return session


def recorded_calls(client: BaseUniFiClient) -> list[dict[str, Any]]:
    session = client._session
    assert isinstance(session, MagicMock)
    return session.calls


def _client(*responses: FakeResponse, **kwargs: Any) -> UniFiAccessClient:
    return UniFiAccessClient(
        token=kwargs.pop("token", _TOKEN),
        host=kwargs.pop("host", "192.168.1.1"),
        session=fake_session(*responses),
        **kwargs,
    )


class TestConstruction:
    """Token, host and port handling at construction time."""

    def test_base_url_uses_developer_api_on_default_port(self) -> None:
        client = _client()
        assert str(client.base_url) == "https://192.168.1.1:12445/api/v1/developer"
        assert ACCESS_API_PORT == 12445

    def test_accepts_full_url_and_custom_port(self) -> None:
        client = _client(host="https://console.example:9443/ignored", port=8443)
        assert str(client.base_url) == ("https://console.example:8443/api/v1/developer")

    def test_brackets_ipv6_hosts(self) -> None:
        client = _client(host="fd00::1")
        assert str(client.base_url) == "https://[fd00::1]:12445/api/v1/developer"

    def test_strips_token_whitespace(self) -> None:
        client = _client(token="  abc  ")
        assert client._auth.get_headers() == {"Authorization": "Bearer abc"}

    @pytest.mark.parametrize("token", ["", "   ", None])
    def test_rejects_missing_token(self, token: Any) -> None:
        with pytest.raises(UniFiValidationError):
            UniFiAccessClient(token=token, host="192.168.1.1")

    @pytest.mark.parametrize("port", [0, 65536, -1, "12445"])
    def test_rejects_port_out_of_range(self, port: Any) -> None:
        with pytest.raises(UniFiValidationError):
            UniFiAccessClient(token=_TOKEN, host="192.168.1.1", port=port)

    def test_rejects_host_without_name(self) -> None:
        with pytest.raises(UniFiValidationError):
            UniFiAccessClient(token=_TOKEN, host="https://")

    def test_endpoint_groups_are_attached(self) -> None:
        client = _client()
        assert client.doors is not None
        assert client.devices is not None
        assert client.emergency is not None
        assert client.users is not None
        assert client.webhooks is not None


class TestAuth:
    """Bearer header, token secrecy and TLS verification."""

    def test_sends_bearer_header_and_no_api_key(self) -> None:
        headers = _client()._get_headers()
        assert headers["Authorization"] == f"Bearer {_TOKEN}"
        assert "X-API-Key" not in headers

    def test_token_hidden_in_auth_repr(self) -> None:
        auth = AccessTokenAuth(token=_TOKEN, verify_ssl=False)
        assert _TOKEN not in repr(auth)
        assert "verify_ssl=False" in repr(auth)

    def test_token_hidden_in_client_repr(self) -> None:
        assert _TOKEN not in repr(_client())

    def test_verify_ssl_applies_to_connector_and_requests(self) -> None:
        client = _client(verify_ssl=False)
        assert client._get_ssl_context() is False
        assert client._ssl_for_request() is False

    async def test_request_passes_verify_ssl_to_shared_session(self) -> None:
        client = _client(
            FakeResponse(200, json.dumps({"code": "SUCCESS", "data": []})),
            verify_ssl=False,
        )
        await client._request("GET", "doors")
        assert recorded_calls(client)[0]["kwargs"] == {"ssl": False}


class TestTransport:
    """Requests, error mapping and log redaction."""

    async def test_unauthorized_becomes_access_token_message(self) -> None:
        client = _client(FakeResponse(401, json.dumps({"code": "CODE_AUTH_FAILED"})))
        with pytest.raises(UniFiAuthenticationError) as err:
            await client._get("doors")
        assert "Access token rejected" in str(err.value.message)
        assert err.value.status_code == 401
        assert err.value.api_error_code is None

    async def test_forbidden_is_authentication_error(self) -> None:
        client = _client(FakeResponse(403, "{}"))
        with pytest.raises(UniFiAuthenticationError) as err:
            await client._get("doors")
        assert err.value.status_code == 403

    async def test_not_found_keeps_error_code_and_drops_body(self) -> None:
        body = json.dumps({"code": "CODE_RESOURCE_NOT_FOUND", "msg": "door 123"})
        client = _client(FakeResponse(404, body))
        with pytest.raises(UniFiNotFoundError) as err:
            await client._get("doors/123")
        assert err.value.api_error_code == "CODE_RESOURCE_NOT_FOUND"
        assert err.value.response_body is None
        assert "door 123" not in str(err.value)

    async def test_server_error_keeps_only_safe_code(self) -> None:
        body = json.dumps({"code": "CODE_SYSTEM_ERROR", "msg": "secret detail"})
        client = _client(FakeResponse(500, body))
        with pytest.raises(UniFiResponseError) as err:
            await client._get("doors")
        assert err.value.api_error_code == "CODE_SYSTEM_ERROR"
        assert err.value.response_body is None

    async def test_rate_limit_keeps_retry_after_and_drops_body(self) -> None:
        responses = [
            FakeResponse(429, "{}", headers={"Retry-After": "120"}),
            FakeResponse(429, "{}", headers={"Retry-After": "120"}),
        ]
        client = _client(*responses)
        with pytest.raises(UniFiRateLimitError) as err:
            await client._get("doors")
        assert err.value.retry_after == 120
        assert err.value.response_body is None

    async def test_error_code_with_long_or_non_string_value_is_dropped(self) -> None:
        body = json.dumps({"code": 500, "msg": "x"})
        client = _client(FakeResponse(400, body))
        with pytest.raises(UniFiResponseError) as err:
            await client._get("doors")
        assert err.value.api_error_code is None

    async def test_request_and_response_bodies_are_not_logged(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG)
        secret_body = json.dumps(
            {"code": "SUCCESS", "data": {"pin_code": "483920", "token": "hash"}}
        )
        client = _client(FakeResponse(200, secret_body))
        await client._put(
            "users/abc/pin_codes",
            json_data={"pin_code": "483920"},
            log_body=False,
        )
        text = caplog.text
        assert "483920" not in text
        assert "hash" not in text
        assert _TOKEN not in text
        assert "<body omitted" in text

    async def test_default_logging_still_omits_access_body(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG)
        client = _client(FakeResponse(200, json.dumps({"data": "visible-value"})))
        await client._get("doors")
        assert "visible-value" not in caplog.text
        assert "[Access response omitted]" in caplog.text

    async def test_non_json_success_body_is_an_error(self) -> None:
        client = _client(FakeResponse(200, "<html>login</html>"))
        with pytest.raises(UniFiResponseError) as err:
            await client._get("doors")
        assert err.value.response_body is None

    async def test_validate_connection_lists_doors(self) -> None:
        client = _client(FakeResponse(200, json.dumps({"code": "SUCCESS", "data": []})))
        assert await client.validate_connection() is True
        assert recorded_calls(client)[0]["method"] == "GET"
        assert recorded_calls(client)[0]["url"].endswith("/api/v1/developer/doors")
