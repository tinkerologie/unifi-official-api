"""Guard: response records are validated through ``validation.py``, not directly."""

from __future__ import annotations

import ast
from pathlib import Path

import unifi_official_api

PACKAGE = Path(unifi_official_api.__file__).parent

# Every direct ``.model_validate(`` call outside ``validation.py``, keyed by
# (module path, enclosing function), with why its ValidationError cannot reach
# a caller. A new direct call fails this test: use ``parse_record``,
# ``parse_records``, ``require_record``, ``created_record`` or ``written_record``,
# or add an entry here with its reason.
ALLOWED: dict[tuple[str, str], str] = {
    ("access/models/common.py", "validate_record"): (
        "Access's own sanitizing helper: catches ValidationError, raises an Access response error"
    ),
    ("carrier_fabric/endpoints.py", "_parse_items"): (
        "listing helper: skips an item that fails validation, logging no content"
    ),
    ("carrier_fabric/endpoints.py", "_write_result"): (
        "write helper: catches ValidationError and returns None for an applied write"
    ),
    ("innerspace/client.py", "UniFiInnerSpaceClient._list_collection"): (
        "listing: catches ValidationError and skips the item"
    ),
    ("network/endpoints/clients.py", "ClientsEndpoint.get_all"): (
        "listing: catches the error and skips the item"
    ),
    ("network/endpoints/clients.py", "ClientsEndpoint._fetch_page"): (
        "listing page: catches the error and skips the item"
    ),
    ("network/endpoints/devices.py", "DevicesEndpoint.get_all"): (
        "listing: catches the error and skips the item"
    ),
    ("network/endpoints/devices.py", "DevicesEndpoint.get_pending_adoption"): (
        "listing: catches the error and skips the item"
    ),
    ("network/endpoints/firewall.py", "FirewallEndpoint._parse_rules_response"): (
        "lenient listing: catches ValidationError and skips the rule"
    ),
    ("network/endpoints/firewall.py", "FirewallEndpoint._parse_rules_strict"): (
        "strict listing: catches ValidationError, raises UniFiValidationError outside the handler"
    ),
    ("network/endpoints/firewall.py", "FirewallEndpoint.update_policy_ordering"): (
        "validates the caller's ordering argument before any request"
    ),
    ("network/endpoints/nat_rules.py", "NatRulesEndpoint._parse_strict"): (
        "strict listing: catches ValidationError, raises UniFiValidationError outside the handler"
    ),
    ("network/endpoints/nat_rules.py", "NatRulesEndpoint.list_nat_rules"): (
        "lenient listing: catches ValidationError and skips the rule"
    ),
    ("network/endpoints/port_forwards.py", "PortForwardsEndpoint._parse_strict"): (
        "strict listing: catches ValidationError, raises UniFiValidationError outside the handler"
    ),
    ("network/endpoints/port_forwards.py", "PortForwardsEndpoint.list_port_forwards"): (
        "lenient listing: catches ValidationError and skips the rule"
    ),
    ("network/endpoints/reports.py", "ReportsEndpoint.get_site_report"): (
        "listing: catches the error and skips the bucket"
    ),
    ("network/endpoints/routes.py", "RoutesEndpoint._parse_strict_routes"): (
        "strict listing: catches the error, raises UniFiValidationError outside the handler"
    ),
    ("network/endpoints/routes.py", "RoutesEndpoint.list_routes"): (
        "lenient listing: catches the error and skips the route"
    ),
    ("network/endpoints/sites.py", "SitesEndpoint.get_all"): (
        "listing: catches ValidationError and skips the site"
    ),
    ("network/endpoints/static_routes.py", "StaticRoutesEndpoint._parse_strict"): (
        "strict listing: catches ValidationError, raises UniFiValidationError outside the handler"
    ),
    ("network/endpoints/static_routes.py", "StaticRoutesEndpoint.list_static_routes"): (
        "lenient listing: catches ValidationError and skips the route"
    ),
    ("network/endpoints/traffic_rules.py", "TrafficRulesEndpoint._parse_strict"): (
        "strict listing: catches ValidationError, raises UniFiValidationError outside the handler"
    ),
    ("network/endpoints/traffic_rules.py", "TrafficRulesEndpoint.list_traffic_rules"): (
        "lenient listing: catches ValidationError and skips the rule"
    ),
    ("network/endpoints/vpn_clients.py", "VpnClientsEndpoint.list_vpn_clients"): (
        "lenient listing: catches ValidationError and skips the client"
    ),
    ("protect/endpoints/_base.py", "ProtectDeviceEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/alarm_hubs.py", "AlarmHubsEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/arm_profiles.py", "ArmProfilesEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/cameras.py", "CamerasEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/chimes.py", "ChimesEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/lights.py", "LightsEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/pos.py", "POSEndpoint.ingest_transaction"): (
        "validates the caller's transaction dict before any request"
    ),
    ("protect/endpoints/sensors.py", "SensorsEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/ulp_users.py", "UlpUsersEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/users.py", "UsersEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
    ("protect/endpoints/viewers.py", "ViewersEndpoint.get_all"): (
        "listing: skips the item and sets last_result_complete = False"
    ),
}


def _direct_calls() -> set[tuple[str, str]]:
    """Return (module path, enclosing function) of every direct ``.model_validate(`` call."""
    found: set[tuple[str, str]] = set()

    def visit(node: ast.AST, module: str, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                visit(child, module, (*scope, child.name))
                continue
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "model_validate"
            ):
                found.add((module, ".".join(scope) or "<module>"))
            visit(child, module, scope)

    for path in sorted(PACKAGE.rglob("*.py")):
        module = path.relative_to(PACKAGE).as_posix()
        if module != "validation.py":
            visit(ast.parse(path.read_text(encoding="utf-8")), module, ())
    return found


def test_no_unlisted_direct_model_validate_calls() -> None:
    """A direct ``.model_validate(`` call outside the allow-list fails the build."""
    unlisted = sorted(_direct_calls() - ALLOWED.keys())
    assert not unlisted, f"validate through unifi_official_api.validation instead: {unlisted}"


def test_allow_list_has_no_stale_entries() -> None:
    """Every allow-list entry still names a direct call, so the list stays exact."""
    stale = sorted(ALLOWED.keys() - _direct_calls())
    assert not stale, f"remove stale allow-list entries: {stale}"


def test_allow_list_entries_give_a_reason() -> None:
    """Each allow-list entry carries a one-line reason."""
    for site, reason in ALLOWED.items():
        assert reason.strip(), site
        assert "\n" not in reason, site
