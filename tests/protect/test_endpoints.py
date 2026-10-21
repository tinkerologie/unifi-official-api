"""Tests for UniFi Protect endpoint methods."""

from __future__ import annotations

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
