"""Library exceptions for missing, malformed and write-acknowledging Network responses."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, Self

import pytest
from yarl import URL

from unifi_official_api import ApiKeyAuth, ConnectionType
from unifi_official_api.exceptions import UniFiNotFoundError, UniFiResponseError
from unifi_official_api.network.client import UniFiNetworkClient
from unifi_official_api.network.models.traffic import TrafficMatchingType

SECRET = "do-not-leak-7f3a"
BASE = "https://192.168.1.1/proxy/network/integration/v1/sites/default"


class _Response:
    """Minimal aiohttp response replacement."""

    def __init__(self, body: Any = None) -> None:
        self.status = 200
        self._body = body
        self.headers: dict[str, str] = {}
        self.url = URL("https://192.168.1.1")
        self.method = "GET"
        self.history = ()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def text(self) -> str:
        return "" if self._body is None else json.dumps(self._body)

    async def json(self) -> Any:
        return self._body


class _Session:
    """Mock session recording requests and returning queued responses."""

    closed = False

    def __init__(self, responses: list[Any]) -> None:
        self._responses = iter([_Response(r) for r in responses])
        self.requests: list[tuple[str, str]] = []

    def request(self, method: str, url: object, **kwargs: Any) -> _Response:
        self.requests.append((method, str(url).split("?")[0]))
        return next(self._responses)

    async def close(self) -> None:
        self.closed = True


def _client(session: _Session) -> UniFiNetworkClient:
    return UniFiNetworkClient(
        auth=ApiKeyAuth(api_key="test-key"),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
        session=session,  # type: ignore[arg-type]
    )


Call = Callable[[UniFiNetworkClient], Awaitable[Any]]
_ZONES = {"source_firewall_zone_id": "z-src", "destination_firewall_zone_id": "z-dst"}

# (name, call, path) for every single-record Network read.
_READS: list[tuple[str, Call, str]] = [
    ("devices.get", lambda c: c.devices.get("default", "d-1"), f"{BASE}/devices/d-1"),
    ("clients.get", lambda c: c.clients.get("default", "c-1"), f"{BASE}/clients/c-1"),
    ("networks.get", lambda c: c.networks.get("default", "n-1"), f"{BASE}/networks/n-1"),
    ("wifi.get", lambda c: c.wifi.get("default", "w-1"), f"{BASE}/wifi/broadcasts/w-1"),
    ("dns.get", lambda c: c.dns.get("default", "p-1"), f"{BASE}/dns/policies/p-1"),
    ("acl.get", lambda c: c.acl.get("default", "r-1"), f"{BASE}/acl-rules/r-1"),
    ("acl.get_ordering", lambda c: c.acl.get_ordering("default"), f"{BASE}/acl-rules/ordering"),
    (
        "firewall.get_zone",
        lambda c: c.firewall.get_zone("default", "z-1"),
        f"{BASE}/firewall/zones/z-1",
    ),
    (
        "firewall.get_rule",
        lambda c: c.firewall.get_rule("default", "r-1"),
        f"{BASE}/firewall/policies/r-1",
    ),
    (
        "firewall.get_policy_ordering",
        lambda c: c.firewall.get_policy_ordering("default", **_ZONES),
        f"{BASE}/firewall/policies/ordering",
    ),
    (
        "traffic.get_list",
        lambda c: c.traffic.get_list("default", "l-1"),
        f"{BASE}/traffic-matching-lists/l-1",
    ),
    ("lags.get", lambda c: c.lags.get("default", "lag-1"), f"{BASE}/switching/lags/lag-1"),
    (
        "lags.get_mc_lag_domain",
        lambda c: c.lags.get_mc_lag_domain("default", "m-1"),
        f"{BASE}/switching/mc-lag-domains/m-1",
    ),
    (
        "stacks.get",
        lambda c: c.stacks.get("default", "s-1"),
        f"{BASE}/switching/switch-stacks/s-1",
    ),
    (
        "switching.get_lag",
        lambda c: c.switching.get_lag("default", "lag-1"),
        f"{BASE}/switching/lags/lag-1",
    ),
    (
        "switching.get_mc_lag_domain",
        lambda c: c.switching.get_mc_lag_domain("default", "m-1"),
        f"{BASE}/switching/mc-lag-domains/m-1",
    ),
    (
        "switching.get_switch_stack",
        lambda c: c.switching.get_switch_stack("default", "s-1"),
        f"{BASE}/switching/switch-stacks/s-1",
    ),
    (
        "vouchers.get",
        lambda c: c.vouchers.get("default", "v-1"),
        f"{BASE}/hotspot/vouchers/v-1",
    ),
    (
        "get_application_info",
        lambda c: c.get_application_info(),
        "https://192.168.1.1/proxy/network/integration/v1/info",
    ),
]

# A record every Network model rejects: each field it may read is a list of dicts.
_MALFORMED_FIELDS = (
    "id",
    "name",
    "type",
    "macAddress",
    "applicationVersion",
    "orderedAclRuleIds",
    "orderedFirewallPolicyIds",
    "code",
    "members",
    "lags",
)
_MALFORMED = {key: [{"nested": [SECRET]}] for key in _MALFORMED_FIELDS}


@pytest.mark.parametrize("response", [None, {}, [], {"data": []}, {"data": {}}, {"data": "x"}])
@pytest.mark.parametrize(("name", "call", "path"), _READS, ids=[r[0] for r in _READS])
async def test_network_read_without_record_raises_not_found(
    name: str, call: Call, path: str, response: Any
) -> None:
    """A 2xx read whose body holds no record raises UniFiNotFoundError, status 200."""
    del name
    session = _Session([response])
    with pytest.raises(UniFiNotFoundError) as exc_info:
        await call(_client(session))
    assert exc_info.value.status_code == 200
    assert "not found" in exc_info.value.message
    assert session.requests == [("GET", path)]


@pytest.mark.parametrize("wrap", [False, True], ids=["bare", "data-list"])
@pytest.mark.parametrize(("name", "call", "path"), _READS, ids=[r[0] for r in _READS])
async def test_network_read_malformed_record_raises_sanitized_response_error(
    name: str, call: Call, path: str, wrap: bool
) -> None:
    """A malformed record raises UniFiResponseError naming fields, never values."""
    del name
    session = _Session([{"data": [_MALFORMED]} if wrap else _MALFORMED])
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(_client(session))
    err = exc_info.value
    assert not isinstance(err, UniFiNotFoundError)
    assert err.status_code == 200
    assert "failed validation" in err.message
    assert SECRET not in err.message
    assert err.__cause__ is None
    assert err.__context__ is None
    assert session.requests == [("GET", path)]


_ORDERING = {"beforeSystemDefined": ["p1"], "afterSystemDefined": ["p2"]}

# (name, call, write verb, write path, read path, record re-fetched by the read)
_WRITES: list[tuple[str, Call, str, str, str, dict[str, Any]]] = [
    (
        "acl.update",
        lambda c: c.acl.update("default", "r-1", name="x"),
        "PUT",
        f"{BASE}/acl-rules/r-1",
        f"{BASE}/acl-rules/r-1",
        {"id": "r-1", "type": "IPV4", "name": "x", "action": "ALLOW", "enabled": True},
    ),
    (
        "acl.update_ordering",
        lambda c: c.acl.update_ordering("default", ordered_rule_ids=["r-1"]),
        "PUT",
        f"{BASE}/acl-rules/ordering",
        f"{BASE}/acl-rules/ordering",
        {"orderedAclRuleIds": ["r-1"]},
    ),
    (
        "firewall.update_zone",
        lambda c: c.firewall.update_zone("default", "z-1", name="x"),
        "PUT",
        f"{BASE}/firewall/zones/z-1",
        f"{BASE}/firewall/zones/z-1",
        {"id": "z-1", "name": "x"},
    ),
    (
        "firewall.patch_rule",
        lambda c: c.firewall.patch_rule("default", "r-1", logging_enabled=True),
        "PATCH",
        f"{BASE}/firewall/policies/r-1",
        f"{BASE}/firewall/policies/r-1",
        {"id": "r-1", "name": "x", "loggingEnabled": True},
    ),
    (
        "firewall.update_policy_ordering",
        lambda c: c.firewall.update_policy_ordering(
            "default", ordered_firewall_policy_ids=_ORDERING, **_ZONES
        ),
        "PUT",
        f"{BASE}/firewall/policies/ordering",
        f"{BASE}/firewall/policies/ordering",
        {"orderedFirewallPolicyIds": _ORDERING},
    ),
    (
        "dns.update",
        lambda c: c.dns.update("default", "p-1", enabled=False),
        "PUT",
        f"{BASE}/dns/policies/p-1",
        f"{BASE}/dns/policies/p-1",
        {"id": "p-1", "type": "A_RECORD", "enabled": False},
    ),
    (
        "networks.update",
        lambda c: c.networks.update("default", "n-1", name="x"),
        "PUT",
        f"{BASE}/networks/n-1",
        f"{BASE}/networks/n-1",
        {"id": "n-1", "name": "x"},
    ),
    (
        "traffic.update_list",
        lambda c: c.traffic.update_list("default", "l-1", name="x"),
        "PUT",
        f"{BASE}/traffic-matching-lists/l-1",
        f"{BASE}/traffic-matching-lists/l-1",
        {"id": "l-1", "name": "x", "type": "PORTS"},
    ),
]


@pytest.mark.parametrize("written", [None, {"data": []}, {"data": {}}, {"data": "x"}])
@pytest.mark.parametrize(
    ("name", "call", "verb", "write_path", "read_path", "record"),
    _WRITES,
    ids=[w[0] for w in _WRITES],
)
async def test_network_write_without_record_refetches(
    name: str,
    call: Call,
    verb: str,
    write_path: str,
    read_path: str,
    record: dict[str, Any],
    written: Any,
) -> None:
    """A successful write acknowledged without the record is re-fetched, not failed."""
    del name
    session = _Session([written, {"data": record}])
    result = await call(_client(session))
    assert result == type(result).model_validate(record)
    assert session.requests == [(verb, write_path), ("GET", read_path)]


@pytest.mark.parametrize(
    ("name", "call", "verb", "write_path", "read_path", "record"),
    _WRITES,
    ids=[w[0] for w in _WRITES],
)
async def test_network_write_refetch_finding_nothing_raises_not_found(
    name: str,
    call: Call,
    verb: str,
    write_path: str,
    read_path: str,
    record: dict[str, Any],
) -> None:
    """When neither the write nor the re-fetch holds the record, it is not found."""
    del name, record
    session = _Session([None, {"data": []}])
    with pytest.raises(UniFiNotFoundError) as exc_info:
        await call(_client(session))
    assert exc_info.value.status_code == 200
    assert session.requests == [(verb, write_path), ("GET", read_path)]


# (name, call, path) for every create whose response must hold the new record.
_CREATES: list[tuple[str, Call, str]] = [
    (
        "acl.create",
        lambda c: c.acl.create("default", name="x"),
        f"{BASE}/acl-rules",
    ),
    (
        "firewall.create_zone",
        lambda c: c.firewall.create_zone("default", name="x"),
        f"{BASE}/firewall/zones",
    ),
    (
        "firewall.create_rule",
        lambda c: c.firewall.create_rule(
            "default", name="x", action="ALLOW", source_zone_id="a", destination_zone_id="b"
        ),
        f"{BASE}/firewall/policies",
    ),
    (
        "dns.create",
        lambda c: c.dns.create("default", record_type="A_RECORD", domain="x.local"),
        f"{BASE}/dns/policies",
    ),
    ("networks.create", lambda c: c.networks.create("default", name="x"), f"{BASE}/networks"),
    (
        "traffic.create_list",
        lambda c: c.traffic.create_list(
            "default", name="x", list_type=TrafficMatchingType.PORTS, entries=["80"]
        ),
        f"{BASE}/traffic-matching-lists",
    ),
    (
        "wifi.create",
        lambda c: c.wifi.create("default", name="x", ssid="x", passphrase="secret-pass"),
        f"{BASE}/wifi/broadcasts",
    ),
    (
        "vouchers.create",
        lambda c: c.vouchers.create("default", count=1, name="x", time_limit_minutes=60),
        f"{BASE}/hotspot/vouchers",
    ),
]


@pytest.mark.parametrize("response", [None, {"data": []}, {"data": {}}, {"data": "x"}])
@pytest.mark.parametrize(("name", "call", "path"), _CREATES, ids=[c[0] for c in _CREATES])
async def test_network_create_without_record_raises_response_error(
    name: str, call: Call, path: str, response: Any
) -> None:
    """A create whose response holds no record cannot be re-fetched, so it is reported."""
    del name
    session = _Session([response])
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(_client(session))
    err = exc_info.value
    assert not isinstance(err, UniFiNotFoundError)
    assert err.status_code == 200
    assert "may have been created" in err.message
    assert session.requests == [("POST", path)]


@pytest.mark.parametrize(("name", "call", "path"), _CREATES, ids=[c[0] for c in _CREATES])
async def test_network_create_malformed_record_raises_sanitized_response_error(
    name: str, call: Call, path: str
) -> None:
    """A created record that fails validation names fields, never values."""
    del name
    session = _Session([{"data": _MALFORMED}])
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(_client(session))
    err = exc_info.value
    assert err.status_code == 200
    assert SECRET not in err.message
    assert err.__cause__ is None
    assert err.__context__ is None
    assert session.requests == [("POST", path)]


@pytest.mark.parametrize(
    ("call", "responses", "requests"),
    [
        (
            lambda c: c.wifi.update("default", "w-1", name="x"),
            [{"data": {}}],
            [("GET", f"{BASE}/wifi/broadcasts/w-1")],
        ),
        (
            lambda c: c.firewall.update_rule("default", "r-1", name="x"),
            [{"data": []}],
            [("GET", f"{BASE}/firewall/policies/r-1")],
        ),
    ],
    ids=["wifi.update", "firewall.update_rule"],
)
async def test_network_read_modify_write_without_record_raises_not_found(
    call: Call, responses: list[Any], requests: list[tuple[str, str]]
) -> None:
    """A read-modify-write whose read holds no record raises before writing."""
    session = _Session(responses)
    with pytest.raises(UniFiNotFoundError) as exc_info:
        await call(_client(session))
    assert exc_info.value.status_code == 200
    assert session.requests == requests
