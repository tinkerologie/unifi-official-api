"""Tests for UniFi Site Manager client and endpoints."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from unifi_official_api import ApiKeyAuth
from unifi_official_api.exceptions import UniFiNotFoundError
from unifi_official_api.site_manager import (
    DeviceListResponse,
    Host,
    HostListResponse,
    ISPMetric,
    ISPMetricQuery,
    ISPMetricQueryResult,
    SDWanConfig,
    SDWanConfigDetail,
    SDWanStatus,
    SiteListResponse,
    UniFiSiteManagerClient,
)


class TestUniFiSiteManagerClient:
    """Tests for UniFiSiteManagerClient."""

    @pytest.fixture
    def client(self) -> UniFiSiteManagerClient:
        """Create Site Manager client."""
        return UniFiSiteManagerClient(
            auth=ApiKeyAuth(api_key="cloud-api-key"),
        )

    async def test_hosts_endpoints(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test hosts endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/hosts?limit=25&nextToken=prev-tok",
            payload={
                "data": [
                    {
                        "id": "host-1",
                        "hardwareId": "HW-12345",
                        "ipAddress": "192.168.10.1",
                        "isBlocked": False,
                        "reportedState": {"state": "CONNECTED", "hostname": "UDM-Pro"},
                    }
                ],
                "nextToken": "tok-1",
            },
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/hosts/host-1",
            payload={
                "data": {
                    "id": "host-1",
                    "hardwareId": "HW-12345",
                    "ipAddress": "192.168.10.1",
                    "isBlocked": False,
                }
            },
        )
        mock_aioresponse.get("https://api.ui.com/v1/hosts?limit=10", payload=None)
        mock_aioresponse.get("https://api.ui.com/v1/hosts/bad-id", payload={})

        async with client:
            hosts = await client.hosts.get_all(next_token="prev-tok")
            assert isinstance(hosts, HostListResponse)
            assert len(hosts.data) == 1
            assert hosts.data[0].id == "host-1"
            assert hosts.next_token == "tok-1"

            empty_hosts = await client.hosts.get_all(limit=10)
            assert empty_hosts.data == []

            host = await client.hosts.get("host-1")
            assert isinstance(host, Host)
            assert host.hardware_id == "HW-12345"

            with pytest.raises(UniFiNotFoundError):
                await client.hosts.get("bad-id")

    async def test_sites_endpoints(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test sites endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/sites?limit=25&nextToken=tok",
            payload={
                "data": [
                    {
                        "siteId": "site-1",
                        "hostId": "host-1",
                        "meta": {"name": "Office HQ"},
                        "statistics": {"deviceCount": 10, "clientCount": 55},
                    }
                ]
            },
        )
        mock_aioresponse.get("https://api.ui.com/v1/sites?limit=10", payload=None)

        async with client:
            sites = await client.sites.get_all(next_token="tok")
            assert isinstance(sites, SiteListResponse)
            assert len(sites.data) == 1
            assert sites.data[0].site_id == "site-1"
            assert sites.data[0].meta is not None
            assert sites.data[0].meta.name == "Office HQ"

            empty = await client.sites.get_all(limit=10)
            assert empty.data == []

    async def test_devices_endpoints(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test devices endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/devices?limit=25&nextToken=tok",
            payload={
                "data": [
                    {
                        "hostId": "host-1",
                        "hostName": "UDM-Pro",
                        "devices": [
                            {"mac": "aa:bb:cc:dd:ee:ff", "model": "UDMPRO", "name": "UDM Pro"}
                        ],
                    }
                ]
            },
        )
        mock_aioresponse.get("https://api.ui.com/v1/devices?limit=10", payload=None)

        async with client:
            devs = await client.devices.get_all(next_token="tok")
            assert isinstance(devs, DeviceListResponse)
            assert len(devs.data) == 1
            assert devs.data[0].host_id == "host-1"
            assert len(devs.data[0].devices) == 1
            assert devs.data[0].devices[0].mac == "aa:bb:cc:dd:ee:ff"

            empty = await client.devices.get_all(limit=10)
            assert empty.data == []

    async def test_isp_metrics_endpoints(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test ISP metrics endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/isp-metrics/latency?duration=24h&hostId=host-1",
            payload={"data": [{"metricType": "latency", "value": 12.5}]},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/isp-metrics/throughput",
            payload=None,
        )
        mock_aioresponse.post(
            "https://api.ui.com/v1/isp-metrics/latency/query",
            payload={"data": {"metrics": [{"metricType": "latency", "value": 14.2}]}},
        )
        mock_aioresponse.post(
            "https://api.ui.com/v1/isp-metrics/throughput/query",
            payload={},
        )

        async with client:
            metrics = await client.isp_metrics.get_metrics(
                "latency", host_id="host-1", duration="24h"
            )
            assert len(metrics) == 1
            assert isinstance(metrics[0], ISPMetric)
            assert metrics[0].value == 12.5

            empty_metrics = await client.isp_metrics.get_metrics("throughput")
            assert empty_metrics == []

            query_result = await client.isp_metrics.query(
                "latency", ISPMetricQuery(host_ids=["host-1"])
            )
            assert isinstance(query_result, ISPMetricQueryResult)
            assert len(query_result.metrics) == 1
            assert query_result.metrics[0].value == 14.2

            empty_query = await client.isp_metrics.query("throughput", {})
            assert empty_query.metrics == []

    async def test_sd_wan_endpoints(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test SD-WAN endpoints."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/sd-wan-configs",
            payload={"data": [{"id": "sdwan-1", "name": "Mesh VPN", "type": "site-to-site"}]},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/sd-wan-configs/sdwan-1",
            payload={
                "data": {
                    "id": "sdwan-1",
                    "name": "Mesh VPN",
                    "type": "site-to-site",
                    "topologies": [],
                    "nodes": [],
                }
            },
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/sd-wan-configs/sdwan-1/status",
            payload={"data": {"id": "sdwan-1", "status": "HEALTHY", "tunnels": []}},
        )
        mock_aioresponse.get("https://api.ui.com/v1/sd-wan-configs", payload=None)
        mock_aioresponse.get("https://api.ui.com/v1/sd-wan-configs/bad-id", payload={})
        mock_aioresponse.get("https://api.ui.com/v1/sd-wan-configs/bad-id/status", payload={})

        async with client:
            configs = await client.sd_wan.get_configs()
            assert len(configs) == 1
            assert isinstance(configs[0], SDWanConfig)

            cfg = await client.sd_wan.get_config("sdwan-1")
            assert isinstance(cfg, SDWanConfigDetail)
            assert cfg.id == "sdwan-1"

            st = await client.sd_wan.get_status("sdwan-1")
            assert isinstance(st, SDWanStatus)
            assert st.status == "HEALTHY"

            empty_configs = await client.sd_wan.get_configs()
            assert empty_configs == []

            with pytest.raises(UniFiNotFoundError):
                await client.sd_wan.get_config("bad-id")

            with pytest.raises(UniFiNotFoundError):
                await client.sd_wan.get_status("bad-id")

    async def test_connector_proxy(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test Cloud Connector proxy endpoint."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/connector/consoles/console-123/network/integration/v1/info",
            payload={"applicationVersion": "10.4.57"},
        )
        async with client:
            res = await client.connector.proxy("console-123", "/network/integration/v1/info")
            assert isinstance(res, dict)
            assert res.get("applicationVersion") == "10.4.57"

    async def test_validate_connection(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test connection validation."""
        mock_aioresponse.get(
            "https://api.ui.com/v1/hosts?limit=1",
            payload={"data": []},
        )
        async with client:
            assert await client.validate_connection() is True
