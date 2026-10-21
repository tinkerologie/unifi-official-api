# Copyright 2026 UniFi Insights contributors
"""Tolerant model and parser tests for UniFi Access payloads."""

import json
import traceback

import pytest

from unifi_official_api.access.errors import (
    access_response_error,
    envelope_error_code,
)
from unifi_official_api.access.models import (
    AccessDevice,
    AccessDoor,
    AccessUser,
    AccessWebhookEndpoint,
    parse_record,
    parse_records,
)
from unifi_official_api.exceptions import UniFiResponseError


class TestParseRecords:
    """List envelopes: success, nesting tolerance and malformed shapes."""

    def test_parses_documented_list(self) -> None:
        response = {"code": "SUCCESS", "data": [{"id": "d1"}, {"id": "d2"}]}
        assert [door.id for door in parse_records(response, AccessDoor, "doors")] == [
            "d1",
            "d2",
        ]

    def test_flattens_one_level_of_nesting(self) -> None:
        response = {"code": "SUCCESS", "data": [[{"id": "a"}], {"id": "b"}]}
        records = parse_records(response, AccessDevice, "devices")
        assert [device.id for device in records] == ["a", "b"]

    def test_none_response_is_malformed(self) -> None:
        with pytest.raises(UniFiResponseError):
            parse_records(None, AccessDoor, "doors")

    def test_non_list_data_is_malformed(self) -> None:
        with pytest.raises(UniFiResponseError) as err:
            parse_records({"code": "SUCCESS", "data": {"id": "x"}}, AccessDoor, "doors")
        assert "malformed data" in err.value.message

    def test_non_object_record_is_malformed(self) -> None:
        with pytest.raises(UniFiResponseError):
            parse_records({"code": "SUCCESS", "data": [1]}, AccessDoor, "doors")

    def test_error_envelope_is_rejected_before_parsing(self) -> None:
        with pytest.raises(UniFiResponseError) as err:
            parse_records({"code": "CODE_SYSTEM_ERROR", "data": []}, AccessDoor, "doors")
        assert err.value.api_error_code == "CODE_SYSTEM_ERROR"


class TestParseRecord:
    """Single-object envelopes, including the one-item list form."""

    def test_parses_object(self) -> None:
        door = parse_record({"code": "SUCCESS", "data": {"id": "d1"}}, AccessDoor, "p")
        assert door.id == "d1"

    def test_accepts_one_item_list(self) -> None:
        door = parse_record({"code": "SUCCESS", "data": [{"id": "d1"}]}, AccessDoor, "p")
        assert door.id == "d1"

    def test_none_response_is_malformed(self) -> None:
        with pytest.raises(UniFiResponseError):
            parse_record(None, AccessDoor, "p")

    def test_scalar_data_is_malformed(self) -> None:
        with pytest.raises(UniFiResponseError):
            parse_record({"code": "SUCCESS", "data": "success"}, AccessDoor, "p")

    def test_multi_item_list_is_malformed(self) -> None:
        with pytest.raises(UniFiResponseError):
            parse_record(
                {"code": "SUCCESS", "data": [{"id": "a"}, {"id": "b"}]},
                AccessDoor,
                "p",
            )


class TestDeviceFields:
    """Source-tagged device fields are None unless the console sends real values."""

    def test_whitespace_alias_is_unknown(self) -> None:
        device = AccessDevice.model_validate({"alias": "   "})
        assert device.alias is None

    def test_non_empty_alias_is_kept(self) -> None:
        assert AccessDevice.model_validate({"alias": "Gate"}).alias == "Gate"

    def test_connected_hub_and_location_are_kept_when_present(self) -> None:
        device = AccessDevice.model_validate({"connected_uah_id": "hub-1", "location_id": "door-1"})
        assert device.connected_uah_id == "hub-1"
        assert device.location_id == "door-1"

    def test_non_boolean_online_is_unknown(self) -> None:
        assert AccessDevice.model_validate({"is_online": 1}).is_online is None
        assert AccessDevice.model_validate({"is_online": False}).is_online is False


class TestUserModel:
    """User status is limited to documented values; PIN hashes stay secret."""

    @pytest.mark.parametrize("status", ["ACTIVE", "PENDING", "DEACTIVATED"])
    def test_documented_status_is_kept(self, status: str) -> None:
        assert AccessUser.model_validate({"status": status}).status == status

    @pytest.mark.parametrize("status", ["active", "SUSPENDED", None, 3])
    def test_unknown_status_is_none(self, status: object) -> None:
        assert AccessUser.model_validate({"status": status}).status is None

    def test_pin_token_is_hidden_in_repr(self) -> None:
        user = AccessUser.model_validate({"pin_code": {"token": "pin-hash-value"}})
        assert user.pin_code is not None
        assert user.pin_code.token is not None
        assert "pin-hash-value" not in repr(user)
        assert "pin-hash-value" not in repr(user.pin_code)
        assert user.pin_code.token.get_secret_value() == "pin-hash-value"

    def test_webhook_secret_is_hidden_in_repr(self) -> None:
        endpoint = AccessWebhookEndpoint.model_validate({"secret": "endpoint-secret"})
        assert "endpoint-secret" not in repr(endpoint)
        assert "endpoint-secret" not in endpoint.model_dump_json()


class TestEnvelopeHelpers:
    """Body-level helpers used when no exception is raised by the transport."""

    @pytest.mark.parametrize("body", [None, "", "not json", "[1, 2]", "5"])
    def test_unusable_bodies_have_no_code(self, body: str | None) -> None:
        assert envelope_error_code(body) is None

    def test_documented_code_is_extracted(self) -> None:
        body = json.dumps({"code": "CODE_NOT_EXISTS", "msg": "gone"})
        assert envelope_error_code(body) == "CODE_NOT_EXISTS"

    def test_access_response_error_is_status_200_without_body(self) -> None:
        error = access_response_error("doors", "malformed data")
        assert isinstance(error, UniFiResponseError)
        assert error.status_code == 200
        assert error.response_body is None


_SECRET_MARKER = "SIGNING-SECRET-MARKER-7f3a"


def _assert_sanitized(error: UniFiResponseError) -> None:
    """Assert a malformed-record error carries nothing from the rejected input."""
    assert type(error) is UniFiResponseError
    assert error.status_code == 200
    assert error.api_error_code is None
    assert error.response_body is None
    assert error.message == "webhooks/endpoints returned a malformed record"
    # No chained exception: nothing points at the pydantic error or its input.
    assert error.__cause__ is None
    assert error.__context__ is None
    rendered = "".join(traceback.format_exception(error))
    assert _SECRET_MARKER not in rendered
    assert _SECRET_MARKER not in repr(error)
    assert _SECRET_MARKER not in str(error)


class TestMalformedRecordsAreSanitized:
    """A record of the wrong type raises a safe response error, never pydantic's."""

    def test_numeric_id_in_list_raises_sanitized_error(self) -> None:
        response = {
            "code": "SUCCESS",
            "data": [{"id": 12345, "secret": _SECRET_MARKER}],
        }
        with pytest.raises(UniFiResponseError) as err:
            parse_records(response, AccessWebhookEndpoint, "webhooks/endpoints")
        _assert_sanitized(err.value)

    def test_dict_secret_in_single_record_raises_sanitized_error(self) -> None:
        response = {
            "code": "SUCCESS",
            "data": {"id": "a22ee283", "secret": {"value": _SECRET_MARKER}},
        }
        with pytest.raises(UniFiResponseError) as err:
            parse_record(response, AccessWebhookEndpoint, "webhooks/endpoints")
        _assert_sanitized(err.value)

    def test_one_bad_record_fails_the_whole_list(self) -> None:
        response = {
            "code": "SUCCESS",
            "data": [
                {"id": "good", "secret": "fine"},
                {"id": 99, "secret": _SECRET_MARKER},
            ],
        }
        with pytest.raises(UniFiResponseError) as err:
            parse_records(response, AccessWebhookEndpoint, "webhooks/endpoints")
        _assert_sanitized(err.value)

    def test_tolerant_values_still_parse(self) -> None:
        response = {
            "code": "SUCCESS",
            "data": {"id": "a22ee283", "events": None, "secret": "endpoint-secret"},
        }
        endpoint = parse_record(response, AccessWebhookEndpoint, "webhooks/endpoints")
        assert endpoint.id == "a22ee283"
        assert endpoint.events is None
        assert endpoint.secret is not None
        assert endpoint.secret.get_secret_value() == "endpoint-secret"
