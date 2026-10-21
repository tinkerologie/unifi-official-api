"""Comprehensive tests to achieve 100% code coverage."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses

from unifi_official_api import ApiKeyAuth, LocalAuth
from unifi_official_api.const import ConnectionType
from unifi_official_api.exceptions import (
    UniFiConnectionError,
    UniFiNotFoundError,
    UniFiResponseError,
    UniFiTimeoutError,
    UniFiUnsupportedError,
)
from unifi_official_api.network import UniFiNetworkClient
from unifi_official_api.network.models import ApplicationInfo
from unifi_official_api.network.models.client import ClientType
from unifi_official_api.network.models.dns import DNSPolicy, DNSPolicyMetadata, DNSRecordType
from unifi_official_api.network.models.firewall import FirewallActionConfig, FirewallRule
from unifi_official_api.network.models.traffic import (
    MetadataOrigin,
    TrafficMatchingList,
    TrafficMatchingType,
    TrafficMetadata,
)
from unifi_official_api.protect import UniFiProtectClient
from unifi_official_api.protect.models.nvr import StorageInfo

# Base URL for mock endpoints
NET_BASE = "https://192.168.1.1/proxy/network/integration/v1"
PROTECT_BASE = "https://192.168.1.1/proxy/protect/integration/v1"
REMOTE_NET = "https://api.ui.com/v1/connector/consoles/test-console/network/integration/v1"


# ===========================================================================
# Base Client Coverage
# ===========================================================================


class TestBaseClientExceptions:
    """Test exception handling in base client _request."""

    async def test_timeout_error(self) -> None:
        """Test TimeoutError is caught and re-raised as UniFiTimeoutError."""
        auth = LocalAuth(api_key="test", verify_ssl=False)
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with aioresponses() as m:
                m.get(
                    re.compile(r".*"),
                    exception=TimeoutError("timeout"),
                )
                with pytest.raises(UniFiTimeoutError):
                    await client._get(f"{NET_BASE}/sites")

    async def test_client_error(self) -> None:
        """Test aiohttp.ClientError is caught and re-raised as UniFiConnectionError."""
        auth = LocalAuth(api_key="test", verify_ssl=False)
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with aioresponses() as m:
                m.get(
                    re.compile(r".*"),
                    exception=aiohttp.ClientError("client error"),
                )
                with pytest.raises(UniFiConnectionError):
                    await client._get(f"{NET_BASE}/sites")


# ===========================================================================
# Network Client Coverage
# ===========================================================================


class TestNetworkClientCoverage:
    """Test Network client methods for full coverage."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        return LocalAuth(api_key="test", verify_ssl=False)

    async def test_local_no_base_url_raises(self) -> None:
        """LOCAL connection without base_url raises ValueError."""
        auth = LocalAuth(api_key="test", verify_ssl=False)
        with pytest.raises(ValueError, match="base_url is required"):
            UniFiNetworkClient(auth=auth, connection_type=ConnectionType.LOCAL)

    async def test_remote_no_console_id_raises(self) -> None:
        """REMOTE connection without console_id raises ValueError lazily."""
        auth = ApiKeyAuth(api_key="test")
        async with UniFiNetworkClient(auth=auth, connection_type=ConnectionType.REMOTE) as client:
            with pytest.raises(ValueError, match="console_id is required"):
                client.build_api_path("/sites")

    async def test_connection_type_property(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            assert client.connection_type == ConnectionType.LOCAL

    async def test_console_id_property(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            assert client.console_id is None

    async def test_build_api_path_remote(self) -> None:
        auth = ApiKeyAuth(api_key="test")
        async with UniFiNetworkClient(
            auth=auth, connection_type=ConnectionType.REMOTE, console_id="c1"
        ) as client:
            path = client.build_api_path("/sites")
            assert "/v1/connector/consoles/c1/" in path

    async def test_get_application_info_with_data_wrapper(self, auth: LocalAuth) -> None:
        """Test get_application_info when response wraps in data key."""
        with aioresponses() as m:
            m.get(
                f"{NET_BASE}/info",
                payload={"data": {"applicationVersion": "10.1.84"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                info = await client.get_application_info()
                assert info.application_version == "10.1.84"


# ===========================================================================
# Network Endpoints - Pagination & Edge Cases
# ===========================================================================


class TestNetworkEndpointPagination:
    """Test pagination, filter, and edge cases for Network endpoints."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        return LocalAuth(api_key="test", verify_ssl=False)

    # --- Sites ---
    async def test_sites_get_all_with_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/sites.*"), payload={"data": [{"id": "s1", "name": "Default"}]})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                sites = await client.sites.get_all(offset=0, limit=10, filter_str="name.eq('x')")
                assert len(sites) == 1

    async def test_sites_get_all_none_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/sites.*"), payload=None)
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                sites = await client.sites.get_all()
                assert sites == []

    async def test_sites_get_all_non_list_data(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/sites.*"), payload={"data": "not a list"})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                sites = await client.sites.get_all()
                assert sites == []

    async def test_sites_get_list_response(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            assert not hasattr(client.sites, "get")

    async def test_sites_get_not_found(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            assert not hasattr(client.sites, "get")

    # --- Devices ---
    async def test_devices_get_all_with_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/devices.*"), payload=[{"id": "d1", "name": "SW"}])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                devices = await client.devices.get_all("s1", offset=0, limit=5, filter_str="f")
                assert len(devices) == 1

    async def test_devices_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/devices/d1"), payload={"data": [{"id": "d1", "name": "SW"}]})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                device = await client.devices.get("s1", "d1")
                assert device.id == "d1"

    async def test_devices_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/devices/.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.devices.get("s1", "missing")

    async def test_devices_pending_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/pending-devices.*"), payload=[{"id": "p1", "name": "P"}])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                pending = await client.devices.get_pending_adoption(
                    offset=0, limit=5, filter_str="f"
                )
                assert len(pending) == 1

    async def test_devices_statistics(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/statistics/latest"), payload={"data": {"cpu": 10}})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                stats = await client.devices.get_statistics("s1", "d1")
                assert stats["cpu"] == 10

    async def test_devices_statistics_empty(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/statistics/latest"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                stats = await client.devices.get_statistics("s1", "d1")
                assert stats == {}

    # --- Clients ---
    async def test_clients_get_all_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/clients.*"),
                payload=[{"id": "c1", "name": "Phone", "macAddress": "aa:bb:cc:dd:ee:ff"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                clients = await client.clients.get_all("s1", offset=0, limit=10, filter_str="f")
                assert len(clients) == 1

    async def test_clients_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/clients/c1"),
                payload={"data": [{"id": "c1", "macAddress": "aa:bb:cc:dd:ee:ff"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                c = await client.clients.get("s1", "c1")
                assert c.id == "c1"

    async def test_clients_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/clients/.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.clients.get("s1", "missing")

    async def test_clients_execute_action(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/cmd/stamgr"), payload={"meta": {"rc": "ok"}})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.clients.execute_action("s1", "c1", "block")
                assert result is True

    async def test_clients_execute_action_invalid(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="Action must be"):
                await client.clients.execute_action("s1", "c1", "invalid")

    # --- Networks ---
    async def test_networks_get_all_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/networks.*"),
                payload=[{"id": "n1", "name": "LAN", "type": "corporate"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                nets = await client.networks.get_all("s1", offset=0, limit=5, filter_str="f")
                assert len(nets) == 1

    async def test_networks_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/networks/n1"),
                payload={"data": [{"id": "n1", "name": "LAN", "type": "corporate"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                n = await client.networks.get("s1", "n1")
                assert n.id == "n1"

    async def test_networks_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/networks/.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.networks.get("s1", "missing")

    async def test_networks_create(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/networks"),
                payload={"data": {"id": "n1", "name": "Test", "type": "corporate"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                n = await client.networks.create("s1", name="Test", vlan_id=100)
                assert n.id == "n1"

    async def test_networks_create_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/networks"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.networks.create("s1", name="Test")

    async def test_networks_update(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.put(
                re.compile(r".*/networks/n1"),
                payload={"data": {"id": "n1", "name": "Updated", "type": "corporate"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                n = await client.networks.update("s1", "n1", name="Updated")
                assert n.name == "Updated"

    async def test_networks_delete(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.delete(re.compile(r".*/networks/n1"), payload={})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.networks.delete("s1", "n1")
                assert result is True

    async def test_networks_get_references(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/references"), payload={"data": {"wifi": ["w1"]}})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                refs = await client.networks.get_references("s1", "n1")
                assert refs["wifi"] == ["w1"]

    async def test_networks_get_references_empty(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/references"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                refs = await client.networks.get_references("s1", "n1")
                assert refs == {}

    # --- WiFi ---
    async def test_wifi_get_all_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/wifi/broadcasts.*"),
                payload=[{"id": "w1", "name": "MyWifi", "ssid": "MySSID"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                wifis = await client.wifi.get_all("s1", offset=0, limit=5, filter_str="f")
                assert len(wifis) == 1

    async def test_wifi_get(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/wifi/broadcasts/w1"),
                payload={"data": {"id": "w1", "name": "W", "ssid": "S"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                w = await client.wifi.get("s1", "w1")
                assert w.id == "w1"

    async def test_wifi_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/wifi/broadcasts/w1"),
                payload={"data": [{"id": "w1", "name": "W", "ssid": "S"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                w = await client.wifi.get("s1", "w1")
                assert w.id == "w1"

    async def test_wifi_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/wifi/broadcasts/.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.wifi.get("s1", "missing")

    async def test_wifi_create(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/wifi/broadcasts"),
                payload={"data": {"id": "w1", "name": "New", "ssid": "New"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                w = await client.wifi.create(
                    "s1",
                    name="New",
                    ssid="New",
                    passphrase="secret",
                    network_id="n1",
                )
                assert w.id == "w1"

    async def test_wifi_create_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/wifi/broadcasts"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.wifi.create("s1", name="X", ssid="X", passphrase="secret")

    async def test_wifi_update(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/wifi/broadcasts/w1"),
                payload={"data": {"id": "w1", "name": "Old", "ssid": "O"}},
            )
            m.put(
                re.compile(r".*/wifi/broadcasts/w1"),
                payload={"data": {"id": "w1", "name": "Updated", "ssid": "U"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                w = await client.wifi.update("s1", "w1", name="Updated")
                assert w.name == "Updated"

    async def test_wifi_update_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/wifi/broadcasts/.*"), payload={"data": []})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiNotFoundError):
                    await client.wifi.update("s1", "w1", name="X")

    async def test_wifi_delete(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.delete(re.compile(r".*/wifi/broadcasts/w1"), payload={})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.wifi.delete("s1", "w1")
                assert result is True

    # --- Resources ---
    async def test_resources_wan_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/wans.*"),
                payload=[{"id": "w1", "name": "WAN"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                wans = await client.resources.get_wan_interfaces(
                    "s1", offset=0, limit=5, filter_str="f"
                )
                assert len(wans) == 1

    async def test_resources_vpn_tunnels_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/vpn/site-to-site-tunnels.*"), payload=[{"id": "t1", "name": "VPN"}]
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                tunnels = await client.resources.get_vpn_tunnels(
                    "s1", offset=0, limit=5, filter_str="f"
                )
                assert len(tunnels) == 1

    async def test_resources_vpn_servers_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/vpn/servers.*"), payload=[{"id": "vs1", "name": "VPN Server"}])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                servers = await client.resources.get_vpn_servers(
                    "s1", offset=0, limit=5, filter_str="f"
                )
                assert len(servers) == 1

    async def test_resources_radius_profiles_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/radius/profiles.*"), payload=[{"id": "r1", "name": "RADIUS"}])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                profiles = await client.resources.get_radius_profiles(
                    "s1", offset=0, limit=5, filter_str="f"
                )
                assert len(profiles) == 1

    async def test_resources_device_tags_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/device-tags.*"), payload=[{"id": "t1", "name": "Tag"}])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                tags = await client.resources.get_device_tags(
                    "s1", offset=0, limit=5, filter_str="f"
                )
                assert len(tags) == 1

    # --- Firewall ---
    async def test_firewall_zones_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/firewall/zones.*"),
                payload=[{"id": "z1", "name": "Internal"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                zones = await client.firewall.list_zones("s1", offset=0, limit=5, filter_str="f")
                assert len(zones) == 1

    async def test_firewall_get_zone_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/firewall/zones/z1"),
                payload={"data": [{"id": "z1", "name": "Z"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                z = await client.firewall.get_zone("s1", "z1")
                assert z.id == "z1"

    async def test_firewall_get_zone_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/firewall/zones/.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.firewall.get_zone("s1", "missing")

    async def test_firewall_create_zone(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/firewall/zones"),
                payload={"data": {"id": "z1", "name": "Custom"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                z = await client.firewall.create_zone("s1", name="Custom")
                assert z.id == "z1"

    async def test_firewall_create_zone_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/firewall/zones"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.firewall.create_zone("s1", name="X")

    async def test_firewall_update_zone(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.put(
                re.compile(r".*/firewall/zones/z1"),
                payload={"data": {"id": "z1", "name": "Updated"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                z = await client.firewall.update_zone("s1", "z1", name="Updated")
                assert z.name == "Updated"

    async def test_firewall_delete_zone(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.delete(re.compile(r".*/firewall/zones/z1"), payload={})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.firewall.delete_zone("s1", "z1")
                assert result is True

    async def test_firewall_rules_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/firewall/policies.*"),
                payload=[{"id": "r1", "name": "Block", "action": "drop"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                rules = await client.firewall.list_rules("s1", offset=0, limit=5, filter_str="f")
                assert len(rules) == 1

    async def test_firewall_get_rule_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/firewall/policies/r1"),
                payload={"data": [{"id": "r1", "name": "Rule", "action": "drop"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                r = await client.firewall.get_rule("s1", "r1")
                assert r.id == "r1"

    async def test_firewall_get_rule_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/firewall/policies/.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.firewall.get_rule("s1", "missing")

    async def test_firewall_create_rule(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/firewall/policies"),
                payload={"data": {"id": "r1", "name": "New", "action": "accept"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                r = await client.firewall.create_rule(
                    "s1",
                    name="New",
                    action="accept",
                    source_zone_id="z1",
                    destination_zone_id="z2",
                )
                assert r.id == "r1"

    async def test_firewall_create_rule_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/firewall/policies"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(ValueError, match="zoneId"):
                    await client.firewall.create_rule("s1", name="X")

    async def test_firewall_update_rule(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/firewall/policies/r1"),
                payload={"data": {"id": "r1", "name": "Old", "action": "drop"}},
            )
            m.put(
                re.compile(r".*/firewall/policies/r1"),
                payload={"data": {"id": "r1", "name": "Updated", "action": "drop"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                r = await client.firewall.update_rule("s1", "r1", name="Updated")
                assert r.name == "Updated"

    async def test_firewall_update_rule_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/firewall/policies/.*"), payload={"data": []})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiNotFoundError):
                    await client.firewall.update_rule("s1", "r1", name="X")

    async def test_firewall_delete_rule(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.delete(re.compile(r".*/firewall/policies/r1"), payload={})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.firewall.delete_rule("s1", "r1")
                assert result is True

    async def test_firewall_patch_rule(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.patch(
                re.compile(r".*/firewall/policies/r1"),
                payload={"data": {"id": "r1", "name": "Patched", "action": "drop"}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                r = await client.firewall.patch_rule("s1", "r1", logging_enabled=False)
                assert r.id == "r1"

    async def test_firewall_patch_rule_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.patch(
                re.compile(r".*/firewall/policies/r1"),
                payload={"data": [{"id": "r1", "name": "P", "action": "drop"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                r = await client.firewall.patch_rule("s1", "r1", logging_enabled=False)
                assert r.id == "r1"

    async def test_firewall_get_policy_ordering(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/firewall/policies/ordering.*"),
                payload={
                    "data": {
                        "orderedFirewallPolicyIds": {
                            "beforeSystemDefined": ["p1"],
                            "afterSystemDefined": [],
                        }
                    }
                },
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                o = await client.firewall.get_policy_ordering(
                    "s1",
                    source_firewall_zone_id="z1",
                    destination_firewall_zone_id="z2",
                )
                assert o.ordered_firewall_policy_ids.before_system_defined == ["p1"]

    async def test_firewall_get_policy_ordering_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/firewall/policies/ordering.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.firewall.get_policy_ordering(
                        "s1",
                        source_firewall_zone_id="z1",
                        destination_firewall_zone_id="z2",
                    )

    async def test_firewall_update_policy_ordering(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.put(
                re.compile(r".*/firewall/policies/ordering.*"),
                payload={
                    "data": {
                        "orderedFirewallPolicyIds": {
                            "beforeSystemDefined": ["p2", "p1"],
                            "afterSystemDefined": [],
                        }
                    }
                },
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                o = await client.firewall.update_policy_ordering(
                    "s1",
                    source_firewall_zone_id="z1",
                    destination_firewall_zone_id="z2",
                    ordered_firewall_policy_ids={
                        "beforeSystemDefined": ["p2", "p1"],
                        "afterSystemDefined": [],
                    },
                )
                assert len(o.ordered_firewall_policy_ids.before_system_defined) == 2

    # --- ACL ---
    async def test_acl_get_all_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/acl-rules.*"),
                payload=[
                    {"id": "a1", "name": "Rule", "type": "IPV4", "action": "BLOCK", "index": 0}
                ],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                rules = await client.acl.get_all("s1", offset=0, limit=5, filter_str="f")
                assert len(rules) == 1

    async def test_acl_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/acl-rules/a1"),
                payload={
                    "data": [
                        {"id": "a1", "name": "R", "type": "IPV4", "action": "BLOCK", "index": 0}
                    ]
                },
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                r = await client.acl.get("s1", "a1")
                assert r.id == "a1"

    async def test_acl_ordering(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/acl-rules/ordering"),
                payload={"data": {"orderedAclRuleIds": ["a1", "a2"]}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                o = await client.acl.get_ordering("s1")
                assert len(o.ordered_acl_rule_ids) == 2

    async def test_acl_update_ordering(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.put(
                re.compile(r".*/acl-rules/ordering"),
                payload={"data": {"orderedAclRuleIds": ["a2", "a1"]}},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                o = await client.acl.update_ordering("s1", ordered_rule_ids=["a2", "a1"])
                assert o.ordered_acl_rule_ids == ["a2", "a1"]

    # --- DNS ---
    async def test_dns_get_all_filter(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/dns/policies.*"),
                payload=[{"id": "d1", "type": "A_RECORD", "domain": "test.local"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                policies = await client.dns.get_all("s1", filter_query="type.eq('A_RECORD')")
                assert len(policies) == 1

    async def test_dns_get_none_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/dns/policies.*"), payload=None)
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                policies = await client.dns.get_all("s1")
                assert policies == []

    async def test_dns_get_non_list(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/dns/policies.*"), payload={"data": "not a list"})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                policies = await client.dns.get_all("s1")
                assert policies == []

    async def test_dns_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/dns/policies/d1"),
                payload={"data": [{"id": "d1", "type": "A_RECORD", "domain": "test.local"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                p = await client.dns.get("s1", "d1")
                assert p.id == "d1"

    async def test_dns_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/dns/policies/.*"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.dns.get("s1", "missing")

    async def test_dns_create_with_enum(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/dns/policies"),
                payload={
                    "data": {
                        "id": "d1",
                        "type": "A_RECORD",
                        "domain": "test.local",
                        "ipv4Address": "1.2.3.4",
                    }
                },
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                p = await client.dns.create(
                    "s1",
                    record_type=DNSRecordType.A_RECORD,
                    domain="test.local",
                    ipv4_address="1.2.3.4",
                    ttl_seconds=300,
                )
                assert p.id == "d1"

    async def test_dns_create_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/dns/policies"), payload=[])
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.dns.create("s1", record_type="A_RECORD")

    async def test_dns_update_all_fields(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.put(
                re.compile(r".*/dns/policies/d1"),
                payload={
                    "data": {"id": "d1", "type": "A_RECORD", "enabled": False, "domain": "u.l"}
                },
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                p = await client.dns.update(
                    "s1",
                    "d1",
                    record_type=DNSRecordType.A_RECORD,
                    enabled=False,
                    domain="u.l",
                    ipv4_address="5.6.7.8",
                    ttl_seconds=600,
                )
                assert p.enabled is False

    async def test_dns_delete(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.delete(re.compile(r".*/dns/policies/d1"), payload={})
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.dns.delete("s1", "d1")
                assert result is True

    # --- Traffic ---
    async def test_traffic_pagination(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/traffic-matching-lists.*"),
                payload=[
                    {
                        "id": "t1",
                        "name": "List",
                        "type": "IP_ADDRESS",
                        "entries": [],
                    }
                ],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                lists = await client.traffic.get_all_lists("s1", offset=0, limit=5, filter_str="f")
                assert len(lists) == 1

    async def test_traffic_get_list_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/traffic-matching-lists/t1"),
                payload={"data": [{"id": "t1", "name": "L", "type": "IP_ADDRESS", "entries": []}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                t = await client.traffic.get_list("s1", "t1")
                assert t.id == "t1"

    async def test_traffic_dpi_categories(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/dpi/categories"),
                payload=[{"id": 1, "name": "Social"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                cats = await client.traffic.get_dpi_categories()
                assert len(cats) == 1

    async def test_traffic_dpi_applications(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/dpi/applications"),
                payload=[{"id": 1, "name": "Facebook"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                apps = await client.traffic.get_dpi_applications()
                assert len(apps) == 1

    async def test_traffic_countries(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/countries"),
                payload=[{"code": "US", "name": "United States"}],
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                countries = await client.traffic.get_countries()
                assert len(countries) == 1


# ===========================================================================
# Network Model Coverage
# ===========================================================================


class TestNetworkModelCoverage:
    """Test model edge cases for coverage."""

    def test_client_type_case_insensitive(self) -> None:
        """ClientType._missing_ handles lowercase."""
        assert ClientType("wired") == ClientType.WIRED
        assert ClientType("wireless") == ClientType.WIRELESS

    def test_client_type_missing_non_string(self) -> None:
        """ClientType._missing_ returns None for non-string."""
        assert ClientType._missing_(123) is None

    def test_dns_policy_is_user_defined(self) -> None:
        p = DNSPolicy(
            id="d1",
            type=DNSRecordType.A_RECORD,
            metadata=DNSPolicyMetadata(origin="USER_DEFINED"),
        )
        assert p.is_user_defined is True

    def test_dns_policy_is_not_user_defined(self) -> None:
        p = DNSPolicy(id="d1", type=DNSRecordType.A_RECORD)
        assert p.is_user_defined is False

    def test_dns_policy_system_defined(self) -> None:
        p = DNSPolicy(
            id="d1",
            type=DNSRecordType.A_RECORD,
            metadata=DNSPolicyMetadata(origin="SYSTEM_DEFINED"),
        )
        assert p.is_user_defined is False

    def test_firewall_rule_action_type_string(self) -> None:
        r = FirewallRule(id="r1", name="Test", action="drop")
        assert r.action_type == "drop"

    def test_firewall_rule_action_type_config(self) -> None:
        r = FirewallRule(id="r1", name="Test", action=FirewallActionConfig(type="ALLOW"))
        assert r.action_type == "ALLOW"

    def test_traffic_matching_list_is_user_defined_no_metadata(self) -> None:
        t = TrafficMatchingList(type=TrafficMatchingType.IP_ADDRESS, name="Test")
        assert t.is_user_defined is True

    def test_traffic_matching_list_is_system_defined(self) -> None:
        t = TrafficMatchingList(
            type=TrafficMatchingType.IP_ADDRESS,
            name="Test",
            metadata=TrafficMetadata(origin=MetadataOrigin.SYSTEM_DEFINED),
        )
        assert t.is_user_defined is False

    def test_application_info_model(self) -> None:
        info = ApplicationInfo(applicationVersion="10.1.84")
        assert info.application_version == "10.1.84"


# ===========================================================================
# Protect Client Coverage
# ===========================================================================


class TestProtectClientCoverage:
    """Test Protect client methods for full coverage."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        return LocalAuth(api_key="test", verify_ssl=False)

    async def test_local_no_base_url_raises(self) -> None:
        auth = LocalAuth(api_key="test", verify_ssl=False)
        with pytest.raises(ValueError, match="base_url is required"):
            UniFiProtectClient(auth=auth, connection_type=ConnectionType.LOCAL)

    async def test_remote_no_console_id_raises(self) -> None:
        auth = ApiKeyAuth(api_key="test")
        with pytest.raises(ValueError, match="console_id is required"):
            UniFiProtectClient(auth=auth, connection_type=ConnectionType.REMOTE)

    async def test_build_api_path_remote(self) -> None:
        auth = ApiKeyAuth(api_key="test")
        async with UniFiProtectClient(
            auth=auth, connection_type=ConnectionType.REMOTE, console_id="c1"
        ) as client:
            path = client.build_api_path("/cameras")
            assert "/v1/connector/consoles/c1/" in path
            assert "/cameras" in path
            assert "/sites/" not in path

    async def test_build_api_path_remote_site_id_ignored(self) -> None:
        """Protect REMOTE build_api_path ignores site_id."""
        auth = ApiKeyAuth(api_key="test")
        async with UniFiProtectClient(
            auth=auth, connection_type=ConnectionType.REMOTE, console_id="c1"
        ) as client:
            path = client.build_api_path("/cameras", site_id="s1")
            assert "/v1/connector/consoles/c1/" in path
            assert "/cameras" in path
            assert "/sites/" not in path

    async def test_build_api_path_no_leading_slash(self) -> None:
        auth = LocalAuth(api_key="test", verify_ssl=False)
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            path = client.build_api_path("cameras")
            assert "/cameras" in path

    async def test_validate_connection(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/cameras"), payload={"data": []})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.validate_connection()
                assert result is True

    async def test_get_host_id(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/nvrs"),
                payload={"data": {"id": "nvr-123", "name": "NVR"}},
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                host_id = await client.get_host_id()
                assert host_id == "nvr-123"

    async def test_get_binary(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/cameras/c1/snapshot"),
                body=b"\x89PNG",
                content_type="image/png",
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                data = await client._get_binary(f"{PROTECT_BASE}/cameras/c1/snapshot")
                assert data == b"\x89PNG"

    async def test_get_binary_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/cameras/c1/snapshot"),
                status=404,
                body=b"Not Found",
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiNotFoundError):
                    await client._get_binary(f"{PROTECT_BASE}/cameras/c1/snapshot")

    async def test_get_binary_timeout(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*"), exception=TimeoutError())
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiTimeoutError):
                    await client._get_binary(f"{PROTECT_BASE}/cameras/c1/snapshot")

    async def test_get_binary_connection_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*"), exception=aiohttp.ClientError("err"))
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiConnectionError):
                    await client._get_binary(f"{PROTECT_BASE}/cameras/c1/snapshot")


# ===========================================================================
# Protect Endpoints Coverage
# ===========================================================================


class TestProtectEndpointsCoverage:
    """Test Protect endpoint methods for full coverage."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        return LocalAuth(api_key="test", verify_ssl=False)

    # Minimal camera data helper
    def _cam(self, **overrides: object) -> dict:
        d = {"id": "c1", "mac": "aa:bb:cc:dd:ee:ff", "name": "Cam"}
        d.update(overrides)
        return d

    def _light(self, **overrides: object) -> dict:
        d = {"id": "l1", "mac": "11:22:33:44:55:66", "name": "Light"}
        d.update(overrides)
        return d

    def _chime(self, **overrides: object) -> dict:
        d = {"id": "ch1", "mac": "22:33:44:55:66:77", "name": "Chime"}
        d.update(overrides)
        return d

    def _sensor(self, **overrides: object) -> dict:
        d = {"id": "s1", "mac": "33:44:55:66:77:88", "name": "Sensor"}
        d.update(overrides)
        return d

    def _liveview(self, **overrides: object) -> dict:
        d = {"id": "lv1", "name": "View"}
        d.update(overrides)
        return d

    def _nvr(self, **overrides: object) -> dict:
        d = {"id": "nvr1", "name": "NVR"}
        d.update(overrides)
        return d

    def _event(self, **overrides: object) -> dict:
        d = {"id": "e1", "type": "motion", "camera": "c1", "start": 1000, "end": 2000}
        d.update(overrides)
        return d

    # --- Cameras ---
    async def test_cameras_get_all_none(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/cameras"), payload=None)
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                cams = await client.cameras.get_all()
                assert cams == []

    async def test_cameras_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/cameras/c1"), payload={"data": [self._cam()]})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                c = await client.cameras.get("c1")
                assert c.id == "c1"

    async def test_cameras_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/cameras/.*"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.cameras.get("missing")

    async def test_cameras_update(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.patch(re.compile(r".*/cameras/c1"), payload={"data": self._cam()})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                c = await client.cameras.update("c1", name="New")
                assert c.id == "c1"

    async def test_cameras_set_mic_volume_invalid(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="Volume"):
                await client.cameras.set_microphone_volume("c1", 150)

    async def test_cameras_set_speaker_volume_invalid(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="Volume"):
                await client.cameras.set_speaker_volume("c1", -1)

    async def test_cameras_ptz_goto_preset(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/cameras/c1/ptz/goto/p1"), payload={})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.cameras.ptz_goto_preset("c1", "p1")
                assert result is True

    async def test_cameras_ptz_patrol_start(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/cameras/c1/ptz/patrol/start/2"), payload={})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.cameras.ptz_patrol_start("c1", 2)
                assert result is True

    async def test_cameras_ptz_patrol_start_invalid(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="Slot"):
                await client.cameras.ptz_patrol_start("c1", 10)

    async def test_cameras_ptz_patrol_stop(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/cameras/c1/ptz/patrol/stop"), payload={})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.cameras.ptz_patrol_stop("c1")
                assert result is True

    async def test_cameras_create_rtsps_stream(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/cameras/c1/rtsps-stream"),
                payload={"data": {"high": "rtsps://192.168.1.1:7441/abc"}},
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                stream = await client.cameras.create_rtsps_stream("c1")
                assert "rtsps" in stream.high

    async def test_cameras_create_rtsps_stream_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/cameras/c1/rtsps-stream"), payload=[])
            m.get(re.compile(r".*/cameras/c1/rtsps-stream"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiNotFoundError):
                    await client.cameras.create_rtsps_stream("c1")

    async def test_cameras_get_rtsps_stream(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/cameras/c1/rtsps-stream"),
                payload={"data": {"high": "rtsps://url"}},
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                stream = await client.cameras.get_rtsps_stream("c1")
                assert stream.high is not None

    async def test_cameras_get_rtsps_stream_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/cameras/c1/rtsps-stream"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.cameras.get_rtsps_stream("c1")

    async def test_cameras_delete_rtsps_stream(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.delete(re.compile(r".*/cameras/c1/rtsps-stream"), payload={})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.cameras.delete_rtsps_stream("c1")
                assert result is True

    async def test_cameras_create_talkback_session(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/cameras/c1/talkback-session"),
                payload={
                    "data": {
                        "url": "wss://url",
                        "codec": "aac",
                        "samplingRate": 8000,
                        "bitsPerSample": 16,
                    }
                },
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                session = await client.cameras.create_talkback_session("c1")
                assert session.url is not None

    async def test_cameras_create_talkback_session_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/cameras/c1/talkback-session"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.cameras.create_talkback_session("c1")

    async def test_cameras_disable_mic_permanently(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/cameras/c1/disable-mic-permanently"),
                payload={"data": self._cam()},
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                c = await client.cameras.disable_mic_permanently("c1")
                assert c.id == "c1"

    async def test_cameras_set_hdr_mode_invalid(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="HDR"):
                await client.cameras.set_hdr_mode("c1", "invalid")

    # --- Lights ---
    async def test_lights_get_all_none(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/lights"), payload=None)
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                lights = await client.lights.get_all()
                assert lights == []

    async def test_lights_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/lights/l1"), payload={"data": [self._light()]})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                light = await client.lights.get("l1")
                assert light.id == "l1"

    async def test_lights_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/lights/.*"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.lights.get("missing")

    async def test_lights_update(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.patch(re.compile(r".*/lights/l1"), payload={"data": self._light()})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                light = await client.lights.update("l1", brightness=50)
                assert light.id == "l1"

    async def test_lights_set_brightness_invalid(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="between 1 and 6"):
                await client.lights.set_brightness("l1", 150)

    # --- Chimes ---
    async def test_chimes_get_all_none(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/chimes"), payload=None)
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                chimes = await client.chimes.get_all()
                assert chimes == []

    async def test_chimes_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/chimes/ch1"), payload={"data": [self._chime()]})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                ch = await client.chimes.get("ch1")
                assert ch.id == "ch1"

    async def test_chimes_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/chimes/.*"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.chimes.get("missing")

    async def test_chimes_update(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.patch(re.compile(r".*/chimes/ch1"), payload={"data": self._chime()})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                ch = await client.chimes.update("ch1", volume=50)
                assert ch.id == "ch1"

    async def test_chimes_set_volume_invalid(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="Volume"):
                await client.chimes.set_volume("ch1", 150)

    async def test_chimes_play(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(UniFiUnsupportedError):
                await client.chimes.play("ch1")

    # --- Sensors ---
    async def test_sensors_get_all_none(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/sensors"), payload=None)
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                sensors = await client.sensors.get_all()
                assert sensors == []

    async def test_sensors_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/sensors/s1"), payload={"data": [self._sensor()]})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                s = await client.sensors.get("s1")
                assert s.id == "s1"

    async def test_sensors_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/sensors/.*"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.sensors.get("missing")

    async def test_sensors_update(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.patch(re.compile(r".*/sensors/s1"), payload={"data": self._sensor()})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                s = await client.sensors.update("s1", name="New")
                assert s.id == "s1"

    async def test_sensors_set_motion_sensitivity_invalid(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="Sensitivity"):
                await client.sensors.set_motion_sensitivity("s1", 200)

    # --- Liveviews ---
    async def test_liveviews_get_all_none(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/liveviews"), payload=None)
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                views = await client.liveviews.get_all()
                assert views == []

    async def test_liveviews_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/liveviews/lv1"), payload={"data": [self._liveview()]})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                lv = await client.liveviews.get("lv1")
                assert lv.id == "lv1"

    async def test_liveviews_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/liveviews/.*"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.liveviews.get("missing")

    async def test_liveviews_create(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/liveviews"),
                payload={"data": self._liveview()},
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                lv = await client.liveviews.create(name="New", slots=[{"cameras": ["c1"]}])
                assert lv.id == "lv1"

    async def test_liveviews_create_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/liveviews"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.liveviews.create(name="X")

    async def test_liveviews_update(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.patch(re.compile(r".*/liveviews/lv1"), payload={"data": self._liveview()})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                lv = await client.liveviews.update("lv1", name="Updated")
                assert lv.id == "lv1"

    # --- NVR ---
    async def test_nvr_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/nvrs"), payload={"data": [self._nvr()]})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                nvr = await client.nvr.get()
                assert nvr.id == "nvr1"

    async def test_nvr_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/nvrs"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiNotFoundError):
                    await client.nvr.get()

    # --- Application ---
    async def test_application_get_info_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/meta/info"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.application.get_info()

    async def test_application_get_files_none(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/files/.*"), payload=None)
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                files = await client.application.get_files()
                assert files == []

    async def test_application_get_files_non_list(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/files/.*"), payload={"data": "not a list"})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                files = await client.application.get_files()
                assert files == []

    async def test_application_upload_file(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(
                re.compile(r".*/files/.*"),
                payload={
                    "data": {
                        "name": "f1",
                        "type": "animations",
                        "originalName": "test.gif",
                        "path": "/files/f1",
                    }
                },
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                f = await client.application.upload_file(b"data", "test.gif")
                assert f.name == "f1"

    async def test_application_upload_file_error(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.post(re.compile(r".*/files/.*"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.application.upload_file(b"data", "test.gif")

    async def test_application_trigger_alarm_empty_id(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with pytest.raises(ValueError, match="Trigger ID"):
                await client.application.trigger_alarm_webhook("")

    # --- Viewers ---
    async def test_viewers_get_list_response(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(
                re.compile(r".*/viewers/v1"),
                payload={
                    "data": [
                        {"id": "v1", "modelKey": "viewer", "state": "CONNECTED", "mac": "aa:bb"}
                    ]
                },
            )
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                v = await client.viewers.get("v1")
                assert v.id == "v1"

    async def test_viewers_get_not_found(self, auth: LocalAuth) -> None:
        with aioresponses() as m:
            m.get(re.compile(r".*/viewers/.*"), payload=[])
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.viewers.get("missing")


# ===========================================================================
# Protect Model Coverage
# ===========================================================================


class TestProtectModelCoverage:
    """Test Protect model edge cases."""

    def test_storage_info_usage_percent_zero(self) -> None:
        s = StorageInfo(totalSize=0, usedSize=0, availableSize=0)
        assert s.usage_percent == 0.0

    def test_storage_info_usage_percent(self) -> None:
        s = StorageInfo(totalSize=1000, usedSize=500, availableSize=500)
        assert s.usage_percent == 50.0

    def test_nvr_display_name_fallbacks(self) -> None:
        from unifi_official_api.protect.models.nvr import NVR

        nvr1 = NVR(id="n1", name="My NVR")
        assert nvr1.display_name == "My NVR"

        nvr2 = NVR(id="n2", mac="aa:bb:cc")
        assert nvr2.display_name == "aa:bb:cc"

        nvr3 = NVR(id="n3")
        assert nvr3.display_name == "n3"

    def test_chime_display_name(self) -> None:
        from unifi_official_api.protect.models.chime import Chime

        c1 = Chime(id="c1", mac="aa:bb:cc", name="My Chime")
        assert c1.display_name == "My Chime"

        c2 = Chime(id="c2", mac="aa:bb:cc")
        assert c2.display_name == "aa:bb:cc"

    def test_light_display_name(self) -> None:
        from unifi_official_api.protect.models.light import Light

        l1 = Light(id="l1", mac="aa:bb:cc", name="My Light")
        assert l1.display_name == "My Light"

        l2 = Light(id="l2", mac="aa:bb:cc")
        assert l2.display_name == "aa:bb:cc"

    def test_sensor_display_name(self) -> None:
        from unifi_official_api.protect.models.sensor import Sensor

        s1 = Sensor(id="s1", mac="aa:bb:cc", name="My Sensor")
        assert s1.display_name == "My Sensor"

        s2 = Sensor(id="s2", mac="aa:bb:cc")
        assert s2.display_name == "aa:bb:cc"

    def test_camera_construct_rtsp_url(self) -> None:
        from unifi_official_api.protect.models.camera import Camera

        cam = Camera(id="cam1", mac="aa:bb:cc", name="Cam")
        url = cam.construct_rtsp_url("192.168.1.1")
        assert "rtsps://" in url
        assert "cam1" in url

        url_no_srtp = cam.construct_rtsp_url("192.168.1.1", use_srtp=False)
        assert url_no_srtp.startswith("rtsp://")
        assert "enableSrtp" not in url_no_srtp


# ===========================================================================
# Additional Coverage - None responses, non-list data, error branches
# ===========================================================================


class TestNoneAndNonListResponses:
    """Test None response and non-list data handling across all endpoints."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        return LocalAuth(api_key="test", verify_ssl=False)

    # --- Base client: custom headers ---
    async def test_request_with_custom_headers(self, auth: LocalAuth) -> None:
        """Cover base.py line 167: request_headers.update(headers)."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with aioresponses() as m:
                m.get(re.compile(r".*"), payload=[{"id": "s1", "name": "Default"}])
                # _request with headers; triggers header update branch
                result = await client._request(
                    "GET", f"{NET_BASE}/sites", headers={"X-Custom": "test"}
                )
                assert result is not None

    # --- Base client: ClientConnectorError ---
    async def test_client_connector_error(self, auth: LocalAuth) -> None:
        """Cover base.py line 186: ClientConnectorError handler."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with aioresponses() as m:
                m.get(
                    re.compile(r".*"),
                    exception=aiohttp.ClientConnectorError(
                        connection_key=MagicMock(), os_error=OSError("conn refused")
                    ),
                )
                with pytest.raises(UniFiConnectionError, match="Failed to connect"):
                    await client._get(f"{NET_BASE}/sites")

    # --- Network client: path without leading / ---
    async def test_build_api_path_no_leading_slash(self, auth: LocalAuth) -> None:
        """Cover network/client.py line 159: endpoint without leading /."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            path = client.build_api_path("sites")
            assert path.startswith("/proxy/network/integration/v1/sites")

    # --- Network client: get_application_info error ---
    async def test_get_application_info_non_dict_response(self, auth: LocalAuth) -> None:
        """Cover network/client.py line 258: ValueError when response is not dict."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with aioresponses() as m:
                m.get(re.compile(r".*/info"), payload=[])
                with pytest.raises(UniFiNotFoundError):
                    await client.get_application_info()

    # --- Sites: get with list data ---
    async def test_sites_get_list_data_branch(self, auth: LocalAuth) -> None:
        """Cover sites.py lines 76-77: data is list in get_all response."""
        with aioresponses() as m:
            m.get(
                re.compile(r".*/sites"),
                payload={"data": [{"id": "s1", "name": "Default"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                sites = await client.sites.get_all()
                assert len(sites) == 1
                assert sites[0].id == "s1"

    # --- Devices: None response ---
    async def test_devices_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover devices.py line 55: response is None."""
        with aioresponses() as m:
            m.get(re.compile(r".*/devices.*"), payload="null")
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                    devices = await client.devices.get_all("s1")
                    assert devices == []

    # --- Devices: non-list data ---
    async def test_devices_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover devices.py line 60: data is not a list."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": "x"},
            ):
                devices = await client.devices.get_all("s1")
                assert devices == []

    # --- Devices: get with list data ---
    async def test_devices_get_list_data_branch(self, auth: LocalAuth) -> None:
        """Cover devices.py branch 79-81: data is list in get response."""
        with aioresponses() as m:
            m.get(
                re.compile(r".*/devices/d1"),
                payload={"data": [{"id": "d1", "name": "SW"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                device = await client.devices.get("s1", "d1")
                assert device.id == "d1"

    # --- Devices: pending devices None & non-list ---
    async def test_devices_pending_none_response(self, auth: LocalAuth) -> None:
        """Cover devices.py line 173: pending devices response is None."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                devices = await client.devices.get_pending_adoption()
                assert devices == []

    async def test_devices_pending_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover devices.py line 178: pending devices data is not a list."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                devices = await client.devices.get_pending_adoption()
                assert devices == []

    # --- Clients: None response ---
    async def test_clients_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover clients.py line 55."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                clients = await client.clients.get_all("s1")
                assert clients == []

    async def test_clients_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover clients.py line 60."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                clients = await client.clients.get_all("s1")
                assert clients == []

    async def test_clients_get_list_data_branch(self, auth: LocalAuth) -> None:
        """Cover clients.py branch 79-81."""
        with aioresponses() as m:
            m.get(
                re.compile(r".*/clients/c1"),
                payload={"data": [{"id": "c1", "mac": "aa:bb:cc:dd:ee:ff"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                c = await client.clients.get("s1", "c1")
                assert c.id == "c1"

    # --- Networks: None and non-list ---
    async def test_networks_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover networks.py line 55."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                nets = await client.networks.get_all("s1")
                assert nets == []

    async def test_networks_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover networks.py line 60."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                nets = await client.networks.get_all("s1")
                assert nets == []

    # --- WiFi: None and non-list ---
    async def test_wifi_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover wifi.py line 55."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                wifis = await client.wifi.get_all("s1")
                assert wifis == []

    async def test_wifi_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover wifi.py line 60."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                wifis = await client.wifi.get_all("s1")
                assert wifis == []

    # --- Firewall: zones None and non-list ---
    async def test_firewall_zones_none_response(self, auth: LocalAuth) -> None:
        """Cover firewall.py line 57."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                zones = await client.firewall.list_zones("s1")
                assert zones == []

    async def test_firewall_zones_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover firewall.py line 62."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                zones = await client.firewall.list_zones("s1")
                assert zones == []

    # --- Firewall: rules None and non-list ---
    async def test_firewall_rules_none_response(self, auth: LocalAuth) -> None:
        """Cover firewall.py line 184."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                rules = await client.firewall.list_rules("s1")
                assert rules == []

    async def test_firewall_rules_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover firewall.py line 189."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                rules = await client.firewall.list_rules("s1")
                assert rules == []

    # --- ACL: None response ---
    async def test_acl_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover acl.py line 52."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                rules = await client.acl.get_all("s1")
                assert rules == []

    # --- ACL: get with dict data ---
    async def test_acl_get_dict_data_branch(self, auth: LocalAuth) -> None:
        """Cover acl.py branch 72->78: data is dict in get response."""
        with aioresponses() as m:
            m.get(
                re.compile(r".*/acl-rules/a1"),
                payload={
                    "data": {"id": "a1", "name": "R", "type": "IPV4", "action": "BLOCK", "index": 0}
                },
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                r = await client.acl.get("s1", "a1")
                assert r.id == "a1"

    # --- ACL: ordering error ---
    async def test_acl_ordering_error(self, auth: LocalAuth) -> None:
        """Cover acl.py line 187: ordering returns non-dict."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiNotFoundError):
                    await client.acl.get_ordering("s1")

    # --- Vouchers: None and non-list ---
    async def test_vouchers_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover vouchers.py line 52."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                vouchers = await client.vouchers.get_all("s1")
                assert vouchers == []

    async def test_vouchers_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover vouchers.py line 57."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                vouchers = await client.vouchers.get_all("s1")
                assert vouchers == []

    async def test_vouchers_get_list_data_branch(self, auth: LocalAuth) -> None:
        """Cover vouchers.py line 77: data is list in get response."""
        with aioresponses() as m:
            m.get(
                re.compile(r".*/vouchers/v1"),
                payload={"data": [{"id": "v1", "code": "ABC123"}]},
            )
            async with UniFiNetworkClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                v = await client.vouchers.get("s1", "v1")
                assert v.id == "v1"

    # --- Traffic: None responses ---
    async def test_traffic_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover traffic.py line 64."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                lists = await client.traffic.get_all_lists("s1")
                assert lists == []

    async def test_traffic_dpi_categories_none(self, auth: LocalAuth) -> None:
        """Cover traffic.py line 184."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                cats = await client.traffic.get_dpi_categories()
                assert cats == []

    async def test_traffic_dpi_applications_none(self, auth: LocalAuth) -> None:
        """Cover traffic.py line 204."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                apps = await client.traffic.get_dpi_applications()
                assert apps == []

    async def test_traffic_countries_none(self, auth: LocalAuth) -> None:
        """Cover traffic.py line 224."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                countries = await client.traffic.get_countries()
                assert countries == []

    # --- Resources: None responses ---
    async def test_resources_wan_none_response(self, auth: LocalAuth) -> None:
        """Cover resources.py line 63."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                wans = await client.resources.get_wan_interfaces("s1")
                assert wans == []

    async def test_resources_vpn_tunnels_none(self, auth: LocalAuth) -> None:
        """Cover resources.py line 103."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                tunnels = await client.resources.get_vpn_tunnels("s1")
                assert tunnels == []

    async def test_resources_vpn_servers_none(self, auth: LocalAuth) -> None:
        """Cover resources.py line 143."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                servers = await client.resources.get_vpn_servers("s1")
                assert servers == []

    async def test_resources_vpn_servers_nonlist(self, auth: LocalAuth) -> None:
        """Cover resources.py line 148."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                servers = await client.resources.get_vpn_servers("s1")
                assert servers == []

    async def test_resources_radius_none(self, auth: LocalAuth) -> None:
        """Cover resources.py line 183."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                profiles = await client.resources.get_radius_profiles("s1")
                assert profiles == []

    async def test_resources_radius_nonlist(self, auth: LocalAuth) -> None:
        """Cover resources.py line 188."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                profiles = await client.resources.get_radius_profiles("s1")
                assert profiles == []

    async def test_resources_device_tags_none(self, auth: LocalAuth) -> None:
        """Cover resources.py line 223."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                tags = await client.resources.get_device_tags("s1")
                assert tags == []

    async def test_resources_device_tags_nonlist(self, auth: LocalAuth) -> None:
        """Cover resources.py line 228."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                tags = await client.resources.get_device_tags("s1")
                assert tags == []

    # --- DNS: None response ---
    async def test_dns_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover dns.py None response branch."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                policies = await client.dns.get_all("s1")
                assert policies == []

    # --- Cameras: mic/speaker volume valid ---
    async def test_cameras_set_mic_volume_valid(self, auth: LocalAuth) -> None:
        """Cover cameras.py line 168: valid mic volume."""
        cam_data = {"id": "c1", "mac": "aa:bb:cc:dd:ee:ff", "name": "Cam"}
        with aioresponses() as m:
            m.patch(re.compile(r".*/cameras/c1"), payload={"data": cam_data})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                cam = await client.cameras.set_microphone_volume("c1", 50)
                assert cam.id == "c1"

    async def test_cameras_set_speaker_volume_valid(self, auth: LocalAuth) -> None:
        """Cover cameras.py line 188: valid speaker volume."""
        cam_data = {"id": "c1", "mac": "aa:bb:cc:dd:ee:ff", "name": "Cam"}
        with aioresponses() as m:
            m.patch(re.compile(r".*/cameras/c1"), payload={"data": cam_data})
            async with UniFiProtectClient(
                auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
            ) as client:
                cam = await client.cameras.set_speaker_volume("c1", 50)
                assert cam.id == "c1"

    # --- Cameras: non-list data ---
    async def test_cameras_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover cameras.py line 43: data is not a list."""
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                cams = await client.cameras.get_all()
                assert cams == []

    # --- Chimes: non-list data ---
    async def test_chimes_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover chimes.py line 42."""
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                chimes = await client.chimes.get_all()
                assert chimes == []

    # --- Lights: non-list data ---
    async def test_lights_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover lights.py line 42."""
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                lights = await client.lights.get_all()
                assert lights == []

    # --- Sensors: non-list data ---
    async def test_sensors_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover sensors.py line 42."""
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                sensors = await client.sensors.get_all()
                assert sensors == []

    # --- Liveviews: non-list data ---
    async def test_liveviews_get_all_nonlist_data(self, auth: LocalAuth) -> None:
        """Cover liveviews.py line 42."""
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": 42}):
                views = await client.liveviews.get_all()
                assert views == []

    # --- Viewers: None response ---
    async def test_viewers_get_all_none_response(self, auth: LocalAuth) -> None:
        """Cover viewers.py line 37."""
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=None):
                viewers = await client.viewers.get_all()
                assert viewers == []

    # --- Protect client: ClientConnectorError in _get_binary ---
    async def test_protect_get_binary_connector_error(self, auth: LocalAuth) -> None:
        """Cover protect/client.py line 326."""
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with aioresponses() as m:
                m.get(
                    re.compile(r".*"),
                    exception=aiohttp.ClientConnectorError(
                        connection_key=MagicMock(), os_error=OSError("conn refused")
                    ),
                )
                with pytest.raises(UniFiConnectionError, match="Failed to connect"):
                    await client._get_binary(f"{PROTECT_BASE}/cameras/c1/snapshot")


# ===========================================================================
# Remaining partial branch coverage
# ===========================================================================


class TestPartialBranches:
    """Cover remaining partial branches (get with list data, create/update/delete error paths)."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        return LocalAuth(api_key="test", verify_ssl=False)

    # --- network/client.py 256->258: get_application_info data is list, not dict ---
    async def test_app_info_data_is_list(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": []}):
                with pytest.raises(UniFiNotFoundError):
                    await client.get_application_info()

    # --- clients.py 79->81: get with list data ---
    async def test_clients_get_dict_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "c1", "mac": "aa:bb:cc:dd:ee:ff"}]},
            ):
                c = await client.clients.get("s1", "c1")
                assert c.id == "c1"

    # --- devices.py 79->81: get with list data ---
    async def test_devices_get_dict_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "d1", "name": "SW"}]},
            ):
                d = await client.devices.get("s1", "d1")
                assert d.id == "d1"

    # --- sites.py non-list data ---
    async def test_sites_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                assert await client.sites.get_all() == []

    # --- acl.py branches: get with dict data, get with list ---
    async def test_acl_get_not_found(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.acl.get("s1", "a1")

    async def test_acl_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={
                    "data": [
                        {"id": "a1", "name": "R", "type": "IPV4", "action": "BLOCK", "index": 0}
                    ]
                },
            ):
                r = await client.acl.get("s1", "a1")
                assert r.id == "a1"

    # --- acl.py create error branch ---
    async def test_acl_create_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.acl.create("s1", name="Test")

    # --- acl.py update error branch ---
    # --- dns.py branches: get with dict data, create/update/delete errors ---
    async def test_dns_get_dict_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "d1", "type": "A_RECORD", "domain": "test.local"}]},
            ):
                p = await client.dns.get("s1", "d1")
                assert p.id == "d1"

    async def test_dns_create_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.dns.create(
                        "s1",
                        record_type=DNSRecordType.A_RECORD,
                        domain="test.local",
                        value="1.2.3.4",
                    )

    async def test_dns_delete_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_delete", new_callable=AsyncMock, return_value="fail"):
                # delete should still work or raise
                await client.dns.delete("s1", "d1")

    # --- networks.py branches ---
    async def test_networks_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "n1", "name": "LAN"}]},
            ):
                n = await client.networks.get("s1", "n1")
                assert n.id == "n1"

    async def test_networks_create_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.networks.create("s1", name="Test")

    async def test_networks_delete_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_delete", new_callable=AsyncMock, return_value="fail"):
                await client.networks.delete("s1", "n1")

    # --- wifi.py branches ---
    async def test_wifi_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "w1", "name": "MyWiFi"}]},
            ):
                w = await client.wifi.get("s1", "w1")
                assert w.id == "w1"

    async def test_wifi_create_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.wifi.create("s1", name="Test", ssid="Test", passphrase="secret")

    async def test_wifi_update_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiNotFoundError):
                    await client.wifi.update("s1", "w1")

    async def test_wifi_delete_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_delete", new_callable=AsyncMock, return_value="fail"):
                await client.wifi.delete("s1", "w1")

    # --- vouchers.py branches ---
    async def test_vouchers_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "v1", "code": "ABC123"}]},
            ):
                v = await client.vouchers.get("s1", "v1")
                assert v.id == "v1"

    async def test_vouchers_create_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.vouchers.create("s1", name="Test", time_limit_minutes=60)

    async def test_vouchers_delete_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_delete", new_callable=AsyncMock, return_value="fail"):
                await client.vouchers.delete("s1", "v1")

    # --- traffic.py branches ---
    async def test_traffic_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={
                    "data": [{"id": "t1", "name": "Test", "type": "DOMAIN", "entries": []}]
                },
            ):
                t = await client.traffic.get_list("s1", "t1")
                assert t.id == "t1"

    async def test_traffic_create_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.traffic.create_list(
                        "s1",
                        name="Test",
                        list_type=TrafficMatchingType.PORTS,
                        entries=["80"],
                    )

    async def test_traffic_delete_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_delete", new_callable=AsyncMock, return_value="fail"):
                await client.traffic.delete_list("s1", "t1")

    # --- firewall.py branches ---
    async def test_firewall_create_zone_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.firewall.create_zone("s1", name="Test")

    async def test_firewall_delete_zone_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_delete", new_callable=AsyncMock, return_value="fail"):
                await client.firewall.delete_zone("s1", "z1")

    # --- Protect cameras: get with list data, get RTSPS stream ---
    async def test_cameras_get_list_data(self, auth: LocalAuth) -> None:
        cam_data = {"id": "c1", "mac": "aa:bb:cc:dd:ee:ff", "name": "Cam"}
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [cam_data]},
            ):
                c = await client.cameras.get("c1")
                assert c.id == "c1"

    async def test_cameras_get_rtsps_stream(self, auth: LocalAuth) -> None:
        cam_data = {"id": "c1", "mac": "aa:bb:cc:dd:ee:ff", "name": "Cam"}
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": cam_data},
            ):
                c = await client.cameras.get("c1")
                url = c.construct_rtsp_url("192.168.1.1", port=7441, channel=0)
                assert "rtsps://" in url

    # --- Protect chimes: get with list data ---
    async def test_chimes_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "ch1", "mac": "aa:bb:cc"}]},
            ):
                ch = await client.chimes.get("ch1")
                assert ch.id == "ch1"

    # --- Protect lights: get with list data ---
    async def test_lights_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "l1", "mac": "aa:bb:cc"}]},
            ):
                light = await client.lights.get("l1")
                assert light.id == "l1"

    # --- Protect sensors: get with list data ---
    async def test_sensors_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "s1", "mac": "aa:bb:cc"}]},
            ):
                s = await client.sensors.get("s1")
                assert s.id == "s1"

    # --- Protect liveviews: get with list data, create/update error ---
    async def test_liveviews_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "lv1", "name": "View"}]},
            ):
                lv = await client.liveviews.get("lv1")
                assert lv.id == "lv1"

    async def test_liveviews_create_with_site_id_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.liveviews.create(name="Test", slot_ids=[])

    # --- Protect NVR: get with list data ---
    async def test_nvr_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "nvr1", "mac": "aa:bb:cc", "name": "NVR"}]},
            ):
                n = await client.nvr.get()
                assert n.id == "nvr1"

    # --- Protect viewers: get with list data (84->88) ---
    async def test_viewers_get_list_data(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"data": [{"id": "vw1", "mac": "aa:bb:cc", "state": "CONNECTED"}]},
            ):
                v = await client.viewers.get("vw1")
                assert v.id == "vw1"

    # --- client.py 26->29: ClientType._missing_ case-insensitive ---
    def test_client_type_case_insensitive(self) -> None:
        ct = ClientType("wired")
        assert ct == ClientType.WIRED

    def test_client_type_unknown_raises(self) -> None:
        with pytest.raises(ValueError):
            ClientType("NONEXISTENT_TYPE")

    # --- Protect cameras: update error, get not found ---
    async def test_cameras_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.cameras.get("c1")

    # --- Protect chimes: update error, get not found ---
    async def test_chimes_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.chimes.get("ch1")

    # --- Protect lights: update error, get not found ---
    async def test_lights_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.lights.get("l1")

    # --- Protect sensors: update error, get not found ---
    async def test_sensors_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.sensors.get("s1")

    # --- Protect liveviews: get not found ---
    async def test_liveviews_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.liveviews.get("lv1")

    # --- Protect NVR: get not found ---
    async def test_nvr_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.nvr.get()

    # --- Protect viewers: get not found ---
    async def test_viewers_get_not_found_error(self, auth: LocalAuth) -> None:
        async with UniFiProtectClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": "str"}):
                with pytest.raises(UniFiNotFoundError):
                    await client.viewers.get("vw1")

    # --- Network endpoints: get not found, create/update/delete success for remaining ---
    async def test_acl_get_dict_direct(self, auth: LocalAuth) -> None:
        """Cover acl.py branch where data is dict directly."""
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={
                    "id": "a1",
                    "name": "R",
                    "type": "IPV4",
                    "action": "BLOCK",
                    "index": 0,
                },
            ):
                r = await client.acl.get("s1", "a1")
                assert r.id == "a1"

    # --- Network: ACL ordering success (non-data wrapped) ---
    async def test_acl_ordering_no_data_key(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"orderedAclRuleIds": ["a1", "a2"]},
            ):
                o = await client.acl.get_ordering("s1")
                assert len(o.ordered_acl_rule_ids) == 2

    async def test_acl_update_ordering_no_data_key(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_put",
                new_callable=AsyncMock,
                return_value={"orderedAclRuleIds": ["a2", "a1"]},
            ):
                o = await client.acl.update_ordering("s1", ordered_rule_ids=["a2", "a1"])
                assert o.ordered_acl_rule_ids == ["a2", "a1"]

    # --- Network: DNS get/create/update with non-data-wrapped response ---
    async def test_dns_get_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"id": "d1", "type": "A_RECORD", "domain": "test.local"},
            ):
                p = await client.dns.get("s1", "d1")
                assert p.id == "d1"

    async def test_dns_create_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_post",
                new_callable=AsyncMock,
                return_value={
                    "id": "d1",
                    "type": "A_RECORD",
                    "domain": "test.local",
                    "value": "1.2.3.4",
                },
            ):
                p = await client.dns.create(
                    "s1", record_type=DNSRecordType.A_RECORD, domain="test.local", value="1.2.3.4"
                )
                assert p.id == "d1"

    async def test_dns_update_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_put",
                new_callable=AsyncMock,
                return_value={"id": "d1", "type": "A_RECORD", "domain": "test.local"},
            ):
                p = await client.dns.update("s1", "d1")
                assert p.id == "d1"

    # --- Network: networks get/create/update with direct dict ---
    async def test_networks_get_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"id": "n1", "name": "LAN"},
            ):
                n = await client.networks.get("s1", "n1")
                assert n.id == "n1"

    async def test_networks_create_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_post",
                new_callable=AsyncMock,
                return_value={"id": "n1", "name": "Test"},
            ):
                n = await client.networks.create("s1", name="Test")
                assert n.id == "n1"

    async def test_networks_update_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_put",
                new_callable=AsyncMock,
                return_value={"id": "n1", "name": "Updated"},
            ):
                n = await client.networks.update("s1", "n1", name="Updated")
                assert n.id == "n1"

    # --- WiFi: get/create/update with direct dict ---
    async def test_wifi_get_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"id": "w1", "name": "WiFi"},
            ):
                w = await client.wifi.get("s1", "w1")
                assert w.id == "w1"

    async def test_wifi_create_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_post",
                new_callable=AsyncMock,
                return_value={"id": "w1", "name": "Test", "ssid": "Test"},
            ):
                w = await client.wifi.create("s1", name="Test", ssid="Test", passphrase="secret")
                assert w.id == "w1"

    async def test_wifi_update_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with (
                patch.object(
                    client,
                    "_get",
                    new_callable=AsyncMock,
                    return_value={"data": {"id": "w1", "name": "Old"}},
                ),
                patch.object(
                    client,
                    "_put",
                    new_callable=AsyncMock,
                    return_value={"id": "w1", "name": "Updated"},
                ),
            ):
                w = await client.wifi.update("s1", "w1", name="Updated")
                assert w.id == "w1"

    # --- Traffic: get_list direct, create/update direct dict ---
    async def test_traffic_get_list_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"id": "t1", "name": "T", "type": "DOMAIN", "entries": []},
            ):
                t = await client.traffic.get_list("s1", "t1")
                assert t.id == "t1"

    # --- Vouchers: get direct dict ---
    async def test_vouchers_get_dict_direct(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(
                client,
                "_get",
                new_callable=AsyncMock,
                return_value={"id": "v1", "code": "ABC"},
            ):
                v = await client.vouchers.get("s1", "v1")
                assert v.id == "v1"

    # --- Firewall: policy ordering create/update ---
    async def test_firewall_create_rule_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_post", new_callable=AsyncMock, return_value=[]):
                with pytest.raises(UniFiResponseError):
                    await client.firewall.create_rule(
                        "s1",
                        name="Test",
                        action="accept",
                        source_zone_id="z1",
                        destination_zone_id="z2",
                    )

    async def test_firewall_update_rule_error(self, auth: LocalAuth) -> None:
        async with UniFiNetworkClient(
            auth=auth, base_url="https://192.168.1.1", connection_type=ConnectionType.LOCAL
        ) as client:
            with patch.object(client, "_get", new_callable=AsyncMock, return_value={"data": []}):
                with pytest.raises(UniFiNotFoundError):
                    await client.firewall.update_rule("s1", "r1")
