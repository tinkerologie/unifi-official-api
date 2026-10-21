"""Pytest configuration and fixtures."""

import inspect
from typing import Any
from unittest.mock import Mock

import aioresponses.core as aioresponses_core
import pytest
from aiohttp import ClientResponse
from aioresponses import aioresponses

from unifi_official_api import ApiKeyAuth, LocalAuth
from unifi_official_api.const import ConnectionType
from unifi_official_api.network import UniFiNetworkClient
from unifi_official_api.protect import UniFiProtectClient

# aiohttp 3.14 added a required keyword-only ``stream_writer`` argument to
# ``ClientResponse.__init__``, which aioresponses 0.7.9 (the latest release) does
# not pass. The argument is only read for its ``output_size``, so a mock is enough.
# Remove this shim once aioresponses ships the upstream fix
# (pnuckowski/aioresponses#288).
if "stream_writer" in inspect.signature(ClientResponse).parameters:

    class _ClientResponse(ClientResponse):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs.setdefault("stream_writer", Mock(output_size=0))
            super().__init__(*args, **kwargs)

    setattr(aioresponses_core, "ClientResponse", _ClientResponse)  # noqa: B010


@pytest.fixture
def api_key() -> str:
    """Return a test API key."""
    return "test-api-key-12345"


@pytest.fixture
def auth(api_key: str) -> ApiKeyAuth:
    """Return a test ApiKeyAuth instance."""
    return ApiKeyAuth(api_key=api_key)


@pytest.fixture
def local_auth(api_key: str) -> LocalAuth:
    """Return a test LocalAuth instance."""
    return LocalAuth(api_key=api_key, verify_ssl=False)


@pytest.fixture
def host_id() -> str:
    """Return a test host ID (used as console_id for REMOTE)."""
    return "test-host-id"


@pytest.fixture
def console_id() -> str:
    """Return a test console ID."""
    return "test-console-id"


@pytest.fixture
def site_id() -> str:
    """Return a test site ID."""
    return "test-site-id"


@pytest.fixture
def base_url() -> str:
    """Return a test base URL for local connection."""
    return "https://192.168.1.1"


@pytest.fixture
def mock_aioresponse():
    """Provide aioresponses mock context manager."""
    with aioresponses() as m:
        yield m


@pytest.fixture
async def network_client(local_auth: LocalAuth, base_url: str) -> UniFiNetworkClient:
    """Create a UniFi Network client for testing (LOCAL connection)."""
    client = UniFiNetworkClient(
        auth=local_auth,
        base_url=base_url,
        connection_type=ConnectionType.LOCAL,
    )
    yield client
    await client.close()


@pytest.fixture
async def protect_client(local_auth: LocalAuth, base_url: str) -> UniFiProtectClient:
    """Create a UniFi Protect client for testing (LOCAL connection)."""
    client = UniFiProtectClient(
        auth=local_auth,
        base_url=base_url,
        connection_type=ConnectionType.LOCAL,
    )
    yield client
    await client.close()


@pytest.fixture
def sample_device() -> dict[str, Any]:
    """Return sample device data."""
    return {
        "id": "device-123",
        "macAddress": "00:11:22:33:44:55",
        "name": "Test Switch",
        "model": "USW-24-POE",
        "type": "usw",
        "state": "ONLINE",
        "ip": "192.168.1.10",
        "firmwareVersion": "6.5.28",
        "uptime": 86400,
        "adopted": True,
        "siteId": "site-123",
    }


@pytest.fixture
def sample_client() -> dict[str, Any]:
    """Return sample client data."""
    return {
        "id": "client-123",
        "macAddress": "AA:BB:CC:DD:EE:FF",
        "name": "Test Device",
        "hostname": "test-device",
        "ipAddress": "192.168.1.100",
        "type": "WIRELESS",
        "connected": True,
        "txBytes": 1000000,
        "rxBytes": 2000000,
    }


@pytest.fixture
def sample_camera() -> dict[str, Any]:
    """Return sample camera data."""
    return {
        "id": "camera-123",
        "mac": "11:22:33:44:55:66",
        "name": "Front Door",
        "type": "UVC G4 Doorbell",
        "model": "UVC G4 Doorbell",
        "state": "CONNECTED",
        "host": "192.168.1.50",
        "firmwareVersion": "4.63.22",
        "isConnected": True,
        "isRecording": True,
        "recordingMode": "always",
        "micVolume": 100,
        "speakerVolume": 80,
    }


@pytest.fixture
def sample_sensor() -> dict[str, Any]:
    """Return sample sensor data."""
    return {
        "id": "sensor-123",
        "mac": "22:33:44:55:66:77",
        "name": "Front Door Sensor",
        "type": "door",
        "isConnected": True,
        "isOpened": False,
        "batteryLevel": 95,
        "batteryStatus": {"percentage": 95, "isLow": False},
    }
