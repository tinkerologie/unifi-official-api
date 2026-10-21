"""Tests for UniFi Protect client."""

from __future__ import annotations

from typing import Any

import pytest
from aioresponses import aioresponses

from unifi_official_api import LocalAuth
from unifi_official_api.const import ConnectionType
from unifi_official_api.protect import UniFiProtectClient


class TestUniFiProtectClient:
    """Tests for UniFiProtectClient."""

    async def test_client_creation_local(self, local_auth: LocalAuth, base_url: str) -> None:
        """Test client creation with LOCAL connection type."""
        async with UniFiProtectClient(
            auth=local_auth,
            base_url=base_url,
            connection_type=ConnectionType.LOCAL,
        ) as client:
            assert client.base_url.host == "192.168.1.1"
            assert not client.closed
            assert client.connection_type == ConnectionType.LOCAL

    async def test_client_creation_remote(self, auth: LocalAuth, console_id: str) -> None:
        """Test client creation with REMOTE connection type."""
        async with UniFiProtectClient(
            auth=auth,
            connection_type=ConnectionType.REMOTE,
            console_id=console_id,
        ) as client:
            assert client.base_url.host == "api.ui.com"
            assert client.connection_type == ConnectionType.REMOTE
            assert client.console_id == console_id

    async def test_client_creation_remote_requires_console_id(self, auth: LocalAuth) -> None:
        """Test that REMOTE connection requires console_id."""
        with pytest.raises(ValueError, match="console_id is required"):
            UniFiProtectClient(
                auth=auth,
                connection_type=ConnectionType.REMOTE,
            )

    async def test_client_creation_local_requires_base_url(self, local_auth: LocalAuth) -> None:
        """Test that LOCAL connection requires base_url."""
        with pytest.raises(ValueError, match="base_url is required"):
            UniFiProtectClient(
                auth=local_auth,
                connection_type=ConnectionType.LOCAL,
            )

    async def test_client_close(self, local_auth: LocalAuth, base_url: str) -> None:
        """Test client close."""
        client = UniFiProtectClient(
            auth=local_auth,
            base_url=base_url,
            connection_type=ConnectionType.LOCAL,
        )
        assert not client.closed
        await client.close()
        assert client.closed

    async def test_endpoints_available(self, local_auth: LocalAuth, base_url: str) -> None:
        """Test that all endpoints are available."""
        async with UniFiProtectClient(
            auth=local_auth,
            base_url=base_url,
            connection_type=ConnectionType.LOCAL,
        ) as client:
            assert client.cameras is not None
            assert client.sensors is not None
            assert client.lights is not None
            assert client.chimes is not None
            assert client.nvr is not None
            assert client.liveviews is not None
            assert client.events is not None

    async def test_build_api_path_local(self, local_auth: LocalAuth, base_url: str) -> None:
        """Test build_api_path for LOCAL connection."""
        async with UniFiProtectClient(
            auth=local_auth,
            base_url=base_url,
            connection_type=ConnectionType.LOCAL,
        ) as client:
            # LOCAL connection should NOT include site_id in path
            path = client.build_api_path("/cameras")
            assert path == "/proxy/protect/integration/v1/cameras"

    async def test_build_api_path_remote(self, auth: LocalAuth, console_id: str) -> None:
        """Test build_api_path for REMOTE connection."""
        async with UniFiProtectClient(
            auth=auth,
            connection_type=ConnectionType.REMOTE,
            console_id=console_id,
        ) as client:
            # REMOTE connection no longer uses site_id
            path = client.build_api_path("/cameras")
            expected = f"/v1/connector/consoles/{console_id}/protect/integration/v1/cameras"
            assert path == expected


class TestCamerasEndpoint:
    """Tests for cameras endpoint."""

    async def test_list_cameras(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test listing cameras."""
        # LOCAL connection doesn't use site_id in path
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras",
            payload={"data": [sample_camera]},
        )

        cameras = await protect_client.cameras.get_all()
        assert len(cameras) == 1
        assert cameras[0].id == "camera-123"
        assert cameras[0].name == "Front Door"
        assert cameras[0].is_recording is True

    async def test_get_camera(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_camera: dict[str, Any],
    ) -> None:
        """Test getting a specific camera."""
        camera_id = sample_camera["id"]
        # LOCAL connection doesn't use site_id in path
        mock_aioresponse.get(
            f"https://192.168.1.1/proxy/protect/integration/v1/cameras/{camera_id}",
            payload={"data": sample_camera},
        )

        camera = await protect_client.cameras.get(camera_id)
        assert camera.id == camera_id
        assert camera.mic_volume == 100
        assert camera.speaker_volume == 80


class TestSensorsEndpoint:
    """Tests for sensors endpoint."""

    async def test_list_sensors(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
        sample_sensor: dict[str, Any],
    ) -> None:
        """Test listing sensors."""
        # LOCAL connection doesn't use site_id in path
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/sensors",
            payload={"data": [sample_sensor]},
        )

        sensors = await protect_client.sensors.get_all()
        assert len(sensors) == 1
        assert sensors[0].id == "sensor-123"
        assert sensors[0].is_opened is False
        assert sensors[0].battery_level == 95
