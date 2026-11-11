"""Tests for UniFi Site Manager client and endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from aioresponses import aioresponses
from pydantic import ValidationError
from yarl import URL

from unifi_official_api import ApiKeyAuth
from unifi_official_api.exceptions import (
    UniFiNotFoundError,
    UniFiResponseError,
    UniFiValidationError,
)
from unifi_official_api.site_manager import (
    DeviceListResponse,
    Host,
    HostListResponse,
    ISPMetric,
    ISPMetricQuery,
    ISPMetricQueryResult,
    ISPMetricQuerySite,
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
            "https://api.ui.com/v1/hosts?pageSize=25&nextToken=prev-tok",
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
        mock_aioresponse.get("https://api.ui.com/v1/hosts?pageSize=10", payload=None)
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

    async def test_typed_host_pages_are_followed_by_the_caller(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        mock_aioresponse.get(
            "https://api.ui.com/v1/hosts?pageSize=1",
            payload={"data": [{"id": "host-1"}], "nextToken": "second"},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/hosts?pageSize=1&nextToken=second",
            payload={"data": [{"id": "host-2", "isBlocked": False}], "nextToken": ""},
        )

        async with client:
            first = await client.hosts.get_all(limit=1, next_token="")
            assert len(mock_aioresponse.requests) == 1
            second = await client.hosts.get_all(limit=1, next_token=first.next_token)

        assert [host.id for host in first.data + second.data] == ["host-1", "host-2"]
        assert first.data[0].is_blocked is False
        assert "is_blocked" not in first.data[0].model_fields_set
        assert "is_blocked" in second.data[0].model_fields_set
        assert second.next_token == ""

    @pytest.mark.parametrize("payload", [{}, {"data": []}, []])
    async def test_typed_host_empty_pages(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses, payload: object
    ) -> None:
        mock_aioresponse.get("https://api.ui.com/v1/hosts?pageSize=25", payload=payload)

        async with client:
            assert await client.hosts.get_all() == HostListResponse()

    @pytest.mark.parametrize("payload", [{"data": None}, {"data": [{"type": "private-value"}]}])
    async def test_typed_host_rejects_invalid_enveloped_data(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses, payload: object
    ) -> None:
        mock_aioresponse.get("https://api.ui.com/v1/hosts?pageSize=25", payload=payload)

        async with client:
            with pytest.raises(UniFiResponseError) as error:
                await client.hosts.get_all()
        assert error.value.status_code == 200
        assert "private-value" not in error.value.message
        assert error.value.__cause__ is None

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

    async def test_typed_isp_metrics_keep_sites_and_samples_distinct(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        start = datetime(2024, 6, 30, 13, 35, tzinfo=UTC)
        end = datetime(2024, 6, 30, 16, 35, tzinfo=timezone(timedelta(hours=1)))
        mock_aioresponse.get(
            URL("https://api.ui.com/v1/isp-metrics/5m").with_query(
                beginTimestamp="2024-06-30T13:35:00Z", endTimestamp="2024-06-30T16:35:00+01:00"
            ),
            payload={
                "data": [
                    {
                        "metricType": "5m",
                        "hostId": "host-1:console-1",
                        "siteId": "site-1",
                        "periods": [
                            {
                                "metricTime": "2024-06-30T13:35:00Z",
                                "version": "1",
                                "data": {
                                    "wan": {
                                        "avgLatency": 1.5,
                                        "maxLatency": 2,
                                        "packetLoss": 0,
                                        "downtime": 0,
                                        "uptime": 100,
                                        "download_kbps": 0,
                                        "ispName": "ISP",
                                        "ispAsn": "12578",
                                    }
                                },
                            },
                            {"data": {}},
                            None,
                        ],
                    },
                    {"siteId": "site-2", "periods": []},
                    {"siteId": "site-3"},
                ]
            },
        )

        async with client:
            measured, empty, absent = await client.isp_metrics.get_metrics(
                "5m", begin_timestamp=start, end_timestamp=end
            )

        assert (measured.metric_type, measured.host_id, measured.site_id) == (
            "5m",
            "host-1:console-1",
            "site-1",
        )
        assert measured.periods is not None
        first, second, null = measured.periods
        assert first is not None and first.data is not None and first.data.wan is not None
        assert (first.metric_time, first.version) == (start, "1")
        wan = first.data.wan
        assert (wan.avg_latency, wan.max_latency, wan.packet_loss) == (1.5, 2, 0)
        assert (wan.downtime, wan.uptime, wan.download_kbps, wan.upload_kbps) == (0, 100, 0, None)
        assert (wan.isp_name, wan.isp_asn) == ("ISP", "12578")
        assert second is not None and second.data is not None and second.data.wan is None
        assert null is None
        assert empty.periods == []
        assert absent.periods is None

    async def test_typed_isp_metrics_accept_a_bare_list(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        mock_aioresponse.get(
            "https://api.ui.com/v1/isp-metrics/1h?duration=7d",
            payload=[{"siteId": "site-1"}],
        )
        async with client:
            records = await client.isp_metrics.get_metrics("1h", duration="7d")

        assert [record.site_id for record in records] == ["site-1"]

    async def test_typed_isp_metrics_reject_naive_timestamps_before_request(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        with pytest.raises(ValueError, match="Timestamps must include a UTC offset"):
            await client.isp_metrics.get_metrics("5m", begin_timestamp=datetime(2024, 6, 30))

        assert mock_aioresponse.requests == {}

    async def test_typed_isp_site_query_sends_sites_and_parses_partial_success(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        url = URL("https://api.ui.com/v1/isp-metrics/1h/query")
        mock_aioresponse.post(
            url,
            payload={
                "data": {
                    "metrics": [{"siteId": "site-1"}],
                    "status": "partialSuccess",
                    "message": "Some sites were inaccessible",
                }
            },
        )
        query = ISPMetricQuery(
            sites=[
                ISPMetricQuerySite(
                    host_id="host-1:console-1",
                    site_id="site-1",
                    begin_timestamp=datetime(2024, 6, 30, 13, 35, tzinfo=UTC),
                ),
                ISPMetricQuerySite(host_id="host-2", site_id="site-2"),
            ]
        )

        async with client:
            result = await client.isp_metrics.query("1h", query)

        assert mock_aioresponse.requests["POST", url][0].kwargs["json"] == {
            "sites": [
                {
                    "hostId": "host-1:console-1",
                    "siteId": "site-1",
                    "beginTimestamp": "2024-06-30T13:35:00Z",
                },
                {"hostId": "host-2", "siteId": "site-2"},
            ]
        }
        assert result.status == "partialSuccess"
        assert result.message == "Some sites were inaccessible"
        assert [record.site_id for record in result.metrics] == ["site-1"]

    @pytest.mark.parametrize(
        "legacy", [{"hostIds": []}, {"timeRangeStart": 0}, {"timeRangeEnd": 0}]
    )
    async def test_typed_isp_query_rejects_mixed_legacy_and_site_fields(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses, legacy: dict[str, Any]
    ) -> None:
        with pytest.raises(UniFiValidationError, match="cannot combine sites with legacy fields"):
            await client.isp_metrics.query("5m", ISPMetricQuery(sites=[], **legacy))

        assert mock_aioresponse.requests == {}

    def test_typed_isp_query_site_requires_timezone(self) -> None:
        with pytest.raises(ValidationError, match="timezone"):
            ISPMetricQuerySite(
                host_id="host-1", site_id="site-1", end_timestamp=datetime(2024, 6, 30)
            )

    async def test_typed_isp_legacy_query_keeps_its_body_and_bare_response(
        self, client: UniFiSiteManagerClient, mock_aioresponse: aioresponses
    ) -> None:
        url = URL("https://api.ui.com/v1/isp-metrics/5m/query")
        mock_aioresponse.post(url, payload={"metrics": [{"value": 0}]})
        query = ISPMetricQuery(host_ids=["host-1"], time_range_start=0, time_range_end="now")

        async with client:
            result = await client.isp_metrics.query("5m", query)

        assert mock_aioresponse.requests["POST", url][0].kwargs["json"] == {
            "hostIds": ["host-1"],
            "timeRangeStart": 0,
            "timeRangeEnd": "now",
        }
        assert result.metrics[0].value == 0

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
