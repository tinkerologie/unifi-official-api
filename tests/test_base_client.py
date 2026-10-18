"""Tests for base client functionality."""

from __future__ import annotations

import re

import pytest
from aioresponses import aioresponses

from unifi_official_api import (
    LocalAuth,
    UniFiAuthenticationError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiResponseError,
)
from unifi_official_api.const import ConnectionType
from unifi_official_api.network import UniFiNetworkClient


class TestBaseClientErrorHandling:
    """Tests for base client error handling."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        """Create test auth."""
        return LocalAuth(api_key="test-api-key", verify_ssl=False)

    @pytest.fixture
    def base_url(self) -> str:
        """Return test base URL."""
        return "https://192.168.1.1"

    async def test_authentication_error_401(self, auth: LocalAuth, base_url: str) -> None:
        """Test 401 unauthorized raises authentication error."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                status=401,
                body="Unauthorized",
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiAuthenticationError) as exc_info:
                    await client.sites.get_all()
                assert "Authentication failed" in str(exc_info.value)

    async def test_authentication_error_403(self, auth: LocalAuth, base_url: str) -> None:
        """Test 403 forbidden raises authentication error."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                status=403,
                body="Forbidden",
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiAuthenticationError) as exc_info:
                    await client.sites.get_all()
                assert "Access forbidden" in str(exc_info.value)

    async def test_not_found_error(self, auth: LocalAuth, base_url: str) -> None:
        """Test 404 not found raises not found error."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites/site-1/devices/device-999",
                status=404,
                body="Not Found",
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiNotFoundError) as exc_info:
                    await client.devices.get("site-1", "device-999")
                assert exc_info.value.status_code == 404

    async def test_rate_limit_error(self, auth: LocalAuth, base_url: str) -> None:
        """Test 429 rate limit raises rate limit error."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                status=429,
                body="Too Many Requests",
                headers={"Retry-After": "30"},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiRateLimitError) as exc_info:
                    await client.sites.get_all()
                assert exc_info.value.retry_after == 30

    async def test_rate_limit_error_no_retry_header(self, auth: LocalAuth, base_url: str) -> None:
        """Test 429 rate limit without Retry-After header."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                status=429,
                body="Too Many Requests",
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiRateLimitError) as exc_info:
                    await client.sites.get_all()
                assert exc_info.value.retry_after == 60  # Default

    async def test_server_error(self, auth: LocalAuth, base_url: str) -> None:
        """Test 500 server error raises response error."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                status=500,
                body="Internal Server Error",
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError) as exc_info:
                    await client.sites.get_all()
                assert exc_info.value.status_code == 500

    async def test_empty_response(self, auth: LocalAuth, base_url: str) -> None:
        """Test handling of empty response."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                status=200,
                body="",
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.sites.get_all()
                assert result == []

    async def test_non_json_response(self, auth: LocalAuth, base_url: str) -> None:
        """Test handling of non-JSON response."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                status=200,
                body="Not JSON content",
                content_type="text/plain",
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                with pytest.raises(UniFiResponseError):
                    await client.sites.get_all()


class TestNetworkEndpoints:
    """Tests for network endpoint methods."""

    @pytest.fixture
    def auth(self) -> LocalAuth:
        """Create test auth."""
        return LocalAuth(api_key="test-api-key", verify_ssl=False)

    @pytest.fixture
    def base_url(self) -> str:
        """Return test base URL."""
        return "https://192.168.1.1"

    @pytest.fixture
    def site_id(self) -> str:
        """Return test site ID."""
        return "site-1"

    async def test_sites_get_all(self, auth: LocalAuth, base_url: str) -> None:
        """Test listing sites."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites",
                payload={"data": [{"id": "site-1", "name": "Default"}]},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                sites = await client.sites.get_all()
                assert len(sites) == 1
                assert sites[0].id == "site-1"

    async def test_sites_get(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test that sites endpoint has no individual get method per OpenAPI spec."""
        async with UniFiNetworkClient(
            auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
        ) as client:
            assert not hasattr(client.sites, "get")

    async def test_networks_get_all(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test listing networks."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/networks",
                payload={"data": [{"id": "net-1", "name": "LAN", "vlan": 1}]},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                networks = await client.networks.get_all(site_id)
                assert len(networks) == 1
                assert networks[0].id == "net-1"

    async def test_networks_get(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test getting a specific network."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/networks/net-1",
                payload={"data": {"id": "net-1", "name": "LAN"}},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                network = await client.networks.get(site_id, "net-1")
                assert network.id == "net-1"

    async def test_networks_create(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test creating a network."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/networks",
                payload={"data": {"id": "net-2", "name": "Guest", "vlan": 10}},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                network = await client.networks.create(site_id, name="Guest", vlan=10)
                assert network.id == "net-2"

    async def test_networks_update(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test updating a network."""
        with aioresponses() as m:
            m.put(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/networks/net-1",
                payload={"data": {"id": "net-1", "name": "Updated"}},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                network = await client.networks.update(site_id, "net-1", name="Updated")
                assert network.name == "Updated"

    async def test_networks_delete(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test deleting a network."""
        with aioresponses() as m:
            m.delete(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/networks/net-1",
                status=204,
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.networks.delete(site_id, "net-1")
                assert result is True

    async def test_wifi_get_all(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test listing WiFi networks."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/wifi/broadcasts",
                payload={"data": [{"id": "wifi-1", "name": "Home WiFi", "ssid": "Home"}]},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                wifi_networks = await client.wifi.get_all(site_id)
                assert len(wifi_networks) == 1
                assert wifi_networks[0].ssid == "Home"

    async def test_wifi_create(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test creating a WiFi network."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/wifi/broadcasts",
                payload={"data": {"id": "wifi-2", "name": "Guest", "ssid": "Guest"}},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                wifi = await client.wifi.create(
                    site_id, name="Guest", ssid="Guest", passphrase="password123"
                )
                assert wifi.ssid == "Guest"

    async def test_firewall_list_zones(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test listing firewall zones."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/firewall/zones",
                payload={"data": [{"id": "zone-1", "name": "LAN"}]},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                zones = await client.firewall.list_zones(site_id)
                assert len(zones) == 1
                assert zones[0].name == "LAN"

    async def test_firewall_list_rules(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test listing firewall rules."""
        with aioresponses() as m:
            m.get(
                re.compile(
                    rf".*{re.escape(base_url)}/proxy/network/integration/v1/sites/{site_id}/firewall/policies.*"
                ),
                payload={
                    "data": [{"id": "rule-1", "name": "Block", "action": "drop"}],
                    "totalCount": 1,
                    "count": 1,
                },
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                rules = await client.firewall.list_rules(site_id)
                assert len(rules) == 1
                assert rules[0].name == "Block"

    async def test_firewall_get_rule(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test getting a specific firewall rule."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/firewall/policies/rule-1",
                payload={"data": {"id": "rule-1", "name": "Block"}},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                rule = await client.firewall.get_rule(site_id, "rule-1")
                assert rule.id == "rule-1"

    async def test_firewall_create_rule(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test creating a firewall rule."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/firewall/policies",
                payload={
                    "data": {
                        "id": "rule-2",
                        "name": "Allow",
                        "action": {"type": "ALLOW"},
                        "protocol": "all",
                    }
                },
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                rule = await client.firewall.create_rule(
                    site_id,
                    name="Allow",
                    action="accept",
                    protocol="all",
                    source_zone_id="zone-1",
                    destination_zone_id="zone-2",
                )
                assert rule.name == "Allow"

    async def test_firewall_update_rule(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test updating a firewall rule (GET + PUT)."""
        rule_url = (
            f"{base_url}/proxy/network/integration/v1/sites/{site_id}/firewall/policies/rule-1"
        )
        with aioresponses() as m:
            m.get(
                rule_url,
                payload={"data": {"id": "rule-1", "name": "Old"}},
            )
            m.put(
                rule_url,
                payload={"data": {"id": "rule-1", "name": "Updated"}},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                rule = await client.firewall.update_rule(site_id, "rule-1", name="Updated")
                assert rule.name == "Updated"

    async def test_firewall_delete_rule(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test deleting a firewall rule."""
        with aioresponses() as m:
            m.delete(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/firewall/policies/rule-1",
                status=204,
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.firewall.delete_rule(site_id, "rule-1")
                assert result is True

    async def test_clients_get(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test getting a specific client."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/clients/client-1",
                payload={"data": {"id": "client-1", "name": "Test Client"}},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                network_client = await client.clients.get(site_id, "client-1")
                assert network_client.id == "client-1"

    async def test_clients_block(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test blocking a client via stamgr."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/api/s/{site_id}/cmd/stamgr",
                payload={"meta": {"rc": "ok"}, "data": []},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.clients.block(site_id, "00:11:22:33:44:55")
                assert result is True

    async def test_clients_unblock(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test unblocking a client via stamgr."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/api/s/{site_id}/cmd/stamgr",
                payload={"meta": {"rc": "ok"}, "data": []},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.clients.unblock(site_id, "00:11:22:33:44:55")
                assert result is True

    async def test_clients_reconnect(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test reconnecting a client via stamgr."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/api/s/{site_id}/cmd/stamgr",
                payload={"meta": {"rc": "ok"}, "data": []},
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.clients.reconnect(site_id, "00:11:22:33:44:55")
                assert result is True

    async def test_devices_restart(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test restarting a device."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/devices/device-1/actions",
                status=204,
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.devices.restart(site_id, "device-1")
                assert result is True

    async def test_devices_adopt(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test adopting a device."""
        with aioresponses() as m:
            m.post(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/devices",
                status=204,
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.devices.adopt(site_id, "00:11:22:33:44:55")
                assert result is True

    async def test_devices_forget(self, auth: LocalAuth, base_url: str, site_id: str) -> None:
        """Test forgetting a device."""
        with aioresponses() as m:
            m.delete(
                f"{base_url}/proxy/network/integration/v1/sites/{site_id}/devices/device-1",
                status=204,
            )

            async with UniFiNetworkClient(
                auth=auth, base_url=base_url, connection_type=ConnectionType.LOCAL
            ) as client:
                result = await client.devices.forget(site_id, "device-1")
                assert result is True
