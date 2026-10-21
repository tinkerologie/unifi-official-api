"""Tests for UniFi Protect endpoint methods."""

from typing import Any

import pytest
from aioresponses import aioresponses

from unifi_official_api.exceptions import UniFiUnsupportedError
from unifi_official_api.protect import UniFiProtectClient
from unifi_official_api.protect.models import LightMode, RecordingMode


class TestCamerasEndpoint:
    """Tests for cameras endpoint methods."""

    async def test_cameras_update(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test updating a camera."""
        camera_id = sample_camera["id"]
        mock_aioresponse.patch(
            f"https://192.168.1.1/proxy/protect/integration/v1/cameras/{camera_id}",
            payload={"data": {**sample_camera, "name": "Updated Name"}},
        )

        camera = await protect_client.cameras.update(camera_id, name="Updated Name")
        assert camera.name == "Updated Name"

    async def test_cameras_set_recording_mode(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test setting camera recording mode."""
        camera_id = sample_camera["id"]
        mock_aioresponse.patch(
            f"https://192.168.1.1/proxy/protect/integration/v1/cameras/{camera_id}",
            payload={"data": {**sample_camera, "recordingMode": "motion"}},
        )

        camera = await protect_client.cameras.set_recording_mode(camera_id, RecordingMode.MOTION)
        assert camera is not None

    async def test_cameras_get_snapshot(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test getting camera snapshot."""
        camera_id = sample_camera["id"]
        mock_aioresponse.get(
            f"https://192.168.1.1/proxy/protect/integration/v1/cameras/{camera_id}/snapshot",
            body=b"fake_image_data",
        )

        snapshot = await protect_client.cameras.get_snapshot(camera_id)
        assert snapshot == b"fake_image_data"

    async def test_cameras_restart(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test restarting camera."""
        camera_id = sample_camera["id"]
        mock_aioresponse.post(
            f"https://192.168.1.1/proxy/protect/integration/v1/cameras/{camera_id}/restart",
            payload={},
        )

        result = await protect_client.cameras.restart(camera_id)
        assert result is True

    async def test_cameras_ptz_move(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test PTZ camera movement."""
        camera_id = sample_camera["id"]
        mock_aioresponse.post(
            f"https://192.168.1.1/proxy/protect/integration/v1/cameras/{camera_id}/ptz/move",
            payload={},
        )

        result = await protect_client.cameras.ptz_move(camera_id, pan=0.5, tilt=0.3)
        assert result is True


class TestSensorsEndpoint:
    """Tests for sensors endpoint methods."""

    async def test_sensors_get(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_sensor: dict[str, Any],
    ) -> None:
        """Test getting sensor."""
        sensor_id = sample_sensor["id"]
        mock_aioresponse.get(
            f"https://192.168.1.1/proxy/protect/integration/v1/sensors/{sensor_id}",
            payload={"data": sample_sensor},
        )

        sensor = await protect_client.sensors.get(sensor_id)
        assert sensor.id == sensor_id

    async def test_sensors_update(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_sensor: dict[str, Any],
    ) -> None:
        """Test updating sensor."""
        sensor_id = sample_sensor["id"]
        mock_aioresponse.patch(
            f"https://192.168.1.1/proxy/protect/integration/v1/sensors/{sensor_id}",
            payload={"data": {**sample_sensor, "name": "Updated"}},
        )

        sensor = await protect_client.sensors.update(sensor_id, name="Updated")
        assert sensor.name == "Updated"

    async def test_sensors_set_status_led(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_sensor: dict[str, Any],
    ) -> None:
        """Test setting sensor status LED."""
        sensor_id = sample_sensor["id"]
        mock_aioresponse.patch(
            f"https://192.168.1.1/proxy/protect/integration/v1/sensors/{sensor_id}",
            payload={"data": {**sample_sensor, "openStatusLedEnabled": True}},
        )

        sensor = await protect_client.sensors.set_status_led(sensor_id, True)
        assert sensor is not None

    async def test_sensors_set_motion_sensitivity(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_sensor: dict[str, Any],
    ) -> None:
        """Test setting sensor motion sensitivity."""
        sensor_id = sample_sensor["id"]
        mock_aioresponse.patch(
            f"https://192.168.1.1/proxy/protect/integration/v1/sensors/{sensor_id}",
            payload={"data": {**sample_sensor, "motionSensitivity": 75}},
        )

        sensor = await protect_client.sensors.set_motion_sensitivity(sensor_id, 75)
        assert sensor is not None


class TestLightsEndpoint:
    """Tests for lights endpoint methods."""

    async def test_lights_get_all(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing lights."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/lights",
            payload={"data": [{"id": "light-1", "mac": "AA:BB:CC:DD:EE:FF", "name": "Test Light"}]},
        )

        lights = await protect_client.lights.get_all()
        assert len(lights) == 1

    async def test_lights_get(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting a light."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/lights/light-1",
            payload={"data": {"id": "light-1", "mac": "AA:BB:CC:DD:EE:FF", "name": "Test Light"}},
        )

        light = await protect_client.lights.get("light-1")
        assert light.id == "light-1"

    async def test_lights_turn_on(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test turning on a light."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/lights/light-1",
            payload={"data": {"id": "light-1", "mac": "AA:BB:CC:DD:EE:FF", "lightMode": "on"}},
        )

        light = await protect_client.lights.turn_on("light-1")
        assert light is not None

    async def test_lights_turn_off(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test turning off a light."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/lights/light-1",
            payload={"data": {"id": "light-1", "mac": "AA:BB:CC:DD:EE:FF", "lightMode": "off"}},
        )

        light = await protect_client.lights.turn_off("light-1")
        assert light is not None

    async def test_lights_set_mode(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test setting light mode."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/lights/light-1",
            payload={"data": {"id": "light-1", "mac": "AA:BB:CC:DD:EE:FF", "lightMode": "motion"}},
        )

        light = await protect_client.lights.set_mode("light-1", LightMode.MOTION)
        assert light is not None

    async def test_lights_set_brightness(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test setting light brightness."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/lights/light-1",
            payload={
                "data": {
                    "id": "light-1",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "lightDeviceSettings": {"ledLevel": 5},
                }
            },
        )

        light = await protect_client.lights.set_brightness("light-1", 5)
        assert light is not None


class TestChimesEndpoint:
    """Tests for chimes endpoint methods."""

    async def test_chimes_get_all(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing chimes."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/chimes",
            payload={"data": [{"id": "chime-1", "mac": "AA:BB:CC:DD:EE:FF", "name": "Door Chime"}]},
        )

        chimes = await protect_client.chimes.get_all()
        assert len(chimes) == 1

    async def test_chimes_get(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting a chime."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/chimes/chime-1",
            payload={"data": {"id": "chime-1", "mac": "AA:BB:CC:DD:EE:FF", "name": "Door Chime"}},
        )

        chime = await protect_client.chimes.get("chime-1")
        assert chime.id == "chime-1"

    async def test_chimes_update(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test updating a chime."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/chimes/chime-1",
            payload={"data": {"id": "chime-1", "mac": "AA:BB:CC:DD:EE:FF", "name": "Updated"}},
        )

        chime = await protect_client.chimes.update("chime-1", name="Updated")
        assert chime.name == "Updated"

    async def test_chimes_set_volume(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test setting chime volume."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/chimes/chime-1",
            payload={
                "data": {
                    "id": "chime-1",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "name": "Door Chime",
                    "ringSettings": [
                        {
                            "cameraId": "cam-1",
                            "ringtoneId": "rt-1",
                            "repeatTimes": 1,
                            "volume": 30,
                        }
                    ],
                }
            },
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/chimes/chime-1",
            payload={
                "data": {
                    "id": "chime-1",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "name": "Door Chime",
                    "ringSettings": [
                        {
                            "cameraId": "cam-1",
                            "ringtoneId": "rt-1",
                            "repeatTimes": 1,
                            "volume": 50,
                        }
                    ],
                }
            },
        )

        chime = await protect_client.chimes.set_volume("chime-1", 50)
        assert chime is not None

    async def test_chimes_play(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test playing chime raises UniFiUnsupportedError."""
        with pytest.raises(UniFiUnsupportedError, match="does not support chime playback"):
            await protect_client.chimes.play("chime-1")


class TestNVREndpoint:
    """Tests for NVR endpoint methods."""

    async def test_nvr_get(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting NVR."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/nvrs",
            payload={"data": {"id": "nvr-1", "mac": "AA:BB:CC:DD:EE:FF", "name": "NVR"}},
        )

        nvr = await protect_client.nvr.get()
        assert nvr.id == "nvr-1"

    async def test_nvr_update(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test updating NVR."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/nvr",
            payload={"data": {"id": "nvr-1", "mac": "AA:BB:CC:DD:EE:FF", "name": "Updated"}},
        )

        nvr = await protect_client.nvr.update(name="Updated")
        assert nvr.name == "Updated"

    async def test_nvr_restart(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test restarting NVR."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/nvr/restart",
            payload={},
        )

        result = await protect_client.nvr.restart()
        assert result is True

    async def test_nvr_set_recording_retention(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test setting NVR recording retention."""
        nvr_data = {
            "id": "nvr-1",
            "mac": "AA:BB:CC:DD:EE:FF",
            "recordingRetentionDays": 30,
        }
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/nvr",
            payload={"data": nvr_data},
        )

        nvr = await protect_client.nvr.set_recording_retention(30)
        assert nvr is not None


class TestLiveViewsEndpoint:
    """Tests for liveviews endpoint methods."""

    async def test_liveviews_get_all(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing liveviews."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/liveviews",
            payload={"data": [{"id": "lv-1", "name": "Main View", "layout": 4}]},
        )

        liveviews = await protect_client.liveviews.get_all()
        assert len(liveviews) == 1

    async def test_liveviews_get(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting a liveview."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/liveviews/lv-1",
            payload={"data": {"id": "lv-1", "name": "Main View", "layout": 4}},
        )

        liveview = await protect_client.liveviews.get("lv-1")
        assert liveview.id == "lv-1"

    async def test_liveviews_create(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test creating a liveview."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/liveviews",
            payload={"data": {"id": "lv-1", "name": "New View", "layout": 4}},
        )

        liveview = await protect_client.liveviews.create(name="New View", layout=4)
        assert liveview.name == "New View"

    async def test_liveviews_update(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test updating a liveview."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/liveviews/lv-1",
            payload={"data": {"id": "lv-1", "name": "Updated", "layout": 4}},
        )

        liveview = await protect_client.liveviews.update("lv-1", name="Updated")
        assert liveview.name == "Updated"

    async def test_liveviews_delete(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test deleting a liveview."""
        mock_aioresponse.delete(
            "https://192.168.1.1/proxy/protect/integration/v1/liveviews/lv-1",
            status=200,
        )

        result = await protect_client.liveviews.delete("lv-1")
        assert result is True


class TestEventsEndpoint:
    """Tests for events endpoint methods."""

    async def test_events_get_all(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing events."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/events?limit=100",
            payload={"data": [{"id": "ev-1", "type": "motion", "start": 1234567890000}]},
        )

        events = await protect_client.events.get_all()
        assert len(events) == 1

    async def test_events_get(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting an event."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/events/ev-1",
            payload={"data": {"id": "ev-1", "type": "motion", "start": 1234567890000}},
        )

        event = await protect_client.events.get("ev-1")
        assert event.id == "ev-1"

    async def test_events_get_thumbnail(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting event thumbnail."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/events/ev-1/thumbnail",
            body=b"fake_thumb_data",
        )

        thumbnail = await protect_client.events.get_thumbnail("ev-1")
        assert thumbnail == b"fake_thumb_data"

    async def test_events_get_heatmap(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting event heatmap."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/events/ev-1/heatmap",
            body=b"fake_heatmap_data",
        )

        heatmap = await protect_client.events.get_heatmap("ev-1")
        assert heatmap == b"fake_heatmap_data"

    async def test_events_list_motion_events(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing motion events."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/events?limit=100&types=motion",
            payload={"data": [{"id": "ev-1", "type": "motion", "start": 1234567890000}]},
        )

        events = await protect_client.events.list_motion_events()
        assert len(events) == 1

    async def test_events_list_smart_detect_events(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing smart detect events."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/events?limit=100&types=smartDetect",
            payload={"data": [{"id": "ev-1", "type": "smartDetect", "start": 1234567890000}]},
        )

        events = await protect_client.events.list_smart_detect_events()
        assert len(events) == 1


class TestProtectClientBinary:
    """Tests for binary response handling."""

    async def test_get_binary(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test binary data retrieval."""
        camera_id = sample_camera["id"]
        mock_aioresponse.get(
            f"https://192.168.1.1/proxy/protect/integration/v1/cameras/{camera_id}/snapshot",
            body=b"fake_binary_data",
            content_type="image/jpeg",
        )

        data = await protect_client.cameras.get_snapshot(camera_id)
        assert data == b"fake_binary_data"
