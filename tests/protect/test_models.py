"""Tests for UniFi Protect models."""

from __future__ import annotations

from datetime import UTC, datetime

from unifi_official_api.protect import (
    NVR,
    Camera,
    CameraState,
    Chime,
    Event,
    EventType,
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
