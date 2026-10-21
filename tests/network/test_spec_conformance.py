"""
Guard: every Integration API request the Network package sends is in the pinned spec.

The spec is vendored at ``tests/fixtures/network_openapi_<version>.json``,
downloaded from ``https://developer.ui.com/network/v<version>/openapi.json`` where
``<version>`` is ``NETWORK_SPEC_VERSION``, so the guard runs offline. The only
change to the download is a trailing newline. To move to a new spec version,
download the new document, delete the old one, and bump ``NETWORK_SPEC_VERSION``
in the same change.

Every public coroutine on the client, and on each endpoint the client exposes,
is called against a recording transport. The transport records the HTTP method
and path of each request, then stops the call. Every Integration API operation
must exist in the spec. Requests to the legacy controller API (``/api`` and
``/v2/api``) are outside the spec by design, so only the methods listed in
``LEGACY`` may send them. Every method must send at least one request, and every
path-builder call site in the package must be reached, so a new method or call
site cannot slip past the guard.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest

import unifi_official_api.network as network_pkg
from unifi_official_api import ApiKeyAuth, ConnectionType, LocalAuth
from unifi_official_api.const import NETWORK_SPEC_VERSION
from unifi_official_api.network import UniFiNetworkClient
from unifi_official_api.network.models import TrafficMatchingType

SPEC_PATH = (
    Path(__file__).parent.parent / "fixtures" / f"network_openapi_{NETWORK_SPEC_VERSION}.json"
)
PACKAGE_DIR = Path(network_pkg.__file__).parent
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})
PATH_BUILDERS = frozenset(
    {
        "build_api_path",
        "build_legacy_api_path",
        "build_legacy_global_api_path",
        "build_legacy_v2_api_path",
    }
)

# Arguments for required parameters, keyed by parameter name. Any other required
# parameter gets an ID such as ``id-device-id``, which can never equal a literal
# path segment such as ``ordering`` or ``actions``.
ARGUMENTS: dict[str, Any] = {
    "action": "RESTART",
    "enabled": True,
    "interval": "hourly",
    "list_type": TrafficMatchingType.PORTS,
    "logging_enabled": True,
    "mac": "aa:bb:cc:dd:ee:ff",
    "macs": ["aa:bb:cc:dd:ee:ff"],
    "ordered_firewall_policy_ids": {"beforeSystemDefined": [], "afterSystemDefined": []},
    "ordered_rule_ids": ["id-rule"],
    "outlet_index": 1,
    "port_idx": 1,
    "record_type": "A_RECORD",
    "site_name": "default",
    "state": True,
    "time_limit_minutes": 60,
    "voucher_ids": ["id-voucher"],
}
# Per-method arguments where the generic ones would fail validation first.
OVERRIDES: dict[str, dict[str, Any]] = {
    "client.get_site_report": {"start_ms": 0, "end_ms": 1},
    "reports.get_site_report": {"start_ms": 0, "end_ms": 1},
    "clients.execute_action": {"action": "block"},
    "devices.execute_port_action": {"action": "POWER_CYCLE"},
    "devices.set_outlet_state": {"current_device": {"outlet_table": [{"index": 1}]}},
    "dns.create": {"domain": "example.com", "ipv4_address": "192.0.2.1"},
    "firewall.create_rule": {"source_zone_id": "id-zone", "destination_zone_id": "id-zone"},
    "traffic.create_list": {"entries": ["443"]},
    "wifi.create": {"ssid": "id-name", "passphrase": "passphrase"},
}
# Responses for methods that read before they write; the write is what matters.
STAGED_RESPONSES: dict[str, list[Any]] = {
    "firewall.update_rule": [{"id": "id-rule-id", "name": "rule"}],
    "wifi.update": [{"id": "id-wifi-id", "name": "wifi"}],
}
# Public coroutines that never send a request.
NO_REQUEST = frozenset({"client.close"})
# Public coroutines that call another API: Site Manager owns ``GET /v1/hosts``.
OTHER_API = frozenset({"client.get_hosts"})
# Public coroutines that call the legacy controller API, which the Integration
# API spec does not document. Keep this list in sync with the package.
LEGACY = frozenset(
    {
        "client.get_site_report",
        "clients.block",
        "clients.execute_action",
        "clients.forget",
        "clients.forget_batch",
        "clients.get_active_legacy",
        "clients.get_historical_legacy",
        "clients.reconnect",
        "clients.unblock",
        "devices.get_legacy_device_stats",
        "devices.get_legacy_site_devices",
        "devices.get_outlet_metrics",
        "devices.get_port_metrics",
        "devices.set_outlet_state",
        "nat_rules.list_nat_rules",
        "nat_rules.update_nat_rule",
        "networks.get_legacy_all",
        "port_forwards.list_port_forwards",
        "port_forwards.update_port_forward",
        "reports.get_site_report",
        "routes.get_route",
        "routes.list_routes",
        "routes.update_route",
        "sites.get_legacy_all",
        "static_routes.list_static_routes",
        "static_routes.update_static_route",
        "traffic_rules.list_traffic_rules",
        "traffic_rules.update_traffic_rule",
        "vpn_clients.get_vpn_client",
        "vpn_clients.list_site_to_site_vpns",
        "vpn_clients.list_vpn_clients",
        "vpn_clients.list_vpn_connections",
        "vpn_clients.update_vpn_client",
        "wifi.get_legacy_configs",
    }
)


class _RequestSentError(Exception):
    """Raised by the recording transport to stop a call once it has sent a request."""


class Operation(NamedTuple):
    """
    An HTTP operation.

    An Integration API path is in the spec's ``/v1/...`` form; a legacy controller
    API path is kept as sent, with ``legacy`` set.
    """

    method: str
    path: str
    legacy: bool = False


def _load_spec() -> dict[str, Any]:
    spec: dict[str, Any] = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    return spec


def _spec_operations() -> list[tuple[re.Pattern[str], str, frozenset[str]]]:
    operations = []
    for template, item in _load_spec()["paths"].items():
        pattern = re.compile("^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(template)) + "$")
        operations.append((pattern, template, frozenset(k for k in item if k in HTTP_METHODS)))
    return operations


SPEC_OPERATIONS = _spec_operations()


def _spec_template(operation: Operation) -> str | None:
    """
    Return the spec path template documenting ``operation``, or None.

    A path matching several templates belongs to the one with the fewest
    parameters, so ``/acl-rules/ordering`` is never read as ``/acl-rules/{id}``.
    """
    matches = [
        (template.count("{"), template, methods)
        for pattern, template, methods in SPEC_OPERATIONS
        if pattern.match(operation.path)
    ]
    if not matches:
        return None
    _parameters, template, methods = min(matches)
    return template if operation.method in methods else None


class Recorder:
    """Recording transport installed on a client."""

    def __init__(self, client: UniFiNetworkClient) -> None:
        self.operations: list[Operation] = []
        self.call_sites: set[tuple[str, str]] = set()
        self.staged: list[Any] = []
        self._prefix = client.build_api_path("/")
        self._legacy_prefixes = (
            client.build_legacy_global_api_path("/"),
            client.build_legacy_v2_api_path("default", "/").removesuffix("site/default/"),
        )
        for name in PATH_BUILDERS:
            setattr(client, name, self._recording_builder(getattr(client, name)))

        async def request(method: str, path: str, **_kwargs: Any) -> Any:
            return self._record(method, path)

        client._request = request  # type: ignore[method-assign]

    def _recording_builder(self, build: Callable[..., str]) -> Callable[..., str]:
        def builder(*args: Any) -> str:
            code = sys._getframe(1).f_code
            module = Path(code.co_filename).relative_to(PACKAGE_DIR).as_posix()
            self.call_sites.add((module, code.co_qualname))
            return build(*args)

        return builder

    def _record(self, method: str, path: str) -> Any:
        if path.startswith(self._prefix):
            operation = Operation(method.lower(), "/v1/" + path.removeprefix(self._prefix))
        else:
            assert path.startswith(self._legacy_prefixes), path
            operation = Operation(method.lower(), path, legacy=True)
        self.operations.append(operation)
        if self.staged:
            return self.staged.pop(0)
        raise _RequestSentError


def _make_client(connection_type: ConnectionType) -> UniFiNetworkClient:
    if connection_type == ConnectionType.LOCAL:
        return UniFiNetworkClient(auth=LocalAuth(api_key="key"), base_url="https://console")
    return UniFiNetworkClient(
        auth=ApiKeyAuth(api_key="key"),
        connection_type=ConnectionType.REMOTE,
        console_id="id-console",
    )


def _public_targets(client: UniFiNetworkClient) -> Iterator[tuple[str, Callable[..., Any]]]:
    """Yield every public coroutine on the client surface."""
    owners: list[tuple[str, object]] = [("client", client)]
    for name, attr in inspect.getmembers(type(client)):
        if isinstance(attr, property) and not name.startswith("_"):
            owners.append((name, getattr(client, name)))
    for owner_name, owner in owners:
        for name, member in inspect.getmembers(owner, inspect.ismethod):
            if not name.startswith("_") and inspect.iscoroutinefunction(inspect.unwrap(member)):
                yield f"{owner_name}.{name}", member


def _arguments(target: str, function: Callable[..., Any]) -> tuple[list[Any], dict[str, Any]]:
    """Return arguments for every required parameter, plus the target's overrides."""
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    overrides = dict(OVERRIDES.get(target, {}))
    for parameter in inspect.signature(function).parameters.values():
        if parameter.kind is parameter.VAR_KEYWORD:
            if not overrides:
                kwargs.setdefault("name", "renamed")
            continue
        if parameter.default is not parameter.empty:
            continue
        value = overrides.pop(
            parameter.name,
            ARGUMENTS.get(parameter.name, f"id-{parameter.name.replace('_', '-')}"),
        )
        if parameter.kind is parameter.KEYWORD_ONLY:
            kwargs[parameter.name] = value
        else:
            args.append(value)
    return args, {**kwargs, **overrides}


async def _exercise(client: UniFiNetworkClient) -> tuple[Recorder, dict[str, list[Operation]]]:
    """Call every public target once and return what each one sent."""
    recorder = Recorder(client)
    sent: dict[str, list[Operation]] = {}
    for name, target in _public_targets(client):
        if name in NO_REQUEST | OTHER_API:
            continue
        before = len(recorder.operations)
        recorder.staged = list(STAGED_RESPONSES.get(name, []))
        with pytest.raises(_RequestSentError):
            args, kwargs = _arguments(name, target)
            await target(*args, **kwargs)
        sent[name] = recorder.operations[before:]
    return recorder, sent


def _ast_call_sites() -> set[tuple[str, str]]:
    """Return (module, qualified function) for every path-builder call in the package."""
    sites: set[tuple[str, str]] = set()

    def visit(node: ast.AST, module: str, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                visit(child, module, (*scope, child.name))
                continue
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr in PATH_BUILDERS
            ):
                sites.add((module, ".".join(scope)))
            visit(child, module, scope)

    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        visit(tree, path.relative_to(PACKAGE_DIR).as_posix(), ())
    return sites


def test_vendored_spec_is_the_pinned_version() -> None:
    """The vendored spec file matches NETWORK_SPEC_VERSION and has operations."""
    assert SPEC_PATH.is_file(), f"Vendor the Network {NETWORK_SPEC_VERSION} spec at {SPEC_PATH}"
    assert _load_spec()["info"]["version"] == NETWORK_SPEC_VERSION
    assert len(SPEC_OPERATIONS) > 1


@pytest.mark.parametrize("connection_type", [ConnectionType.LOCAL, ConnectionType.REMOTE])
async def test_every_network_request_is_in_the_spec(connection_type: ConnectionType) -> None:
    """Every public Network method sends only Integration API operations the spec documents."""
    _recorder, sent = await _exercise(_make_client(connection_type))

    off_spec = {
        name: [
            f"{op.method.upper()} {op.path}"
            for op in ops
            if not op.legacy and _spec_template(op) is None
        ]
        for name, ops in sent.items()
    }
    assert {name: ops for name, ops in off_spec.items() if ops} == {}
    assert len(sent) > 100


@pytest.mark.parametrize("connection_type", [ConnectionType.LOCAL, ConnectionType.REMOTE])
async def test_only_listed_methods_call_the_legacy_api(connection_type: ConnectionType) -> None:
    """LEGACY names exactly the public methods that send legacy controller API requests."""
    _recorder, sent = await _exercise(_make_client(connection_type))

    legacy = {name for name, ops in sent.items() if any(op.legacy for op in ops)}
    assert legacy == LEGACY


async def test_guard_reaches_every_path_builder_call_site() -> None:
    """The exercise run reaches every path-builder call site in the package."""
    recorder, _sent = await _exercise(_make_client(ConnectionType.LOCAL))

    assert recorder.call_sites == _ast_call_sites()


async def test_multi_request_methods_send_their_write() -> None:
    """Methods that read before writing are recorded through to the write."""
    _recorder, sent = await _exercise(_make_client(ConnectionType.LOCAL))

    assert sent["wifi.update"] == [
        Operation("get", "/v1/sites/id-site-id/wifi/broadcasts/id-wifi-id"),
        Operation("put", "/v1/sites/id-site-id/wifi/broadcasts/id-wifi-id"),
    ]
    assert sent["firewall.update_rule"] == [
        Operation("get", "/v1/sites/id-site-id/firewall/policies/id-rule-id"),
        Operation("put", "/v1/sites/id-site-id/firewall/policies/id-rule-id"),
    ]


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (Operation("get", "/v1/sites"), "/v1/sites"),
        (Operation("get", "/v1/sites/{siteId}/devices"), "/v1/sites/{siteId}/devices"),
        (
            Operation("get", "/v1/sites/id-site/devices/id-device"),
            "/v1/sites/{siteId}/devices/{deviceId}",
        ),
        (
            Operation("put", "/v1/sites/id-site/acl-rules/ordering"),
            "/v1/sites/{siteId}/acl-rules/ordering",
        ),
        (Operation("delete", "/v1/sites/id-site/acl-rules/ordering"), None),
        (Operation("patch", "/v1/sites/id-site/networks/id-network"), None),
        (Operation("post", "/v1/sites"), None),
        (Operation("get", "/v1/sites/id-site/devices/id-device/extra"), None),
    ],
)
def test_spec_matcher(operation: Operation, expected: str | None) -> None:
    """The matcher accepts documented operations and rejects undocumented ones."""
    assert _spec_template(operation) == expected
