"""Tests covering all remaining edge cases to achieve 100% coverage across the codebase."""

from __future__ import annotations

from unittest.mock import AsyncMock

import aiohttp
import pytest

from unifi_official_api import ApiKeyAuth, ConnectionType
from unifi_official_api.mobility.client import UniFiMobilityClient
from unifi_official_api.network.client import UniFiNetworkClient
from unifi_official_api.network.models.acl import ACLRule
from unifi_official_api.network.models.dns import DNSPolicy
from unifi_official_api.network.models.firewall import FirewallRule
from unifi_official_api.protect.client import UniFiProtectClient
from unifi_official_api.protect.models.camera import CameraState, CameraType
from unifi_official_api.protect.models.nvr import NVR, StorageInfo
from unifi_official_api.protect.websocket import ProtectWebSocket
from unifi_official_api.site_manager.client import UniFiSiteManagerClient
from unifi_official_api.site_manager.models.isp_metric import ISPMetricQueryResult


def test_acl_rule_is_user_defined_dict_and_invalid_metadata() -> None:
    """Test ACLRule.is_user_defined when metadata is a dict or arbitrary object."""
    r = ACLRule(name="test_rule", action="ALLOW")

    object.__setattr__(r, "metadata", {"origin": "USER_DEFINED"})
    assert r.is_user_defined is True

    object.__setattr__(r, "metadata", {"origin": "SYSTEM_DEFINED"})
    assert r.is_user_defined is False

    object.__setattr__(r, "metadata", 123)
    assert r.is_user_defined is False


def test_dns_policy_is_user_defined_dict_and_invalid_metadata() -> None:
    """Test DNSPolicy.is_user_defined when metadata is a dict or arbitrary object."""
    p = DNSPolicy(type="A_RECORD")

    object.__setattr__(p, "metadata", {"origin": "USER_DEFINED"})
    assert p.is_user_defined is True

    object.__setattr__(p, "metadata", {"origin": "SYSTEM"})
    assert p.is_user_defined is False

    object.__setattr__(p, "metadata", 999)
    assert p.is_user_defined is False


def test_firewall_rule_action_type_dict_and_other() -> None:
    """Test FirewallRule.action_type when action is a dict or string."""
    f_dict_allow = FirewallRule(id="f-1", name="f1", action={"type": "ALLOW"})
    assert f_dict_allow.action_type == "ALLOW"

    f_dict_default = FirewallRule(id="f-2", name="f2", action={})
    assert f_dict_default.action_type == "BLOCK"

    f_str = FirewallRule(id="f-3", name="f3", action="REJECT")
    assert f_str.action_type == "REJECT"


def test_camera_tolerant_enums_unknown_values() -> None:
    """Test _TolerantStrEnum._missing_ for unknown CameraType and CameraState."""
    assert CameraType("UNKNOWN_CAMERA_MODEL_123") == CameraType.UNKNOWN
    assert CameraState("SOME_NEW_FUTURE_STATE") == CameraState.UNKNOWN


def test_nvr_model_serializer_storage_info_branches() -> None:
    """Test NVR._serialize_storage when storage_info is None, or excluded."""
    # Branch 75->84: storage_info is not StorageInfo (e.g. None)
    nvr_none = NVR(id="nvr-none", name="NVR None", storage_info=None)
    dump_none = nvr_none.model_dump()
    assert dump_none["storage_info"] is None

    # Branch 77->84: storage_info excluded from dump, so key not in result
    nvr_with_storage = NVR(id="nvr-storage", name="NVR Storage", storage_info=StorageInfo())
    dump_excluded = nvr_with_storage.model_dump(exclude={"storage_info"})
    assert "storage_info" not in dump_excluded

    dump_alias_excluded = nvr_with_storage.model_dump(by_alias=True, exclude={"storage_info"})
    assert "storageInfo" not in dump_alias_excluded


@pytest.mark.asyncio
async def test_arm_profiles_update_settings_non_dict_response() -> None:
    """Test arm_profiles.update_settings when response is non-dict (branch 307->311)."""
    client = UniFiProtectClient(
        auth=ApiKeyAuth(api_key="test-key"),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    )
    client._patch = AsyncMock(return_value="unexpected_string_response")

    with pytest.raises(ValueError, match="Failed to update arm profile settings"):
        await client.arm_profiles.update_settings(active_profile_id="arm-1")


@pytest.mark.asyncio
async def test_hosts_endpoint_get_non_dict_response() -> None:
    """Test hosts.get when response is not a dict (branch 35->39)."""
    client = UniFiSiteManagerClient(
        auth=ApiKeyAuth(api_key="test-key"),
    )
    client._get = AsyncMock(return_value=["unexpected", "list"])

    with pytest.raises(ValueError, match="Host h-1 not found"):
        await client.hosts.get("h-1")


@pytest.mark.asyncio
async def test_isp_metrics_query_non_dict_response() -> None:
    """Test isp_metrics.query when response is not a dict (branch 81->85)."""
    client = UniFiSiteManagerClient(
        auth=ApiKeyAuth(api_key="test-key"),
    )
    client._post = AsyncMock(return_value="not_a_dict")

    res = await client.isp_metrics.query(metric_type="latency", query_data={})
    assert isinstance(res, ISPMetricQueryResult)


@pytest.mark.asyncio
async def test_mobility_devices_get_non_dict_response() -> None:
    """Test mobility.devices.get when response is not a dict (branch 33->37)."""
    client = UniFiMobilityClient(
        auth=ApiKeyAuth(api_key="test-key"),
    )
    client._get = AsyncMock(return_value="not_a_dict")

    with pytest.raises(ValueError, match="Device dev-1 not found in workspace ws-1"):
        await client.devices.get("ws-1", "dev-1")


@pytest.mark.asyncio
async def test_switching_endpoints_non_dict_responses() -> None:
    """Test switching get_lag, get_mc_lag_domain, get_switch_stack when response is not a dict."""
    client = UniFiNetworkClient(
        auth=ApiKeyAuth(api_key="test-key"),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    )
    client._get = AsyncMock(return_value="not_a_dict")

    with pytest.raises(ValueError, match="LAG lag-1 not found"):
        await client.switching.get_lag("site-1", "lag-1")

    with pytest.raises(ValueError, match="MC-LAG domain dom-1 not found"):
        await client.switching.get_mc_lag_domain("site-1", "dom-1")

    with pytest.raises(ValueError, match="Switch stack stack-1 not found"):
        await client.switching.get_switch_stack("site-1", "stack-1")


class _FakeWSMessage:
    def __init__(self, msg_type: aiohttp.WSMsgType, data: str = "") -> None:
        self.type = msg_type
        self.data = data


class _FakeWSEmpty:
    def __aiter__(self) -> _FakeWSEmpty:
        return self

    async def __anext__(self) -> _FakeWSMessage:
        raise StopAsyncIteration

    async def close(self) -> None:
        pass


class _FakeWSBinaryThenClose:
    def __init__(self) -> None:
        self._items = [
            _FakeWSMessage(aiohttp.WSMsgType.BINARY, "binary_data"),
            _FakeWSMessage(aiohttp.WSMsgType.CLOSED),
        ]

    def __aiter__(self) -> _FakeWSBinaryThenClose:
        return self

    async def __anext__(self) -> _FakeWSMessage:
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_protect_websocket_branches_devices_and_events() -> None:
    """Test protect websocket empty and binary branches (116->129, 123->116, 161->174, 168->161)."""
    protect_client = UniFiProtectClient(
        auth=ApiKeyAuth(api_key="test-key"),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    )
    ws_client = ProtectWebSocket(protect_client)

    # 1. Empty websocket iteration for subscribe_devices (116->129)
    ws_client._connect = AsyncMock(return_value=_FakeWSEmpty())
    async with ws_client.subscribe_devices("host-1", "site-1") as msgs:
        received = [m async for m in msgs]
        assert received == []

    # 2. Binary message followed by CLOSED for subscribe_devices (123->116)
    ws_client._connect = AsyncMock(return_value=_FakeWSBinaryThenClose())
    async with ws_client.subscribe_devices("host-1", "site-1") as msgs:
        received = [m async for m in msgs]
        assert received == []

    # 3. Empty websocket iteration for subscribe_events (161->174)
    ws_client._connect = AsyncMock(return_value=_FakeWSEmpty())
    async with ws_client.subscribe_events("host-1", "site-1") as msgs:
        received = [m async for m in msgs]
        assert received == []

    # 4. Binary message followed by CLOSED for subscribe_events (168->161)
    ws_client._connect = AsyncMock(return_value=_FakeWSBinaryThenClose())
    async with ws_client.subscribe_events("host-1", "site-1") as msgs:
        received = [m async for m in msgs]
        assert received == []
