# Copyright 2026 UniFi Insights contributors
"""Regression tests for PIN and credential redaction, and base ``_put`` log_body."""

import json
import logging
from typing import Any

import pytest

from tests.test_api_access_client import FakeResponse, fake_session, recorded_calls
from unifi_official_api.auth import ApiKeyAuth
from unifi_official_api.base import BaseUniFiClient, _redact


class _ProbeClient(BaseUniFiClient):
    """Concrete base client used to exercise transport behaviour directly."""

    async def validate_connection(self) -> bool:
        return True


def _client(*responses: FakeResponse, **kwargs: Any) -> _ProbeClient:
    return _ProbeClient(
        auth=ApiKeyAuth(api_key="network-key"),
        base_url="https://192.168.1.1/",
        session=fake_session(*responses),
        **kwargs,
    )


class TestPutLogBody:
    """``_put`` accepts ``log_body`` and forwards it, like ``_get`` and ``_post``."""

    async def test_put_omits_response_body_when_asked(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG)
        client = _client(FakeResponse(200, json.dumps({"pin_code": "483920"})))
        await client._put("users/1", json_data={"name": "x"}, log_body=False)
        assert "483920" not in caplog.text
        assert "<body omitted" in caplog.text

    async def test_put_logs_redacted_body_by_default(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG)
        client = _client(FakeResponse(200, json.dumps({"name": "visible"})))
        await client._put("devices/1", json_data={"name": "x"})
        assert "visible" in caplog.text

    async def test_put_sends_body_and_params_unchanged(self) -> None:
        client = _client(FakeResponse(200, json.dumps({"ok": True})))
        await client._put("doors/1/unlock", json_data={"a": 1}, params={"b": "2"})
        call = recorded_calls(client)[0]
        assert call["method"] == "PUT"
        assert call["json"] == {"a": 1}
        assert call["params"] == {"b": "2"}

    async def test_request_body_is_never_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG)
        client = _client(FakeResponse(200, json.dumps({"ok": True})))
        await client._put("users/1/pin_codes", json_data={"pin_code": "483920"})
        assert "483920" not in caplog.text


class TestSslHook:
    """The per-request TLS hook is only sent when a client sets it."""

    async def test_default_hook_sends_no_ssl_argument(self) -> None:
        client = _client(FakeResponse(200, json.dumps({"ok": True})))
        await client._request("GET", "devices")
        assert recorded_calls(client)[0]["kwargs"] == {}

    async def test_overridden_hook_is_sent_per_request(self) -> None:
        class _NoVerify(_ProbeClient):
            def _ssl_for_request(self) -> bool | None:
                return False

        client = _NoVerify(
            auth=ApiKeyAuth(api_key="k"),
            base_url="https://192.168.1.1/",
            session=fake_session(FakeResponse(200, json.dumps({"ok": True}))),
        )
        await client._request("GET", "devices")
        assert recorded_calls(client)[0]["kwargs"] == {"ssl": False}


class TestRedaction:
    """Credential and PIN keys are redacted in JSON and in non-JSON text."""

    @pytest.mark.parametrize("key", ["pin", "pin_code", "pin_codes"])
    def test_pin_keys_are_redacted_in_json(self, key: str) -> None:
        text = json.dumps({key: "483920", "name": "keep"})
        redacted = _redact(text)
        assert "483920" not in redacted
        assert "keep" in redacted

    def test_pin_list_value_is_redacted_in_json(self) -> None:
        text = json.dumps({"pin_codes": ["483920", "112233"]})
        redacted = _redact(text)
        assert "483920" not in redacted
        assert "112233" not in redacted

    def test_pin_keys_are_redacted_in_nested_json(self) -> None:
        text = json.dumps({"user": {"pin_code": {"token": "hash-value"}}})
        redacted = _redact(text)
        assert "hash-value" not in redacted
        assert "pin_code" in redacted

    def test_pin_key_is_redacted_in_non_json_text(self) -> None:
        text = '<html>"pin_code": "483920"</html>'
        redacted = _redact(text)
        assert "483920" not in redacted
        assert '"pin_code"' in redacted

    def test_pin_key_is_case_insensitive(self) -> None:
        redacted = _redact(json.dumps({"PIN_CODE": "483920"}))
        assert "483920" not in redacted

    def test_unrelated_keys_are_not_redacted(self) -> None:
        redacted = _redact(json.dumps({"pinned": "visible", "mapping": "visible"}))
        assert "visible" in redacted

    def test_existing_credential_keys_still_redacted(self) -> None:
        redacted = _redact(json.dumps({"password": "p1", "apiKey": "k1"}))
        assert "p1" not in redacted
        assert "k1" not in redacted
