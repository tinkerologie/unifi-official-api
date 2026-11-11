"""Tests for UniFi Mobility client and endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from aioresponses import aioresponses

from unifi_official_api import ApiKeyAuth
from unifi_official_api.exceptions import (
    UniFiNotFoundError,
    UniFiResponseError,
    UniFiValidationError,
)
from unifi_official_api.mobility import (
    AdminSummary,
    MobilityDeviceClient,
    MobilityDeviceDetail,
    MobilityDeviceSummary,
    UniFiMobilityClient,
    UpdateDeviceNameReq,
    UpdateNetworkReq,
    UpdateWirelessReq,
    WorkspaceSummary,
)


class TestUniFiMobilityClient:
    """Tests for UniFiMobilityClient."""

    @pytest.fixture
    def client(self) -> UniFiMobilityClient:
        """Create Mobility client."""
        return UniFiMobilityClient(
            auth=ApiKeyAuth(api_key="cloud-api-key"),
        )

    async def test_workspaces_endpoints(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test workspaces endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces",
            payload={
                "data": [
                    {
                        "workspace_id": "ws-1",
                        "workspace_name": "Fleet Ops",
                        "is_owner": True,
                        "status": "ACTIVE",
                    }
                ]
            },
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/admins",
            payload={
                "data": [
                    {
                        "name": "Admin User",
                        "email": "admin@example.com",
                        "is_owner": True,
                        "status": "ACTIVE",
                    }
                ]
            },
        )
        mock_aioresponse.get("https://api.ui.com/v1/mobility/workspaces", payload=None)
        mock_aioresponse.get("https://api.ui.com/v1/mobility/workspaces/ws-1/admins", payload=None)

        async with client:
            workspaces = await client.workspaces.get_all()
            assert len(workspaces) == 1
            assert isinstance(workspaces[0], WorkspaceSummary)
            assert workspaces[0].workspace_id == "ws-1"

            admins = await client.workspaces.get_admins("ws-1")
            assert len(admins) == 1
            assert isinstance(admins[0], AdminSummary)
            assert admins[0].email == "admin@example.com"

            assert await client.workspaces.get_all() == []
            assert await client.workspaces.get_admins("ws-1") == []

    async def test_devices_endpoints(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test devices endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices",
            payload={
                "data": [
                    {
                        "id": "dev-1",
                        "name": "Vehicle Router",
                        "model": "UMR",
                        "state": "CONNECTED",
                        "firmware_version": "3.1.14",
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                    }
                ]
            },
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1",
            payload={
                "data": {
                    "id": "dev-1",
                    "name": "Vehicle Router",
                    "model": "UMR",
                    "state": "CONNECTED",
                    "firmware_version": "3.1.14",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "wan_source": "LTE",
                    "location": {
                        "latitude": 37.7749,
                        "longitude": -122.4194,
                        "last_updated": 1709712000000,
                    },
                }
            },
        )
        mock_aioresponse.get("https://api.ui.com/v1/mobility/workspaces/ws-1/devices", payload=None)
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/bad-id", payload={}
        )
        mock_aioresponse.put(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1", status=200
        )
        mock_aioresponse.put(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1", status=200
        )

        async with client:
            devices = await client.devices.get_all("ws-1")
            assert len(devices) == 1
            assert isinstance(devices[0], MobilityDeviceSummary)

            detail = await client.devices.get("ws-1", "dev-1")
            assert isinstance(detail, MobilityDeviceDetail)
            assert detail.location is not None
            assert detail.location.latitude == 37.7749

            assert await client.devices.get_all("ws-1") == []

            with pytest.raises(UniFiNotFoundError):
                await client.devices.get("ws-1", "bad-id")

            await client.devices.update_name("ws-1", "dev-1", "New Name")
            await client.devices.update_name(
                "ws-1", "dev-1", UpdateDeviceNameReq(name="New Name 2")
            )

    async def test_clients_and_config_endpoints(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test clients and configuration endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1/clients",
            payload={
                "data": [
                    {
                        "mac": "11:22:33:44:55:66",
                        "name": "Tablet",
                        "type": "WIRELESS",
                        "connection_status": "ONLINE",
                        "ip_address": "192.168.10.50",
                        "is_blocked": False,
                    }
                ]
            },
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1/clients", payload=None
        )
        mock_aioresponse.put(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1/network", status=200
        )
        mock_aioresponse.put(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1/network", status=200
        )
        mock_aioresponse.put(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1/wireless", status=200
        )
        mock_aioresponse.put(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1/wireless", status=200
        )

        async with client:
            clients = await client.clients.get_all("ws-1", "dev-1")
            assert len(clients) == 1
            assert isinstance(clients[0], MobilityDeviceClient)
            assert clients[0].mac == "11:22:33:44:55:66"

            assert await client.clients.get_all("ws-1", "dev-1") == []

            await client.network.update(
                "ws-1",
                "dev-1",
                UpdateNetworkReq(host_address="192.168.10.1", dhcp_mode="dhcp"),
            )
            await client.network.update(
                "ws-1",
                "dev-1",
                {"host_address": "192.168.10.1"},
            )
            await client.wireless.update(
                "ws-1",
                "dev-1",
                UpdateWirelessReq(ssid="FleetWiFi", password="password123"),
            )
            await client.wireless.update(
                "ws-1",
                "dev-1",
                {"ssid": "FleetWiFi", "password": "password123"},
            )

    async def test_validate_connection(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test connection validation."""
        mock_aioresponse.get("https://api.ui.com/v1/mobility/workspaces", payload={"data": []})
        async with client:
            assert await client.validate_connection() is True

    async def test_typed_device_pages_are_followed_by_the_caller(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        path = "https://api.ui.com/v1/mobility/workspaces/ws-1/devices"
        device = {"name": "Router", "firmware_version": "1.0", "mac_address": "00:00:00:00:00:00"}
        mock_aioresponse.get(f"{path}?limit=1&offset=0", payload={"data": [{**device, "id": "a"}]})
        mock_aioresponse.get(f"{path}?limit=1&offset=1", payload={"data": [{**device, "id": "b"}]})
        mock_aioresponse.get(f"{path}?offset=2", payload={"data": []})

        async with client:
            first = await client.devices.get_all("ws-1", limit=1, offset=0)
            assert len(mock_aioresponse.requests) == 1
            second = await client.devices.get_all("ws-1", limit=1, offset=1)
            assert await client.devices.get_all("ws-1", offset=2) == []

        assert [item.id for item in first + second] == ["a", "b"]
        assert first[0].state == "CONNECTED"
        assert first[0].model == "UMR"
        assert {"state", "model"}.isdisjoint(first[0].model_fields_set)

    async def test_typed_workspaces_accept_a_bare_list_and_preserve_explicit_false(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces",
            payload=[{"workspace_id": "ws-1", "workspace_name": "Fleet", "is_owner": False}],
        )
        async with client:
            (workspace,) = await client.workspaces.get_all()

        assert workspace.is_owner is False
        assert workspace.status == "ACTIVE"
        assert "status" not in workspace.model_fields_set

    @pytest.mark.parametrize("payload", [{}, {"data": []}, {"data": None}, {"data": {}}])
    async def test_typed_device_list_has_empty_fallback(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses, payload: object
    ) -> None:
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices", payload=payload
        )
        async with client:
            assert await client.devices.get_all("ws-1") == []

    async def test_typed_device_rejects_a_malformed_record(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices",
            payload={"data": [{"name": "private-value"}]},
        )
        async with client:
            with pytest.raises(UniFiResponseError) as error:
                await client.devices.get_all("ws-1")

        assert error.value.status_code == 200
        assert "private-value" not in error.value.message
        assert error.value.__cause__ is None

    @pytest.mark.parametrize(
        "read",
        [
            lambda c: c.workspaces.get_admins("../admins"),
            lambda c: c.devices.get_all("../devices"),
            lambda c: c.devices.get("../devices", "dev-1"),
            lambda c: c.devices.get("ws-1", "dev/1"),
            lambda c: c.clients.get_all("ws-1", "dev%2F1"),
            lambda c: c.clients.get_all("../workspaces", "dev-1"),
        ],
    )
    async def test_typed_reads_reject_unsafe_ids_before_request(
        self,
        client: UniFiMobilityClient,
        mock_aioresponse: aioresponses,
        read: Callable[[UniFiMobilityClient], Awaitable[object]],
    ) -> None:
        with pytest.raises(UniFiValidationError, match="Invalid Mobility identifier"):
            await read(client)

        assert mock_aioresponse.requests == {}

    async def test_typed_device_detail_uses_first_list_record(
        self, client: UniFiMobilityClient, mock_aioresponse: aioresponses
    ) -> None:
        device = {
            "id": "dev-1",
            "name": "Router",
            "firmware_version": "1.0",
            "mac_address": "00:00:00:00:00:00",
            "client_count": 0,
            "wifi_enabled": False,
        }
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1",
            payload={"data": [device, {"id": "dev-2"}]},
        )
        async with client:
            detail = await client.devices.get("ws-1", "dev-1")

        assert detail.id == "dev-1"
        assert detail.client_count == 0
        assert detail.wifi_enabled is False
