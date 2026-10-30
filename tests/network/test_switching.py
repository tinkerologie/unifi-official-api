"""Tests for UniFi Network switching endpoints."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from unifi_official_api import ConnectionType, LocalAuth
from unifi_official_api.exceptions import UniFiNotFoundError
from unifi_official_api.network import UniFiNetworkClient
from unifi_official_api.network.models.stack import SwitchStackUnitRole
from unifi_official_api.network.models.switching import (
    Lag,
    LagPage,
    McLagDomain,
    McLagDomainPage,
    SwitchStack,
    SwitchStackPage,
)


class TestSwitchingEndpoint:
    """Tests for switching endpoint."""

    @pytest.fixture
    def client(self) -> UniFiNetworkClient:
        """Create network client."""
        return UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key", verify_ssl=False),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        )

    async def test_get_lags(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_lags."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/lags?limit=10&offset=0",
            payload={
                "data": [
                    {
                        "id": "lag-1",
                        "name": "Core LAG",
                        "mode": "DYNAMIC",
                        "members": [{"switchMac": "aa:bb:cc:dd:ee:ff", "portIdx": 1}],
                    }
                ],
                "totalCount": 1,
                "limit": 10,
                "offset": 0,
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/lags",
            payload=None,
        )

        async with client:
            page = await client.switching.get_lags("default", limit=10, offset=0)
            assert isinstance(page, LagPage)
            assert len(page.data) == 1
            assert page.data[0].id == "lag-1"
            assert page.data[0].name == "Core LAG"

            empty = await client.switching.get_lags("default")
            assert empty.data == []

    async def test_get_lag(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_lag."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/lags/lag-1",
            payload={
                "data": {
                    "id": "lag-1",
                    "name": "Core LAG",
                    "mode": "DYNAMIC",
                    "members": [{"switchMac": "aa:bb:cc:dd:ee:ff", "portIdx": 1}],
                }
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/lags/bad-id",
            payload={},
        )

        async with client:
            lag = await client.switching.get_lag("default", "lag-1")
            assert isinstance(lag, Lag)
            assert lag.id == "lag-1"
            assert len(lag.members) == 1

            with pytest.raises(UniFiNotFoundError):
                await client.switching.get_lag("default", "bad-id")

    async def test_get_mc_lag_domains(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_mc_lag_domains."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/mc-lag-domains?limit=5",
            payload={
                "data": [
                    {
                        "id": "mclag-1",
                        "domainId": 10,
                        "peers": [{"switchMac": "aa:bb:cc:dd:ee:ff", "role": "PRIMARY"}],
                    }
                ],
                "totalCount": 1,
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/mc-lag-domains",
            payload=None,
        )

        async with client:
            page = await client.switching.get_mc_lag_domains("default", limit=5)
            assert isinstance(page, McLagDomainPage)
            assert len(page.data) == 1
            assert page.data[0].domain_id == 10

            empty = await client.switching.get_mc_lag_domains("default")
            assert empty.data == []

    async def test_get_mc_lag_domain(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_mc_lag_domain."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/mc-lag-domains/mclag-1",
            payload={
                "data": {
                    "id": "mclag-1",
                    "domainId": 10,
                    "peers": [{"switchMac": "aa:bb:cc:dd:ee:ff", "role": "PRIMARY"}],
                }
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/mc-lag-domains/bad-id",
            payload={},
        )

        async with client:
            domain = await client.switching.get_mc_lag_domain("default", "mclag-1")
            assert isinstance(domain, McLagDomain)
            assert domain.id == "mclag-1"

            with pytest.raises(UniFiNotFoundError):
                await client.switching.get_mc_lag_domain("default", "bad-id")

    async def test_get_switch_stacks(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_switch_stacks."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks?limit=10",
            payload={
                "data": [
                    {
                        "id": "stack-1",
                        "name": "Stack 1",
                        "members": [{"switchMac": "11:22:33:44:55:66", "role": "MASTER"}],
                    }
                ],
                "totalCount": 1,
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks",
            payload=None,
        )

        async with client:
            page = await client.switching.get_switch_stacks("default", limit=10)
            assert isinstance(page, SwitchStackPage)
            assert len(page.data) == 1
            assert page.data[0].id == "stack-1"

            empty = await client.switching.get_switch_stacks("default")
            assert empty.data == []

    async def test_get_switch_stack(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_switch_stack."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks/stack-1",
            payload={
                "data": {
                    "id": "stack-1",
                    "name": "Stack 1",
                    "members": [{"switchMac": "11:22:33:44:55:66", "role": "MASTER"}],
                }
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks/bad-id",
            payload={},
        )

        async with client:
            stack = await client.switching.get_switch_stack("default", "stack-1")
            assert isinstance(stack, SwitchStack)
            assert stack.id == "stack-1"

            with pytest.raises(UniFiNotFoundError):
                await client.switching.get_switch_stack("default", "bad-id")

    async def test_get_switch_stacks_v11_units(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_switch_stacks with the Network 11.0.97 units shape."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks?limit=10",
            payload={
                "data": [
                    {
                        "id": "stack-1",
                        "name": "Stack 1",
                        "deviceId": "dev-1",
                        "units": [
                            {
                                "id": 1,
                                "macAddress": "11:22:33:44:55:66",
                                "order": 1,
                                "role": "ACTIVE_CONTROLLER",
                            }
                        ],
                        "lags": [
                            {
                                "id": "lag-1",
                                "members": [
                                    {
                                        "unitId": 1,
                                        "unitMacAddress": "11:22:33:44:55:66",
                                        "portIdxs": [1, 2],
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "totalCount": 1,
            },
        )

        async with client:
            page = await client.switching.get_switch_stacks("default", limit=10)

        assert isinstance(page, SwitchStackPage)
        stack = page.data[0]
        assert stack.device_id == "dev-1"
        assert stack.units[0].mac_address == "11:22:33:44:55:66"
        assert stack.units[0].role == SwitchStackUnitRole.ACTIVE_CONTROLLER
        assert stack.members == []
        member = stack.lags[0].members[0]
        assert member.unit_id == 1
        assert member.unit_mac_address == "11:22:33:44:55:66"
        assert member.port_idxs == [1, 2]

    async def test_get_switch_stack_v11_units(
        self, client: UniFiNetworkClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test get_switch_stack with the Network 11.0.97 units shape."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks/stack-1",
            payload={
                "data": {
                    "id": "stack-1",
                    "name": "Stack 1",
                    "deviceId": "dev-1",
                    "units": [
                        {
                            "id": 2,
                            "macAddress": "11:22:33:44:55:77",
                            "order": 2,
                            "role": "MEMBER",
                        }
                    ],
                    "lags": [
                        {
                            "id": "lag-1",
                            "members": [
                                {
                                    "unitId": 2,
                                    "unitMacAddress": "11:22:33:44:55:77",
                                    "portIdxs": [3],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        async with client:
            stack = await client.switching.get_switch_stack("default", "stack-1")

        assert isinstance(stack, SwitchStack)
        assert stack.units[0].id == 2
        assert stack.units[0].order == 2
        assert stack.units[0].role == SwitchStackUnitRole.MEMBER
        assert stack.lags[0].members[0].unit_id == 2
