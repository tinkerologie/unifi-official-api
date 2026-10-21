# Copyright 2026 UniFi Insights contributors
"""Tests for UniFi Access endpoint groups: payloads, envelopes and validation."""

from __future__ import annotations

import json
import traceback
from typing import Any

import pytest

from tests.test_api_access_client import FakeResponse, fake_session, recorded_calls
from unifi_official_api.access import GateCommand, UniFiAccessClient
from unifi_official_api.access.models import (
    AccessDevice,
    AccessDoor,
    AccessWebhookEndpoint,
)
from unifi_official_api.exceptions import (
    UniFiResponseError,
    UniFiValidationError,
)

_DOOR_ID = "0ed545f8-2fcd-4839-9021-b39e707f6aa9"
_USER_ID = "17d2f099-99df-429b-becb-1399a6937e5a"
_ENDPOINT = {
    "id": "a22ee283",
    "endpoint": "https://ha.example/api/webhook/abc",
    "name": "Home Assistant",
    "events": ["access.door.unlock"],
    "secret": "1a7c9c6a69bb5a1e",
}
_SUCCESS = {"code": "SUCCESS", "data": "success", "msg": "success"}


def _client(*responses: FakeResponse) -> UniFiAccessClient:
    return UniFiAccessClient(
        token="token-value",
        host="192.168.1.1",
        session=fake_session(*responses),
    )


def _ok(data: Any = None) -> FakeResponse:
    body = {
        "code": "SUCCESS",
        "msg": "success",
        "data": data if data is not None else "success",
    }
    return FakeResponse(200, json.dumps(body))


def _calls(client: UniFiAccessClient) -> list[dict[str, Any]]:
    return recorded_calls(client)


class TestDoors:
    """Door reads, remote unlock with optional gate command, and lock rules."""

    async def test_get_all_parses_documented_fields(self) -> None:
        door = {
            "id": _DOOR_ID,
            "name": "Main Door",
            "full_name": "UNVR - 1F - Main Door",
            "floor_id": "3275af8d",
            "type": "door",
            "is_bind_hub": True,
            "door_lock_relay_status": "unlock",
            "door_position_status": "open",
        }
        client = _client(_ok([door]))
        doors = await client.doors.get_all()
        assert doors == [AccessDoor.model_validate(door)]
        assert doors[0].door_lock_relay_status == "unlock"
        assert doors[0].door_position_status == "open"
        assert _calls(client)[0]["url"].endswith("/api/v1/developer/doors")

    async def test_unknown_or_empty_states_are_none(self) -> None:
        door = AccessDoor.model_validate(
            {
                "id": _DOOR_ID,
                "door_lock_relay_status": "jammed",
                "door_position_status": "",
            }
        )
        assert door.door_lock_relay_status is None
        assert door.door_position_status is None

    async def test_get_one_door(self) -> None:
        client = _client(_ok({"id": _DOOR_ID, "name": "Main Door"}))
        door = await client.doors.get(_DOOR_ID)
        assert door.name == "Main Door"

    async def test_get_rejects_unsafe_id_without_request(self) -> None:
        client = _client()
        with pytest.raises(UniFiValidationError):
            await client.doors.get("../etc")
        assert _calls(client) == []

    async def test_plain_unlock_sends_no_params_or_body(self) -> None:
        client = _client(_ok())
        await client.doors.unlock(_DOOR_ID)
        call = _calls(client)[0]
        assert call["method"] == "PUT"
        assert call["url"].endswith(f"/doors/{_DOOR_ID}/unlock")
        assert call["params"] is None
        assert call["json"] is None

    @pytest.mark.parametrize("command", ["open", "close", "stop"])
    async def test_gate_command_is_query_parameter(self, command: GateCommand) -> None:
        client = _client(_ok())
        await client.doors.unlock(_DOOR_ID, control_cmd=command)
        call = _calls(client)[0]
        assert call["params"] == {"control_cmd": command}
        assert call["json"] is None

    async def test_unknown_gate_command_is_refused(self) -> None:
        client = _client()
        # Dynamic payload: exercises the runtime gate check, not the type hint.
        invalid_kwargs: dict[str, Any] = {"control_cmd": "lock_now"}
        with pytest.raises(UniFiValidationError):
            await client.doors.unlock(_DOOR_ID, **invalid_kwargs)
        assert _calls(client) == []

    async def test_unlock_refuses_error_envelope_on_http_200(self) -> None:
        body = json.dumps({"code": "CODE_DEVICE_DEVICE_OFFLINE", "msg": "offline"})
        client = _client(FakeResponse(200, body))
        with pytest.raises(UniFiResponseError) as err:
            await client.doors.unlock(_DOOR_ID)
        assert err.value.api_error_code == "CODE_DEVICE_DEVICE_OFFLINE"

    async def test_unlock_refuses_missing_body(self) -> None:
        client = _client(FakeResponse(200, ""))
        with pytest.raises(UniFiResponseError):
            await client.doors.unlock(_DOOR_ID)

    async def test_custom_lock_rule_sends_interval(self) -> None:
        client = _client(_ok())
        await client.doors.set_lock_rule(_DOOR_ID, "custom", interval=10)
        call = _calls(client)[0]
        assert call["method"] == "PUT"
        assert call["url"].endswith(f"/doors/{_DOOR_ID}/lock_rule")
        assert call["json"] == {"type": "custom", "interval": 10}

    async def test_reset_lock_rule_is_positional_and_returns_none(self) -> None:
        client = _client(_ok({"type": "reset", "ended_time": 0}))
        result = await client.doors.set_lock_rule(_DOOR_ID, "reset")
        assert result is None
        assert _calls(client)[0]["json"] == {"type": "reset"}

    async def test_custom_rule_requires_interval(self) -> None:
        client = _client()
        with pytest.raises(UniFiValidationError):
            await client.doors.set_lock_rule(_DOOR_ID, "custom")
        with pytest.raises(UniFiValidationError):
            await client.doors.set_lock_rule(_DOOR_ID, "custom", interval=0)
        assert _calls(client) == []

    async def test_non_custom_rule_refuses_interval(self) -> None:
        client = _client()
        with pytest.raises(UniFiValidationError):
            await client.doors.set_lock_rule(_DOOR_ID, "keep_lock", interval=5)
        assert _calls(client) == []

    async def test_lock_rule_refuses_error_envelope(self) -> None:
        client = _client(FakeResponse(200, json.dumps({"code": "CODE_NOT_EXISTS"})))
        with pytest.raises(UniFiResponseError) as err:
            await client.doors.set_lock_rule(_DOOR_ID, "reset")
        assert err.value.api_error_code == "CODE_NOT_EXISTS"


class TestDevices:
    """Device list with the nested-envelope tolerance and pyua-sourced fields."""

    async def test_flattens_nested_records_and_keeps_unknowns_none(self) -> None:
        nested = [
            [
                {"id": "7483c2773855", "name": "UA-HUB-3855", "type": "UAH"},
                {
                    "id": "gate1",
                    "type": "UGT",
                    "location_id": _DOOR_ID,
                    "is_online": True,
                },
            ]
        ]
        client = _client(_ok(nested))
        devices = await client.devices.get_all()
        assert [device.type for device in devices] == ["UAH", "UGT"]
        assert devices[0].location_id is None
        assert devices[1].location_id == _DOOR_ID
        assert devices[1].is_online is True
        assert devices[0].is_online is None

    async def test_malformed_record_is_rejected(self) -> None:
        client = _client(_ok(["not-an-object"]))
        with pytest.raises(UniFiResponseError):
            await client.devices.get_all()

    async def test_device_fields_follow_documented_shape(self) -> None:
        device = AccessDevice.model_validate(
            {"id": "x", "name": "n", "type": "t", "full_name": "f", "unknown": 1}
        )
        assert (device.id, device.name, device.type, device.full_name) == (
            "x",
            "n",
            "t",
            "f",
        )


class TestEmergency:
    """Console-wide Lockdown and Evacuation reads and writes."""

    async def test_get_parses_flags(self) -> None:
        client = _client(_ok({"lockdown": False, "evacuation": True}))
        status = await client.emergency.get()
        assert status.lockdown is False
        assert status.evacuation is True

    async def test_set_sends_both_flags_and_returns_none(self) -> None:
        client = _client(_ok())
        assert await client.emergency.set(lockdown=True, evacuation=False) is None
        call = _calls(client)[0]
        assert call["json"] == {"lockdown": True, "evacuation": False}
        assert call["url"].endswith("/doors/settings/emergency")

    async def test_set_rejects_non_boolean(self) -> None:
        client = _client()
        invalid_fields: tuple[dict[str, Any], ...] = (
            {"lockdown": 1, "evacuation": False},
            {"lockdown": False, "evacuation": 1},
        )
        for fields in invalid_fields:
            with pytest.raises(UniFiValidationError):
                await client.emergency.set(**fields)
        assert _calls(client) == []

    async def test_set_refuses_error_envelope(self) -> None:
        client = _client(FakeResponse(200, json.dumps({"code": "CODE_SYSTEM_ERROR"})))
        with pytest.raises(UniFiResponseError):
            await client.emergency.set(lockdown=False, evacuation=False)


class TestUsers:
    """PIN and status writes never log bodies and never accept bad input."""

    async def test_set_pin_sends_user_chosen_digits(self) -> None:
        client = _client(_ok())
        await client.users.set_pin(_USER_ID, "483920")
        call = _calls(client)[0]
        assert call["method"] == "PUT"
        assert call["url"].endswith(f"/users/{_USER_ID}/pin_codes")
        assert call["json"] == {"pin_code": "483920"}

    @pytest.mark.parametrize("pin", ["", "12a4", "١٢٣", " 1234", "12-34", None])
    async def test_set_pin_rejects_non_digits(self, pin: Any) -> None:
        client = _client()
        with pytest.raises(UniFiValidationError):
            await client.users.set_pin(_USER_ID, pin)
        assert _calls(client) == []

    async def test_remove_pin_uses_delete_without_body(self) -> None:
        client = _client(_ok())
        await client.users.remove_pin(_USER_ID)
        call = _calls(client)[0]
        assert call["method"] == "DELETE"
        assert call["url"].endswith(f"/users/{_USER_ID}/pin_codes")
        assert call["json"] is None

    async def test_pin_write_refuses_error_envelope(self) -> None:
        body = json.dumps({"code": "CODE_CREDS_PIN_CODE_CREDS_LENGTH_INVALID"})
        client = _client(FakeResponse(200, body))
        with pytest.raises(UniFiResponseError) as err:
            await client.users.set_pin(_USER_ID, "1")
        assert err.value.api_error_code == "CODE_CREDS_PIN_CODE_CREDS_LENGTH_INVALID"

    async def test_set_status_accepts_only_writable_values(self) -> None:
        client = _client(_ok())
        await client.users.set_status(_USER_ID, "DEACTIVATED")
        assert _calls(client)[0]["json"] == {"status": "DEACTIVATED"}
        for status in ("PENDING", "active", ""):
            with pytest.raises(UniFiValidationError):
                await client.users.set_status(_USER_ID, status)  # type: ignore[arg-type]

    async def test_status_write_refuses_missing_body(self) -> None:
        client = _client(FakeResponse(200, ""))
        with pytest.raises(UniFiResponseError):
            await client.users.set_status(_USER_ID, "ACTIVE")


class TestWebhooks:
    """Endpoint registration: secret returned, never logged or repr'd."""

    async def test_create_returns_secret_and_body_not_logged(self) -> None:
        client = _client(_ok(_ENDPOINT))
        created = await client.webhooks.create(
            name="Home Assistant",
            endpoint="https://ha.example/api/webhook/abc",
            events=["access.door.unlock"],
        )
        assert created == AccessWebhookEndpoint.model_validate(_ENDPOINT)
        assert created.secret is not None
        assert "1a7c9c6a69bb5a1e" not in repr(created)
        call = _calls(client)[0]
        assert call["method"] == "POST"
        assert call["json"]["events"] == ["access.door.unlock"]

    async def test_create_accepts_single_item_list_envelope(self) -> None:
        client = _client(_ok([_ENDPOINT]))
        created = await client.webhooks.create(
            name="n", endpoint="https://ha.example/x", events=["access.door.unlock"]
        )
        assert created.id == "a22ee283"

    async def test_create_without_secret_yields_none(self) -> None:
        endpoint = {k: v for k, v in _ENDPOINT.items() if k != "secret"}
        client = _client(_ok(endpoint))
        created = await client.webhooks.create(
            name="n", endpoint="https://ha.example/x", events=["access.door.unlock"]
        )
        assert created.secret is None

    async def test_create_requires_name_endpoint_and_events(self) -> None:
        client = _client()
        with pytest.raises(UniFiValidationError):
            await client.webhooks.create(name="", endpoint="https://x", events=["e"])
        with pytest.raises(UniFiValidationError):
            await client.webhooks.create(name="n", endpoint="https://x", events=[])
        assert _calls(client) == []

    async def test_update_puts_to_endpoint_id(self) -> None:
        client = _client(_ok(_ENDPOINT))
        updated = await client.webhooks.update(
            "a22ee283", name="n", endpoint="https://x", events=["access.door.unlock"]
        )
        assert updated.id == "a22ee283"
        assert _calls(client)[0]["url"].endswith("/webhooks/endpoints/a22ee283")

    async def test_delete_checks_envelope(self) -> None:
        client = _client(_ok())
        await client.webhooks.delete("a22ee283")
        assert _calls(client)[0]["method"] == "DELETE"

    async def test_delete_refuses_error_envelope(self) -> None:
        client = _client(FakeResponse(200, json.dumps({"code": "CODE_RESOURCE_NOT_FOUND"})))
        with pytest.raises(UniFiResponseError):
            await client.webhooks.delete("a22ee283")

    async def test_get_all_lists_endpoints(self) -> None:
        client = _client(_ok([_ENDPOINT]))
        endpoints = await client.webhooks.get_all()
        assert len(endpoints) == 1
        assert endpoints[0].events == ["access.door.unlock"]

    async def test_unsafe_endpoint_id_is_refused(self) -> None:
        client = _client()
        with pytest.raises(UniFiValidationError):
            await client.webhooks.update("a/b", name="n", endpoint="https://x", events=["e"])
        assert _calls(client) == []


_LEAK_MARKER = "SIGNING-SECRET-MARKER-7f3a"


class TestMalformedPayloadsThroughEndpoints:
    """Endpoint wrappers surface a sanitized error for a malformed record."""

    async def test_webhook_list_with_numeric_id_is_sanitized(self) -> None:
        body = json.dumps({"code": "SUCCESS", "data": [{"id": 12345, "secret": _LEAK_MARKER}]})
        client = _client(FakeResponse(200, body))
        with pytest.raises(UniFiResponseError) as err:
            await client.webhooks.get_all()
        assert err.value.api_error_code is None
        assert err.value.response_body is None
        assert err.value.__context__ is None
        assert _LEAK_MARKER not in "".join(traceback.format_exception(err.value))

    async def test_webhook_create_with_dict_secret_is_sanitized(self) -> None:
        body = json.dumps(
            {
                "code": "SUCCESS",
                "data": {"id": "a22ee283", "secret": {"v": _LEAK_MARKER}},
            }
        )
        client = _client(FakeResponse(200, body))
        with pytest.raises(UniFiResponseError) as err:
            await client.webhooks.create(
                name="n", endpoint="https://ha.example/x", events=["access.door.unlock"]
            )
        assert err.value.__context__ is None
        assert _LEAK_MARKER not in "".join(traceback.format_exception(err.value))
        assert _LEAK_MARKER not in str(err.value)

    async def test_door_with_numeric_id_is_sanitized(self) -> None:
        body = json.dumps({"code": "SUCCESS", "data": [{"id": 7, "name": _LEAK_MARKER}]})
        client = _client(FakeResponse(200, body))
        with pytest.raises(UniFiResponseError) as err:
            await client.doors.get_all()
        assert err.value.__context__ is None
        assert _LEAK_MARKER not in "".join(traceback.format_exception(err.value))
