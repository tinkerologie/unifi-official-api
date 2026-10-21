# Copyright 2026 UniFi Insights contributors
"""Envelope error mapping: HTTP 200 codes become the same exceptions as HTTP errors."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.test_api_access_client import FakeResponse, fake_session
from unifi_official_api.access import UniFiAccessClient
from unifi_official_api.access.errors import (
    envelope_error_code,
    safe_code,
)
from unifi_official_api.exceptions import (
    UniFiAuthenticationError,
    UniFiNotFoundError,
    UniFiResponseError,
)

_USER_ID = "17d2f099-99df-429b-becb-1399a6937e5a"
_SERVER_TEXT = "server-side detail that must not reach an exception"


def _client(*responses: FakeResponse) -> UniFiAccessClient:
    return UniFiAccessClient(
        token="token-value",
        host="192.168.1.1",
        session=fake_session(*responses),
    )


def _envelope(code: Any) -> FakeResponse:
    """HTTP 200 carrying an error envelope, as the console really does."""
    return FakeResponse(200, json.dumps({"code": code, "msg": _SERVER_TEXT}))


class TestEnvelopeAuthentication:
    """Documented token and permission codes arrive on HTTP 200."""

    @pytest.mark.parametrize(
        "code",
        ["CODE_AUTH_FAILED", "CODE_ACCESS_TOKEN_INVALID"],
    )
    async def test_token_codes_map_to_401(self, code: str) -> None:
        client = _client(_envelope(code))
        with pytest.raises(UniFiAuthenticationError) as err:
            await client.doors.get_all()
        assert err.value.status_code == 401
        assert err.value.api_error_code == code
        assert "token rejected" in err.value.message.lower()

    @pytest.mark.parametrize(
        "code",
        ["CODE_UNAUTHORIZED", "CODE_OPERATION_FORBIDDEN"],
    )
    async def test_permission_codes_map_to_403(self, code: str) -> None:
        client = _client(_envelope(code))
        with pytest.raises(UniFiAuthenticationError) as err:
            await client.users.set_status(_USER_ID, "ACTIVE")
        assert err.value.status_code == 403
        assert err.value.api_error_code == code
        assert "lacks permission" in err.value.message

    async def test_envelope_auth_message_matches_http_401_message(self) -> None:
        envelope_client = _client(_envelope("CODE_AUTH_FAILED"))
        http_client = _client(FakeResponse(401, "{}"))
        with pytest.raises(UniFiAuthenticationError) as from_envelope:
            await envelope_client.doors.get_all()
        with pytest.raises(UniFiAuthenticationError) as from_http:
            await http_client.doors.get_all()
        assert from_envelope.value.message == from_http.value.message
        assert from_envelope.value.status_code == from_http.value.status_code

    async def test_server_text_never_reaches_the_message(self) -> None:
        client = _client(_envelope("CODE_AUTH_FAILED"))
        with pytest.raises(UniFiAuthenticationError) as err:
            await client.doors.get_all()
        assert _SERVER_TEXT not in err.value.message
        assert _SERVER_TEXT not in str(err.value)


class TestEnvelopeNotFound:
    """Missing-resource codes arrive on HTTP 200 and become UniFiNotFoundError."""

    @pytest.mark.parametrize(
        "code",
        [
            "CODE_RESOURCE_NOT_FOUND",
            "CODE_NOT_EXISTS",
            "CODE_USER_WORKER_NOT_EXISTS",
            "CODE_USER_ACCOUNT_NOT_EXIST",
            "CODE_DEVICE_DEVICE_NOT_FOUND",
        ],
    )
    async def test_missing_resource_codes_map_to_404(self, code: str) -> None:
        client = _client(_envelope(code))
        with pytest.raises(UniFiNotFoundError) as err:
            await client.users.set_status(_USER_ID, "DEACTIVATED")
        assert err.value.status_code == 404
        assert err.value.api_error_code == code
        assert _SERVER_TEXT not in str(err.value)

    async def test_unknown_user_pin_removal_is_not_found(self) -> None:
        client = _client(_envelope("CODE_USER_WORKER_NOT_EXISTS"))
        with pytest.raises(UniFiNotFoundError):
            await client.users.remove_pin(_USER_ID)

    async def test_not_found_is_still_a_response_error(self) -> None:
        client = _client(_envelope("CODE_RESOURCE_NOT_FOUND"))
        with pytest.raises(UniFiResponseError):
            await client.doors.get(_USER_ID)


class TestEnvelopeOtherCodes:
    """Other documented codes keep status 200 and their code, for translation."""

    async def test_pin_length_code_is_a_safe_translation_key(self) -> None:
        client = _client(_envelope("CODE_CREDS_PIN_CODE_CREDS_LENGTH_INVALID"))
        with pytest.raises(UniFiResponseError) as err:
            await client.users.set_pin(_USER_ID, "1")
        assert not isinstance(err.value, (UniFiAuthenticationError, UniFiNotFoundError))
        assert err.value.status_code == 200
        assert err.value.api_error_code == "CODE_CREDS_PIN_CODE_CREDS_LENGTH_INVALID"
        assert _SERVER_TEXT not in str(err.value)
        assert err.value.response_body is None

    async def test_pin_already_exists_code_is_kept(self) -> None:
        client = _client(_envelope("CODE_CREDS_PIN_CODE_CREDS_ALREADY_EXIST"))
        with pytest.raises(UniFiResponseError) as err:
            await client.users.set_pin(_USER_ID, "483920")
        assert err.value.api_error_code == "CODE_CREDS_PIN_CODE_CREDS_ALREADY_EXIST"

    async def test_system_error_is_generic_response_error(self) -> None:
        client = _client(_envelope("CODE_SYSTEM_ERROR"))
        with pytest.raises(UniFiResponseError) as err:
            await client.devices.get_all()
        assert not isinstance(err.value, UniFiAuthenticationError)
        assert err.value.api_error_code == "CODE_SYSTEM_ERROR"


class TestCodeShape:
    """Only genuine machine codes are kept; anything else is dropped."""

    @pytest.mark.parametrize(
        "value",
        [
            "CODE_OK",
            "CODE_PARAMS_INVALID",
            "CODE_CREDS_PIN_CODE_CREDS_LENGTH_INVALID",
            "CODE_" + "A" * 60,
        ],
    )
    def test_documented_shape_is_accepted(self, value: str) -> None:
        assert safe_code(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            None,
            5,
            "",
            "SUCCESS",
            "code_lower",
            "CODE_",
            "CODE_" + "A" * 61,
            "CODE_has space",
            "CODE_x\n",
            "hunter2-secret",
            "Bearer abcdef",
            "CODE_A/../../x",
        ],
    )
    def test_arbitrary_strings_are_rejected(self, value: object) -> None:
        assert safe_code(value) is None

    def test_envelope_code_of_secret_shape_is_dropped(self) -> None:
        body = json.dumps({"code": "hunter2-secret", "msg": "x"})
        assert envelope_error_code(body) is None

    async def test_secret_shaped_envelope_code_never_reaches_exception(self) -> None:
        client = _client(_envelope("hunter2-secret"))
        with pytest.raises(UniFiResponseError) as err:
            await client.doors.get_all()
        assert err.value.api_error_code is None
        assert "hunter2" not in str(err.value)
