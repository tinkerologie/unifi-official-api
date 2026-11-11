"""Tests for UniFi Protect models."""

from __future__ import annotations

import json
from collections import UserDict
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from unifi_official_api.protect import (
    NVR,
    Camera,
    CameraState,
    Chime,
    Event,
    EventType,
    ExternalArmProfile,
    ExternalArmProfileState,
    Light,
    LightMode,
    LiveView,
    RecordingMode,
    Sensor,
)


class TestCameraModel:
    """Tests for Camera model."""

    def test_create_camera(self) -> None:
        """Test creating a camera from dict."""
        data = {
            "id": "cam-123",
            "mac": "11:22:33:44:55:66",
            "name": "Front Door",
            "state": "CONNECTED",
            "isConnected": True,
            "isRecording": True,
            "recordingMode": "always",
        }
        camera = Camera.model_validate(data)
        assert camera.id == "cam-123"
        assert camera.name == "Front Door"
        assert camera.state == CameraState.CONNECTED
        assert camera.is_connected is True
        assert camera.is_recording is True
        assert camera.recording_mode == RecordingMode.ALWAYS

    def test_camera_display_name(self) -> None:
        """Test camera display_name property."""
        camera = Camera.model_validate(
            {
                "id": "1",
                "mac": "11:22:33:44:55:66",
                "name": "Backyard",
            }
        )
        assert camera.display_name == "Backyard"

        camera = Camera.model_validate(
            {
                "id": "2",
                "mac": "11:22:33:44:55:66",
            }
        )
        assert camera.display_name == "11:22:33:44:55:66"


class TestSensorModel:
    """Tests for Sensor model."""

    def test_create_sensor(self) -> None:
        """Test creating a sensor from dict."""
        data = {
            "id": "sensor-123",
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Door Sensor",
            "type": "door",
            "isConnected": True,
            "isOpened": False,
            "batteryLevel": 85,
            "batteryStatus": {"percentage": 85, "isLow": False},
        }
        sensor = Sensor.model_validate(data)
        assert sensor.id == "sensor-123"
        assert sensor.name == "Door Sensor"
        assert sensor.is_opened is False
        assert sensor.battery_level == 85
        assert sensor.battery_status is not None
        assert sensor.battery_status.percentage == 85
        assert sensor.battery_status.is_low is False

    @pytest.mark.parametrize(
        ("payload_key", "value"),
        [
            ("isMountedIncorrectly", True),
            ("isMountedIncorrectly", False),
            ("isMountedIncorrectly", None),
            ("is_mounted_incorrectly", True),
            ("is_mounted_incorrectly", None),
            ("is_mounted_incorrectly", "omitted"),
        ],
    )
    def test_is_mounted_incorrectly(self, payload_key: str, value: bool | str | None) -> None:
        """The orientation flag reads through its alias or Python name."""
        base = {"id": "sensor-123", "mac": "AA:BB:CC:DD:EE:FF"}
        if value == "omitted":
            sensor = Sensor.model_validate(base)
            assert sensor.is_mounted_incorrectly is None
            return
        sensor = Sensor.model_validate({**base, payload_key: value})
        assert sensor.is_mounted_incorrectly is value
        assert "isMountedIncorrectly" in sensor.model_dump(by_alias=True)
        assert "is_mounted_incorrectly" in sensor.model_dump()


class TestLightModel:
    """Tests for Light model."""

    def test_create_light(self) -> None:
        """Test creating a light from dict."""
        data = {
            "id": "light-123",
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Floodlight",
            "isConnected": True,
            "isLightOn": True,
            "lightMode": "motion",
            "brightness": 100,
        }
        light = Light.model_validate(data)
        assert light.id == "light-123"
        assert light.name == "Floodlight"
        assert light.is_light_on is True
        assert light.light_mode == LightMode.MOTION
        assert light.brightness == 100


class TestChimeModel:
    """Tests for Chime model."""

    def test_create_chime(self) -> None:
        """Test creating a chime from dict."""
        data = {
            "id": "chime-123",
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Doorbell Chime",
            "isConnected": True,
            "volume": 80,
        }
        chime = Chime.model_validate(data)
        assert chime.id == "chime-123"
        assert chime.name == "Doorbell Chime"
        assert chime.volume == 80


class TestNVRModel:
    """Tests for NVR model."""

    def test_create_nvr(self) -> None:
        """Test creating an NVR from dict."""
        data = {
            "id": "nvr-123",
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "UniFi NVR",
            "version": "2.9.20",
            "isConnectedToCloud": True,
            "cameraCount": 8,
            "recordingRetentionDays": 30,
        }
        nvr = NVR.model_validate(data)
        assert nvr.id == "nvr-123"
        assert nvr.version == "2.9.20"
        assert nvr.camera_count == 8
        assert nvr.recording_retention_days == 30

    @pytest.mark.parametrize(
        ("feature_flags", "expected"),
        [
            ({"useExternalAlarmManager": True}, True),
            ({"useExternalAlarmManager": False}, False),
            ({}, None),
            ({"useExternalAlarmManager": "yes"}, None),
            ({"useExternalAlarmManager": 1}, None),
            (None, None),
        ],
    )
    def test_use_external_alarm_manager_reads_only_booleans(
        self, feature_flags: dict[str, Any] | None, expected: bool | None
    ) -> None:
        """The property returns the flag only when it is a real boolean."""
        nvr = NVR.model_validate({"id": "nvr-123", "featureFlags": feature_flags})
        assert nvr.use_external_alarm_manager is expected

    def test_use_external_alarm_manager_keeps_dictionary_access(self) -> None:
        """The flag stays readable through the unchanged ``feature_flags`` dict."""
        flags = {"useExternalAlarmManager": True, "futureFlag": 7}
        nvr = NVR.model_validate({"id": "nvr-123", "featureFlags": flags})

        assert nvr.feature_flags is not None
        assert nvr.feature_flags["useExternalAlarmManager"] is True
        assert nvr.feature_flags["futureFlag"] == 7
        assert nvr.model_dump(by_alias=True)["featureFlags"] == flags


class TestLiveViewModel:
    """Tests for LiveView model."""

    def test_create_liveview(self) -> None:
        """Test creating a live view from dict."""
        data = {
            "id": "lv-123",
            "name": "Main View",
            "layout": 4,
            "isDefault": True,
            "slots": [
                {"cameraId": "cam-1"},
                {"cameraId": "cam-2"},
            ],
        }
        liveview = LiveView.model_validate(data)
        assert liveview.id == "lv-123"
        assert liveview.name == "Main View"
        assert liveview.layout == 4
        assert len(liveview.slots) == 2


class TestEventModel:
    """Tests for Event model."""

    def test_create_event(self) -> None:
        """Test creating an event from dict."""
        data = {
            "id": "event-123",
            "type": "motion",
            "cameraId": "cam-123",
            "smartDetectTypes": ["person"],
        }
        event = Event.model_validate(data)
        assert event.id == "event-123"
        assert event.type == EventType.MOTION
        assert event.camera_id == "cam-123"
        assert "person" in event.smart_detect_types

    def test_event_duration(self) -> None:
        """Test event duration calculation."""
        event = Event.model_validate(
            {
                "id": "event-123",
                "type": "motion",
                "start": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                "end": datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC),
            }
        )
        assert event.duration == 30.0

    def test_event_duration_no_end(self) -> None:
        """Test event duration when no end time."""
        event = Event.model_validate(
            {
                "id": "event-123",
                "type": "motion",
                "start": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            }
        )
        assert event.duration is None


_PIN_MARKER = "915273"


def _texts(profile: ExternalArmProfile) -> list[str]:
    """Return every profile representation that can reach a caller or a log."""
    return [repr(profile), str(profile), str(profile.model_dump()), profile.model_dump_json()]


def _error_texts(exc: BaseException) -> list[str]:
    """Return the text and error payloads of every exception in the chain."""
    texts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        texts.extend((str(current), repr(current)))
        errors = getattr(current, "errors", None)
        if callable(errors):
            texts.append(repr(errors()))
        current = current.__cause__ or current.__context__
    return texts


def _assert_no_pin(*texts: str) -> None:
    for text in texts:
        assert _PIN_MARKER not in text


_FULL_PROFILE: dict[str, Any] = {
    "id": "profile-1",
    "title": "Home",
    "state": "armed",
    "state_set_at": "2026-11-01T00:00:00.000Z",
    "state_promotion_due_at": "2026-11-01T00:00:30.000Z",
    "created_at": "2026-10-01T00:00:00.000Z",
    "created_by": "user-1",
    "updated_at": "2026-11-01T00:00:00.000Z",
    "updated_by": "user-2",
    "activation_delay": 30,
    "deactivation_delay": 15.5,
    "active_breach_id": 12,
    "alarm_ids": ["alarm-1", "alarm-2"],
    "has_pin": True,
    "schedule": {"mon": {"type": "all_day"}},
}


class TestExternalArmProfileModel:
    """Tests for the external alarm manager arm profile model."""

    def test_full_payload(self) -> None:
        """Every documented snake_case field parses."""
        profile = ExternalArmProfile.model_validate(_FULL_PROFILE)

        assert profile.id == "profile-1"
        assert profile.title == "Home"
        assert profile.state is ExternalArmProfileState.ARMED
        assert profile.state_set_at == "2026-11-01T00:00:00.000Z"
        assert profile.state_promotion_due_at == "2026-11-01T00:00:30.000Z"
        assert profile.activation_delay == 30
        assert profile.deactivation_delay == 15.5
        assert profile.active_breach_id == 12
        assert profile.alarm_ids == ["alarm-1", "alarm-2"]
        assert profile.has_pin is True
        assert profile.schedule == {"mon": {"type": "all_day"}}
        assert profile.model_dump(by_alias=True) == _FULL_PROFILE

    def test_minimal_payload(self) -> None:
        """Only ``id`` is required, as for the other arm profile models."""
        profile = ExternalArmProfile.model_validate({"id": "profile-1"})

        assert profile.id == "profile-1"
        assert profile.state is None
        assert profile.model_dump(exclude_none=True) == {"id": "profile-1"}

    def test_unknown_state_and_extras_follow_forward_compatibility(self) -> None:
        """A newer state stays a plain string and unknown extras are kept."""
        profile = ExternalArmProfile.model_validate(
            {"id": "profile-1", "state": "futureState", "futureField": {"a": 1}}
        )

        assert type(profile.state) is str
        assert profile.state == "futureState"
        assert profile.model_extra == {"futureField": {"a": 1}}

    @pytest.mark.parametrize(
        "pin_payload",
        [
            {"pin_code": _PIN_MARKER},
            {"pinCode": _PIN_MARKER},
            {"PIN": _PIN_MARKER},
            {"pin_codes": [_PIN_MARKER]},
            {"schedule": {"mon": {"pin": _PIN_MARKER}}},
            {"extra": [{"pin_code": _PIN_MARKER}, {"pinCode": _PIN_MARKER}]},
            {"extra": UserDict({"pinCode": _PIN_MARKER, "futureField": True})},
            {"tuple_extra": ({"pin_code": _PIN_MARKER}, {"PIN": _PIN_MARKER})},
            {"pin_code": _PIN_MARKER, "pinCode": _PIN_MARKER, "pin": _PIN_MARKER},
        ],
    )
    def test_pin_keys_never_reach_the_model(self, pin_payload: dict[str, Any]) -> None:
        """No PIN spelling survives into any representation or dump."""
        profile = ExternalArmProfile.model_validate(
            {"id": "profile-1", "has_pin": True, **pin_payload}
        )

        rendered = (repr(profile), str(profile.model_dump()), profile.model_dump_json())
        for text in rendered:
            assert _PIN_MARKER not in text
        assert profile.has_pin is True

    def test_container_values_are_stripped_and_preserved(self) -> None:
        """Tuples, sets and frozensets keep their type while PIN keys go."""
        profile = ExternalArmProfile.model_validate(
            {
                "id": "profile-1",
                "tuple_extra": ({"pin_codes": _PIN_MARKER},),
                "set_extra": {1, 2},
                "frozenset_extra": frozenset({3}),
            }
        )

        assert profile.model_extra == {
            "tuple_extra": ({},),
            "set_extra": {1, 2},
            "frozenset_extra": frozenset({3}),
        }
        assert _PIN_MARKER not in repr(profile) + profile.model_dump_json()

    def test_model_copy_drops_pin_spellings(self) -> None:
        """Copy updates cannot put a PIN on the copied profile."""
        profile = ExternalArmProfile.model_validate({"id": "profile-1", "has_pin": True})

        copied = profile.model_copy(
            update={
                "pin_code": _PIN_MARKER,
                "PIN": _PIN_MARKER,
                "extra": [{"pin": _PIN_MARKER}, {"pinCode": _PIN_MARKER}],
                "tuple_extra": ({"pin_codes": _PIN_MARKER},),
            }
        )

        assert copied.model_extra == {"extra": [{}, {}], "tuple_extra": ({},)}
        assert copied.has_pin is True
        _assert_no_pin(*_texts(copied))

    def test_model_copy_without_update_keeps_the_profile(self) -> None:
        """A plain copy keeps every value."""
        profile = ExternalArmProfile.model_validate(_FULL_PROFILE)

        assert profile.model_copy() == profile

    def test_assignment_drops_pin_spellings(self) -> None:
        """Attribute assignment cannot put a PIN on the profile either."""
        profile = ExternalArmProfile.model_validate({"id": "profile-1"})

        profile.pin_code = _PIN_MARKER
        profile.pinCode = _PIN_MARKER
        profile.extra = [{"pin": _PIN_MARKER}]
        profile.schedule = {"mon": {"pin": _PIN_MARKER}}

        assert profile.model_extra == {"extra": [{}]}
        assert profile.schedule == {"mon": {}}
        _assert_no_pin(*_texts(profile))

    def test_representations_hide_a_pin_injected_into_the_extra_store(self) -> None:
        """A key written past the mutators still never reaches repr or a dump."""
        profile = ExternalArmProfile.model_validate({"id": "profile-1"})
        assert profile.__pydantic_extra__ is not None
        profile.__pydantic_extra__["pin_code"] = _PIN_MARKER
        profile.__pydantic_extra__["extra"] = [{"pinCode": _PIN_MARKER}]

        _assert_no_pin(*_texts(profile))

    def test_validation_errors_quote_no_input(self) -> None:
        """A rejected non-mapping input is not echoed in the error."""
        with pytest.raises(ValidationError) as caught:
            ExternalArmProfile.model_validate(_PIN_MARKER)

        _assert_no_pin(*_error_texts(caught.value))
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is None

    def test_malformed_json_error_quotes_no_input(self) -> None:
        """An unparsable body is not echoed in the error."""
        with pytest.raises(ValidationError) as caught:
            ExternalArmProfile.model_validate_json(f'{{"pin_code":"{_PIN_MARKER}",')

        _assert_no_pin(*_error_texts(caught.value))
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is None

    def test_valid_json_parses_and_drops_the_pin(self) -> None:
        """A valid JSON body parses like a dict and the PIN never reaches the model."""
        body = json.dumps({**_FULL_PROFILE, "pin_code": _PIN_MARKER})

        profile = ExternalArmProfile.model_validate_json(body)

        assert profile == ExternalArmProfile.model_validate(_FULL_PROFILE)
        assert profile.model_dump(by_alias=True) == _FULL_PROFILE
        assert profile.model_extra == {}
        _assert_no_pin(repr(profile), str(profile), profile.model_dump_json())

    def test_wrong_type_pin_error_quotes_no_input(self) -> None:
        """A field error keeps its location but drops every input value."""
        with pytest.raises(ValidationError) as caught:
            ExternalArmProfile.model_validate_json(f'{{"id": 123, "pin_code": "{_PIN_MARKER}"}}')

        _assert_no_pin(*_error_texts(caught.value))
        assert caught.value.errors()[0]["loc"] == ("id",)
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is None
