"""Tests for UniFi InnerSpace client and endpoints."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from unifi_official_api import (
    ApiKeyAuth,
    ConnectionType,
    LocalAuth,
    UniFiConnectionError,
    UniFiResponseError,
)
from unifi_official_api.innerspace import (
    FloorPlan,
    InnerSpaceAccessPoint,
    InnerSpaceSwitch,
    InventoryDevice,
    ProjectData,
    UniFiInnerSpaceClient,
)


class TestUniFiInnerSpaceClient:
    """Tests for UniFiInnerSpaceClient."""

    @pytest.fixture
    def local_client(self) -> UniFiInnerSpaceClient:
        """Create local InnerSpace client."""
        return UniFiInnerSpaceClient(
            auth=LocalAuth(api_key="test-key", verify_ssl=False),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        )

    @pytest.fixture
    def remote_client(self) -> UniFiInnerSpaceClient:
        """Create remote InnerSpace client."""
        return UniFiInnerSpaceClient(
            auth=ApiKeyAuth(api_key="test-key"),
            connection_type=ConnectionType.REMOTE,
            console_id="console-123",
        )

    async def test_client_init(
        self, local_client: UniFiInnerSpaceClient, remote_client: UniFiInnerSpaceClient
    ) -> None:
        """Test client initialization and path builders."""
        assert local_client.connection_type == ConnectionType.LOCAL
        assert remote_client.connection_type == ConnectionType.REMOTE
        assert remote_client.console_id == "console-123"

        assert (
            local_client.build_api_path("floor_plans")
            == "/proxy/innerspace/integration/v1/floor_plans"
        )
        assert (
            remote_client.build_api_path("floor_plans")
            == "/v1/connector/consoles/console-123/innerspace/integration/v1/floor_plans"
        )

        with pytest.raises(ValueError, match="base_url is required"):
            UniFiInnerSpaceClient(
                auth=LocalAuth(api_key="k"),
                connection_type=ConnectionType.LOCAL,
            )

        with pytest.raises(ValueError, match="console_id is required"):
            UniFiInnerSpaceClient(
                auth=ApiKeyAuth(api_key="k"),
                connection_type=ConnectionType.REMOTE,
            )

    async def test_project_endpoint(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test project endpoint."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/project",
            payload={
                "data": {
                    "project": {"id": "proj-1", "title": "Headquarters"},
                    "shapes": [],
                    "plans": [],
                    "products": [],
                    "wallTypes": [],
                    "attenuationObjectTypes": [],
                }
            },
        )
        async with local_client:
            proj = await local_client.project.get()
            assert isinstance(proj, ProjectData)
            assert proj.project is not None
            assert proj.project.title == "Headquarters"

    async def test_project_endpoint_error(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test project endpoint error branch."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/project", payload="bad"
        )
        async with local_client:
            with pytest.raises(UniFiResponseError):
                await local_client.project.get()

    async def test_floor_plans_endpoint(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test floor plans endpoint."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/floor_plans?siteId=site-1",
            payload={
                "floor_plans": [{"id": "fp-1", "name": "1st Floor", "floor_number": 1, "ppm": 10.5}]
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/floor_plans",
            payload=None,
        )
        async with local_client:
            plans = await local_client.floor_plans.get_all(site_id="site-1")
            assert len(plans) == 1
            assert isinstance(plans[0], FloorPlan)
            assert plans[0].name == "1st Floor"

            empty = await local_client.floor_plans.get_all()
            assert empty == []

    async def test_access_points_endpoint(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test access points endpoint."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/access_points?siteId=site-1",
            payload={
                "access_points": [
                    {
                        "id": "ap-1",
                        "name": "AP Lobby",
                        "model": "U6-Pro",
                        "mac": "aa:bb:cc:dd:ee:ff",
                        "serial": "SNaabbccddeeff",
                        "floor_plan_id": "fp-1",
                        "x": 120.5,
                        "y": 85.0,
                        "height": 2.8,
                        "azimuth": 90,
                        "mount": "ceiling",
                        "status": "online",
                    }
                ]
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/access_points",
            payload=None,
        )
        async with local_client:
            aps = await local_client.access_points.get_all(site_id="site-1")
            assert len(aps) == 1
            assert isinstance(aps[0], InnerSpaceAccessPoint)
            assert aps[0].model == "U6-Pro"
            assert aps[0].x == 120.5

            empty = await local_client.access_points.get_all()
            assert empty == []

    async def test_switches_endpoint(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test switches endpoint."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/switches?siteId=site-1",
            payload={
                "switches": [
                    {
                        "id": "sw-1",
                        "name": "Switch Core",
                        "model": "USW-Pro-24-PoE",
                        "type": "switch",
                        "mac": "11:22:33:44:55:66",
                        "serial": "SN112233445566",
                        "floor_plan_id": "fp-1",
                        "x": 50.0,
                        "y": 50.0,
                        "status": "online",
                    }
                ]
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/switches",
            payload=None,
        )
        async with local_client:
            sws = await local_client.switches.get_all(site_id="site-1")
            assert len(sws) == 1
            assert isinstance(sws[0], InnerSpaceSwitch)
            assert sws[0].name == "Switch Core"

            empty = await local_client.switches.get_all()
            assert empty == []

    async def test_inventory_endpoint(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test inventory endpoint."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/inventory?siteId=site-1",
            payload={
                "devices": [
                    {
                        "id": "inv-1",
                        "name": "Spare AP",
                        "model": "U6-Mesh",
                        "mac": "99:88:77:66:55:44",
                        "serial": "SN998877665544",
                    }
                ]
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/inventory",
            payload=None,
        )
        async with local_client:
            devs = await local_client.inventory.get_all(site_id="site-1")
            assert len(devs) == 1
            assert isinstance(devs[0], InventoryDevice)
            assert devs[0].name == "Spare AP"

            empty = await local_client.inventory.get_all()
            assert empty == []

    async def test_assets_download(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test downloading asset binary."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/assets/fp-1/floorplan.png",
            body=b"\x89PNG\r\n\x1a\nfakeimage",
            content_type="image/png",
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/assets/fp-1/bad.png",
            status=404,
        )
        async with local_client:
            data = await local_client.assets.download("fp-1", "floorplan.png")
            assert data.startswith(b"\x89PNG")

            with pytest.raises(
                UniFiConnectionError, match="Failed to fetch binary asset: HTTP 404"
            ):
                await local_client.assets.download("fp-1", "bad.png")

    async def test_validate_connection(
        self, local_client: UniFiInnerSpaceClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test validate_connection."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/project",
            payload={"project": {"id": "p1"}},
        )
        async with local_client:
            assert await local_client.validate_connection() is True
