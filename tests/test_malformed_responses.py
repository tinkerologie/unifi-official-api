"""Malformed list items, records and write echoes surface as library exceptions."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest

from unifi_official_api import ApiKeyAuth, ConnectionType, LocalAuth
from unifi_official_api.carrier_fabric import UniFiCarrierFabricClient
from unifi_official_api.exceptions import UniFiNotFoundError, UniFiResponseError
from unifi_official_api.innerspace import UniFiInnerSpaceClient
from unifi_official_api.mobility import UniFiMobilityClient
from unifi_official_api.network.client import UniFiNetworkClient
from unifi_official_api.protect import UniFiProtectClient
from unifi_official_api.site_manager import UniFiSiteManagerClient

SECRET = "do-not-leak-7f3a"
# A list item no model accepts: it is not an object, and it carries a value
# that must never reach a message.
BAD_ITEM = [SECRET]
SUBSCRIBER_ID = "123e4567-e89b-12d3-a456-426614174000"


def _network() -> UniFiNetworkClient:
    return UniFiNetworkClient(
        auth=ApiKeyAuth(api_key="key"),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    )


def _protect() -> UniFiProtectClient:
    return UniFiProtectClient(
        auth=ApiKeyAuth(api_key="key"),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    )


def _site_manager() -> UniFiSiteManagerClient:
    return UniFiSiteManagerClient(auth=ApiKeyAuth(api_key="key"), base_url="https://api.ui.com")


def _mobility() -> UniFiMobilityClient:
    return UniFiMobilityClient(auth=ApiKeyAuth(api_key="key"), base_url="https://api.ui.com")


def _innerspace() -> UniFiInnerSpaceClient:
    return UniFiInnerSpaceClient(
        auth=LocalAuth(api_key="key", verify_ssl=False),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    )


def _carrier_fabric() -> UniFiCarrierFabricClient:
    return UniFiCarrierFabricClient(auth=ApiKeyAuth(api_key="key"))


def _assert_sanitized(err: UniFiResponseError) -> None:
    """The error is a response error of a 2xx, with no trace of the rejected input."""
    assert not isinstance(err, UniFiNotFoundError)
    assert err.status_code == 200
    assert "failed validation" in err.message
    assert SECRET not in err.message
    assert err.__cause__ is None
    assert err.__context__ is None


Call = Callable[[Any], Awaitable[Any]]

# (factory, call) for every listing that cannot report a skipped item, so a
# malformed item fails the read. Each is answered {"data": [<good?>, BAD_ITEM]}.
_STRICT_LISTS: dict[str, tuple[Callable[[], Any], Call]] = {
    "network.wifi.get_all": (_network, lambda c: c.wifi.get_all("s")),
    "network.dns.get_all": (_network, lambda c: c.dns.get_all("s")),
    "network.networks.get_all": (_network, lambda c: c.networks.get_all("s")),
    "network.acl.get_all": (_network, lambda c: c.acl.get_all("s")),
    "network.firewall.list_zones": (_network, lambda c: c.firewall.list_zones("s")),
    "network.traffic.get_all_lists": (_network, lambda c: c.traffic.get_all_lists("s")),
    "network.traffic.get_dpi_categories": (_network, lambda c: c.traffic.get_dpi_categories()),
    "network.traffic.get_dpi_applications": (
        _network,
        lambda c: c.traffic.get_dpi_applications(),
    ),
    "network.traffic.get_countries": (_network, lambda c: c.traffic.get_countries()),
    "network.resources.get_wan_interfaces": (
        _network,
        lambda c: c.resources.get_wan_interfaces("s"),
    ),
    "network.resources.get_vpn_tunnels": (_network, lambda c: c.resources.get_vpn_tunnels("s")),
    "network.resources.get_vpn_servers": (_network, lambda c: c.resources.get_vpn_servers("s")),
    "network.resources.get_radius_profiles": (
        _network,
        lambda c: c.resources.get_radius_profiles("s"),
    ),
    "network.resources.get_device_tags": (_network, lambda c: c.resources.get_device_tags("s")),
    "network.lags.get_all": (_network, lambda c: c.lags.get_all("s")),
    "network.lags.get_all.page": (_network, lambda c: c.lags.get_all("s", limit=10)),
    "network.lags.get_mc_lag_domains": (_network, lambda c: c.lags.get_mc_lag_domains("s")),
    "network.switching.get_lags": (_network, lambda c: c.switching.get_lags("s")),
    "network.switching.get_mc_lag_domains": (
        _network,
        lambda c: c.switching.get_mc_lag_domains("s"),
    ),
    "network.switching.get_switch_stacks": (
        _network,
        lambda c: c.switching.get_switch_stacks("s"),
    ),
    "protect.liveviews.get_all": (_protect, lambda c: c.liveviews.get_all()),
    "protect.application.get_files": (_protect, lambda c: c.application.get_files()),
    "site_manager.hosts.get_all": (_site_manager, lambda c: c.hosts.get_all()),
    "site_manager.sites.get_all": (_site_manager, lambda c: c.sites.get_all()),
    "site_manager.devices.get_all": (_site_manager, lambda c: c.devices.get_all()),
    "site_manager.sd_wan.get_configs": (_site_manager, lambda c: c.sd_wan.get_configs()),
    "site_manager.isp_metrics.get_metrics": (
        _site_manager,
        lambda c: c.isp_metrics.get_metrics("5m"),
    ),
    "mobility.workspaces.get_all": (_mobility, lambda c: c.workspaces.get_all()),
    "mobility.workspaces.get_admins": (_mobility, lambda c: c.workspaces.get_admins("ws")),
    "mobility.devices.get_all": (_mobility, lambda c: c.devices.get_all("ws")),
    "mobility.clients.get_all": (_mobility, lambda c: c.clients.get_all("ws", "d")),
}


@pytest.mark.parametrize("name", list(_STRICT_LISTS))
async def test_list_with_malformed_item_raises_sanitized_response_error(name: str) -> None:
    """A listing without a completeness flag fails on a malformed item, never with pydantic's."""
    factory, call = _STRICT_LISTS[name]
    client = factory()
    client._get = AsyncMock(return_value={"data": [BAD_ITEM]})
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(client)
    _assert_sanitized(exc_info.value)


async def test_firewall_list_rules_skips_malformed_rule_by_field_name(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The lenient firewall policy read skips a malformed rule and logs field names only."""
    caplog.set_level(logging.DEBUG, logger="unifi_official_api.network.endpoints.firewall")
    client = _network()
    good = {"id": "r-1", "name": "Allow"}
    client._get = AsyncMock(return_value={"data": [{"id": "r-2", "name": [SECRET]}, good]})
    rules = await client.firewall.list_rules("s", limit=10)
    assert [rule.id for rule in rules] == ["r-1"]
    assert "Skipping invalid firewall policy item (ValidationError: name)" in caplog.text
    assert SECRET not in caplog.text


async def test_vpn_client_listing_skips_malformed_client_by_field_name(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The VPN client listing logs a skipped client by field name, never by value."""
    caplog.set_level(logging.DEBUG, logger="unifi_official_api.network.endpoints.vpn_clients")
    client = _network()
    client._get = AsyncMock(
        return_value={"data": [{"_id": "vpn-1", "purpose": "vpn-client", "name": [SECRET]}]}
    )
    assert await client.vpn_clients.list_vpn_clients("default") == []
    assert "Skipping invalid VPN client item (ValidationError: name)" in caplog.text
    assert SECRET not in caplog.text


# Greptile's example: the requested _id and purpose, but a name that is no string.
_BAD_VPN_CLIENT = {"_id": "vpn-1", "purpose": "vpn-client", "name": []}
_BAD_ROUTE = {"_id": "rt-1", "enabled": [SECRET]}


@pytest.mark.parametrize(
    ("call", "responses"),
    [
        (
            lambda c: c.vpn_clients.get_vpn_client("default", "vpn-1"),
            [{"data": [_BAD_VPN_CLIENT]}],
        ),
        (
            lambda c: c.vpn_clients.get_vpn_client("default", "vpn-1"),
            [{"data": []}, {"data": [{"_id": "lan", "purpose": "corporate"}, _BAD_VPN_CLIENT]}],
        ),
        (lambda c: c.routes.get_route("default", "rt-1"), [{"data": [_BAD_ROUTE]}]),
        (lambda c: c.routes.get_route("default", "rt-1"), [{"data": []}, {"data": [_BAD_ROUTE]}]),
    ],
    ids=["vpn-client-read", "vpn-client-listing", "route-read", "route-listing"],
)
async def test_legacy_getter_malformed_record_raises_sanitized_response_error(
    call: Call, responses: list[Any]
) -> None:
    """A malformed record found by a read or its listing fallback is malformed, not missing."""
    client = _network()
    client._get = AsyncMock(side_effect=responses)
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(client)
    _assert_sanitized(exc_info.value)
    assert client._get.await_count == len(responses)


@pytest.mark.parametrize(
    ("factory", "call", "method", "response"),
    [
        (
            _carrier_fabric,
            lambda c: c.service_plans.get("plan-1"),
            "_get",
            {"data": {"id": [SECRET]}},
        ),
        (
            _carrier_fabric,
            lambda c: c.subscribers.get(SUBSCRIBER_ID),
            "_get",
            {"data": {"id": [SECRET]}},
        ),
        (_innerspace, lambda c: c.project.get(), "_get", {"data": {"plans": [BAD_ITEM]}}),
        (
            _site_manager,
            lambda c: c.isp_metrics.query("5m", {"sites": []}),
            "_post",
            {"data": {"metrics": [BAD_ITEM]}},
        ),
    ],
    ids=["service_plans.get", "subscribers.get", "innerspace.project.get", "isp_metrics.query"],
)
async def test_record_read_malformed_raises_sanitized_response_error(
    factory: Callable[[], Any], call: Call, method: str, response: Any
) -> None:
    """A malformed record of a single-record read raises a sanitized response error."""
    client = factory()
    setattr(client, method, AsyncMock(return_value=response))
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(client)
    _assert_sanitized(exc_info.value)


_WIFI = {"id": "w-1", "name": "Guest", "enabled": True}
_RULE = {"id": "r-1", "name": "Allow", "enabled": True}
_ROUTE = {"_id": "rt-1", "description": "Route", "enabled": True}
_VPN = {"_id": "vpn-1", "purpose": "vpn-client", "name": "VPN", "enabled": True}

# (call, current record, malformed PUT echo) for each read-modify-write that
# re-fetches when the PUT echo is not a valid record.
_RMW: dict[str, tuple[Call, dict[str, Any], dict[str, Any]]] = {
    "wifi.update": (
        lambda c: c.wifi.update("s", "w-1", enabled=False),
        _WIFI,
        {"id": "w-1", "name": [SECRET]},
    ),
    "firewall.update_rule": (
        lambda c: c.firewall.update_rule("s", "r-1", enabled=False),
        _RULE,
        {"id": "r-1", "name": [SECRET]},
    ),
    "routes.update_route": (
        lambda c: c.routes.update_route("default", "rt-1", enabled=False),
        _ROUTE,
        {"_id": "rt-1", "enabled": [SECRET]},
    ),
    "vpn_clients.update_vpn_client": (
        lambda c: c.vpn_clients.update_vpn_client("default", "vpn-1", enabled=False),
        _VPN,
        {**_BAD_VPN_CLIENT, "name": [SECRET]},
    ),
}


@pytest.mark.parametrize("name", list(_RMW))
async def test_read_modify_write_malformed_echo_refetches(name: str) -> None:
    """A PUT echo that fails validation is an acknowledgement: the record is re-fetched."""
    call, current, echo = _RMW[name]
    updated = {**current, "enabled": False}
    client = _network()
    client._get = AsyncMock(side_effect=[{"data": [current]}, {"data": [updated]}])
    client._put = AsyncMock(return_value={"data": [echo]})
    result = await call(client)
    assert result == type(result).model_validate(updated)
    assert client._get.await_count == 2
    client._put.assert_awaited_once()


@pytest.mark.parametrize("name", list(_RMW))
async def test_read_modify_write_malformed_refetch_raises_sanitized_response_error(
    name: str,
) -> None:
    """When the re-fetched record fails validation too, a sanitized response error is raised."""
    call, current, echo = _RMW[name]
    client = _network()
    client._get = AsyncMock(side_effect=[{"data": [current]}, {"data": [echo]}])
    client._put = AsyncMock(return_value=None)
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(client)
    _assert_sanitized(exc_info.value)


@pytest.mark.parametrize(
    ("call", "current", "response"),
    [
        (
            lambda c: c.routes.update_route("default", "rt-1"),
            _ROUTE,
            {"data": [{"_id": "rt-other"}]},
        ),
        (
            lambda c: c.vpn_clients.update_vpn_client("default", "vpn-1"),
            _VPN,
            {"data": [{**_VPN, "_id": "vpn-other"}]},
        ),
    ],
    ids=["routes.update_route", "vpn_clients.update_vpn_client"],
)
async def test_read_modify_write_echo_of_another_record_refetches(
    call: Call, current: dict[str, Any], response: dict[str, Any]
) -> None:
    """A PUT echo that is not the written record is ignored and the record re-fetched."""
    client = _network()
    client._get = AsyncMock(side_effect=[{"data": [current]}, {"data": [current]}])
    client._put = AsyncMock(return_value=response)
    result = await call(client)
    assert result == type(result).model_validate(current)
    assert client._get.await_count == 2


# (call, the rule as listed) for the legacy rule toggles, which have no getter
# and return the record they sent when the PUT echo is not a valid record.
_TOGGLES: dict[str, tuple[Call, dict[str, Any]]] = {
    "static_routes": (
        lambda c: c.static_routes.update_static_route("default", "r-1", enabled=False),
        {"_id": "r-1", "name": "Route"},
    ),
    "nat_rules": (
        lambda c: c.nat_rules.update_nat_rule("default", "r-1", enabled=False),
        {"_id": "r-1", "description": "NAT"},
    ),
    "traffic_rules": (
        lambda c: c.traffic_rules.update_traffic_rule("default", "r-1", enabled=False),
        {"_id": "r-1", "description": "Rule"},
    ),
    "port_forwards": (
        lambda c: c.port_forwards.update_port_forward("default", "r-1", enabled=False),
        {"_id": "r-1", "name": "Forward"},
    ),
}


@pytest.mark.parametrize("name", list(_TOGGLES))
async def test_rule_toggle_malformed_echo_returns_sent_record(name: str) -> None:
    """A malformed PUT echo of the rule falls back to the record that was sent."""
    call, current = _TOGGLES[name]
    client = _network()
    client._get = AsyncMock(return_value={"data": [current]})
    echo = {"_id": "r-1", "name": [SECRET], "description": [SECRET]}
    client._put = AsyncMock(return_value={"data": [echo]})
    result = await call(client)
    assert result == type(result).model_validate({**current, "enabled": False})


@pytest.mark.parametrize("name", list(_TOGGLES))
async def test_rule_toggle_malformed_record_raises_sanitized_response_error(name: str) -> None:
    """When the sent record itself fails validation, a sanitized response error is raised."""
    call, _ = _TOGGLES[name]
    client = _network()
    bad = {"_id": "r-1", "name": [SECRET], "description": [SECRET]}
    client._get = AsyncMock(return_value={"data": [bad]})
    client._put = AsyncMock(return_value=None)
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(client)
    _assert_sanitized(exc_info.value)


async def test_arm_profile_update_malformed_listed_profile_is_not_reported_missing() -> None:
    """After an empty PATCH, a listed profile that fails validation is malformed, not missing."""
    client = _protect()
    client._patch = AsyncMock(return_value=None)
    client._get = AsyncMock(
        return_value={"data": [{"id": "prof-1", "name": [SECRET]}, {"id": "prof-2"}]}
    )
    with pytest.raises(UniFiResponseError) as exc_info:
        await client.arm_profiles.update("prof-1", name="Away")
    _assert_sanitized(exc_info.value)
    # get_all() would have dropped the profile and flagged the listing incomplete.
    assert [p.id for p in await client.arm_profiles.get_all()] == ["prof-2"]
    assert client.arm_profiles.last_result_complete is False


async def test_arm_profile_update_skips_non_dict_listing_items() -> None:
    """The listing fallback ignores items that are not objects."""
    client = _protect()
    client._patch = AsyncMock(return_value=None)
    client._get = AsyncMock(return_value={"data": ["junk", {"id": "prof-1", "name": "Away"}]})
    profile = await client.arm_profiles.update("prof-1", name="Away")
    assert profile.id == "prof-1"
    assert profile.name == "Away"


@pytest.mark.parametrize("name", list(_TOGGLES))
async def test_rule_toggle_missing_rule_is_not_found_with_status_200(name: str) -> None:
    """A listing without the rule is a successful answer with no record: not found, 200."""
    call, _ = _TOGGLES[name]
    client = _network()
    client._get = AsyncMock(return_value={"data": [{"_id": "other", "name": "Other"}]})
    client._put = AsyncMock()
    with pytest.raises(UniFiNotFoundError) as exc_info:
        await call(client)
    assert type(exc_info.value) is UniFiNotFoundError
    assert exc_info.value.status_code == 200
    client._put.assert_not_awaited()
