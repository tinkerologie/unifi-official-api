"""Enum-or-``str`` model fields validate known values into their ``StrEnum``.

Pydantic's smart union keeps a ``str`` input as a plain ``str`` because it is an
exact match, so the enum branch of ``SomeStrEnum | str`` never ran and the
case-normalising ``_missing_`` hooks never applied (#70). Every such field now
carries ``union_mode="left_to_right"``; these tests fail if that regresses.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import types
import typing
from collections.abc import Iterator
from enum import StrEnum
from typing import Any, NamedTuple, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

import unifi_official_api
from unifi_official_api.innerspace.models.access_point import (
    InnerSpaceAccessPoint,
    InnerSpaceMountType,
)
from unifi_official_api.network.models.acl import (
    ACLAction,
    ACLMetadata,
    ACLProtocol,
    ACLRule,
    ACLRuleType,
    MetadataOrigin,
)
from unifi_official_api.network.models.client import Client, ClientType
from unifi_official_api.network.models.device import Device, DeviceState, DeviceType
from unifi_official_api.network.models.dns import DNSPolicy, DNSPolicyType
from unifi_official_api.network.models.firewall import (
    FirewallAction,
    FirewallActionConfig,
    FirewallRule,
)
from unifi_official_api.network.models.lag import LAG, LagType, McLagPeer, McLagRole
from unifi_official_api.network.models.resources import (
    VPNServer,
    VPNServerType,
    VPNTunnel,
    VPNTunnelStatus,
    WANInterface,
    WANStatus,
)
from unifi_official_api.network.models.site import Site, SiteHealth
from unifi_official_api.network.models.stack import SwitchStackUnit, SwitchStackUnitRole
from unifi_official_api.network.models.wifi import WifiNetwork, WifiSecurity
from unifi_official_api.protect.models.camera import Camera, RecordingMode, VideoMode
from unifi_official_api.protect.models.event import Event, EventType
from unifi_official_api.protect.models.ulp_user import UlpUser, UlpUserStatus


class Case(NamedTuple):
    """One enum-or-``str`` field and the values it must accept."""

    model: type[BaseModel]
    payload: dict[str, Any]
    key: str
    known: str
    expected: StrEnum
    unknown: str = "FUTURE_FIRMWARE_VALUE"
    lower: str | None = None
    lower_expected: StrEnum | None = None


CASES = sorted(
    [
        Case(ACLMetadata, {}, "origin", "USER_DEFINED", MetadataOrigin.USER_DEFINED),
        Case(ACLRule, {"name": "rule"}, "action", "ALLOW", ACLAction.ALLOW),
        Case(ACLRule, {"name": "rule", "action": "ALLOW"}, "type", "IPV4", ACLRuleType.IPV4),
        Case(
            Client,
            {"id": "client"},
            "type",
            "WIRED",
            ClientType.WIRED,
            lower="wired",
            lower_expected=ClientType.WIRED,
        ),
        Case(Device, {"id": "device"}, "state", "ONLINE", DeviceState.ONLINE),
        Case(Device, {"id": "device"}, "type", "usw", DeviceType.USW),
        Case(
            DNSPolicy,
            {},
            "type",
            "A_RECORD",
            DNSPolicyType.A_RECORD,
            lower="a_record",
            lower_expected=DNSPolicyType.A_RECORD,
        ),
        Case(
            FirewallActionConfig,
            {},
            "type",
            "ALLOW",
            FirewallAction.ALLOW,
            lower="block",
            lower_expected=FirewallAction.BLOCK,
        ),
        Case(LAG, {"id": "lag"}, "type", "LOCAL", LagType.LOCAL),
        Case(McLagPeer, {}, "role", "TOP", McLagRole.TOP),
        Case(VPNServer, {"id": "server"}, "type", "WIREGUARD", VPNServerType.WIREGUARD),
        Case(VPNTunnel, {"id": "tunnel"}, "status", "UP", VPNTunnelStatus.UP),
        Case(
            WANInterface,
            {"id": "wan", "name": "WAN"},
            "status",
            "UP",
            WANStatus.UP,
        ),
        Case(Site, {}, "health", "healthy", SiteHealth.HEALTHY),
        Case(
            WifiNetwork,
            {"id": "wifi", "name": "WiFi"},
            "security",
            "wpa2",
            WifiSecurity.WPA2,
        ),
        Case(
            SwitchStackUnit,
            {"id": 1, "macAddress": "00:00:00:00:00:01"},
            "role",
            "MEMBER",
            SwitchStackUnitRole.MEMBER,
            lower="member",
            lower_expected=SwitchStackUnitRole.MEMBER,
        ),
        Case(
            Camera,
            {"id": "camera", "mac": "00:00:00:00:00:02"},
            "recording_mode",
            "always",
            RecordingMode.ALWAYS,
        ),
        Case(
            Camera,
            {"id": "camera", "mac": "00:00:00:00:00:02"},
            "video_mode",
            "default",
            VideoMode.DEFAULT,
        ),
        Case(Event, {"id": "event"}, "type", "motion", EventType.MOTION),
        Case(
            UlpUser,
            {
                "id": "user",
                "firstName": "Ada",
                "lastName": "Lovelace",
                "fullName": "Ada Lovelace",
            },
            "status",
            "ACTIVE",
            UlpUserStatus.ACTIVE,
        ),
        Case(
            InnerSpaceAccessPoint,
            {"id": "access-point"},
            "mount_type",
            "CEILING",
            InnerSpaceMountType.CEILING,
            lower="ceiling",
            lower_expected=InnerSpaceMountType.CEILING,
        ),
    ],
    key=lambda case: (case.model.__name__, case.key),
)


def _case_id(case: Case) -> str:
    return f"{case.model.__name__}.{case.key}"


LOWERCASE_CASES = [case for case in CASES if case.lower is not None]

NULLABLE_CASES = [
    (Camera, {"id": "camera", "mac": "00:00:00:00:00:02"}, "recording_mode"),
    (Device, {"id": "device"}, "state"),
    (SwitchStackUnit, {"id": 1, "macAddress": "00:00:00:00:00:01"}, "role"),
]


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_known_value_becomes_the_enum_member(case: Case) -> None:
    """A value the enum knows is an enum member, not a plain string."""
    parsed = case.model.model_validate({**case.payload, case.key: case.known})

    value = getattr(parsed, case.key)

    assert value is case.expected


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_unknown_value_stays_a_plain_str(case: Case) -> None:
    """A value from newer firmware still parses, as the raw string."""
    parsed = case.model.model_validate({**case.payload, case.key: case.unknown})

    value = getattr(parsed, case.key)

    assert type(value) is str
    assert value == case.unknown


@pytest.mark.parametrize("case", LOWERCASE_CASES, ids=_case_id)
def test_lowercase_value_is_normalised_by_the_missing_hook(case: Case) -> None:
    """The ``_missing_`` hooks run during validation and canonicalise case."""
    parsed = case.model.model_validate({**case.payload, case.key: case.lower})

    assert getattr(parsed, case.key) is case.lower_expected


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_an_existing_enum_member_is_preserved(case: Case) -> None:
    """An enum member input keeps its identity instead of being re-created."""
    parsed = case.model.model_validate({**case.payload, case.key: case.expected})

    assert getattr(parsed, case.key) is case.expected


@pytest.mark.parametrize(
    ("model", "payload", "key"),
    NULLABLE_CASES,
    ids=[f"{model.__name__}.{key}" for model, _, key in NULLABLE_CASES],
)
def test_nullable_field_accepts_none_and_omitted(
    model: type[BaseModel], payload: dict[str, Any], key: str
) -> None:
    """An explicit ``None`` and an omitted field both give ``None``."""
    assert getattr(model.model_validate({**payload, key: None}), key) is None
    assert getattr(model.model_validate(payload), key) is None


def test_defaults_are_enum_members() -> None:
    """Typed defaults stay enum members."""
    assert Site.model_validate({}).health is SiteHealth.UNKNOWN
    assert ACLRule.model_validate({"name": "rule", "action": "ALLOW"}).type is ACLRuleType.IPV4
    assert FirewallActionConfig().type is FirewallAction.BLOCK


def test_protocol_filter_elements_follow_the_same_rule() -> None:
    """The list element union, not the list field, carries the union mode."""
    rule = ACLRule.model_validate(
        {
            "name": "rule",
            "action": "ALLOW",
            "protocolFilter": ["TCP", "tcp", "SCTP"],
        }
    )

    known, unknown_case, unknown_protocol = rule.protocol_filter

    assert known is ACLProtocol.TCP
    assert type(unknown_case) is str
    assert type(unknown_protocol) is str


def test_model_dump_keeps_members_and_json_keeps_strings() -> None:
    """Python mode dumps the member; JSON mode and JSON text stay strings."""
    rule = ACLRule.model_validate({"name": "rule", "action": "ALLOW", "type": "MAC"})

    assert rule.action is ACLAction.ALLOW
    assert rule.model_dump()["action"] is ACLAction.ALLOW
    assert rule.model_dump()["action"] == "ALLOW"
    assert type(rule.model_dump(mode="json")["action"]) is str
    assert rule.model_dump(mode="json")["action"] == "ALLOW"
    assert json.loads(rule.model_dump_json())["action"] == "ALLOW"


def test_serialisation_keeps_aliases() -> None:
    """``by_alias=True`` still writes the API's camelCase keys."""
    camera = Camera.model_validate(
        {"id": "camera", "mac": "00:00:00:00:00:02", "recordingMode": "always"}
    )
    access_point = InnerSpaceAccessPoint.model_validate(
        {"id": "access-point", "mountType": "CEILING"}
    )

    assert camera.recording_mode is RecordingMode.ALWAYS
    assert camera.model_dump(by_alias=True)["recordingMode"] is RecordingMode.ALWAYS
    assert access_point.model_dump(by_alias=True)["mountType"] == "CEILING"


# ``FirewallRule.action`` is the structural exception: it is a four-branch union
# (``FirewallAction | FirewallActionConfig | dict[str, Any] | str``) whose dict
# representation must not change, so it is normalised by a before-validator
# instead of ``union_mode`` (see ``test_firewall_rule_action_*`` below, which
# characterise the dict handling recorded before the fix).


def test_firewall_rule_action_strings_become_members() -> None:
    """A string action becomes a member, including through ``_missing_``."""
    canonical = FirewallRule.model_validate({"id": "rule", "name": "rule", "action": "BLOCK"})
    mixed_case = FirewallRule.model_validate({"id": "rule", "name": "rule", "action": "block"})

    assert canonical.action is FirewallAction.BLOCK
    assert mixed_case.action is FirewallAction.BLOCK


def test_firewall_rule_action_unknown_string_stays_str() -> None:
    """An unknown action string still parses as the raw string."""
    rule = FirewallRule.model_validate({"id": "rule", "name": "rule", "action": "FUTURE"})

    assert type(rule.action) is str
    assert rule.action == "FUTURE"


@pytest.mark.parametrize(
    ("action", "expected_type"),
    [
        pytest.param({}, dict, id="empty-dict"),
        pytest.param({"type": "ALLOW"}, FirewallActionConfig, id="type-only"),
        pytest.param(
            {"type": "ALLOW", "allowReturnTraffic": True},
            FirewallActionConfig,
            id="allow-return-traffic",
        ),
        pytest.param({"type": "ALLOW", "unknownKey": 1}, FirewallActionConfig, id="unknown-key"),
    ],
)
def test_firewall_rule_action_dict_representation_is_unchanged(
    action: Any, expected_type: type[Any]
) -> None:
    """Dict actions keep the representation recorded before the #70 fix."""
    rule = FirewallRule.model_validate({"id": "rule", "name": "rule", "action": action})

    assert type(rule.action) is expected_type


def test_firewall_rule_action_config_keeps_attribute_access() -> None:
    """A config action still exposes its parsed fields as attributes."""
    rule = FirewallRule.model_validate(
        {
            "id": "rule",
            "name": "rule",
            "action": {"type": "ALLOW", "allowReturnTraffic": True},
        }
    )

    assert isinstance(rule.action, FirewallActionConfig)
    assert rule.action.type is FirewallAction.ALLOW
    assert rule.action.allow_return_traffic is True


def test_firewall_action_config_rejects_a_non_string_type() -> None:
    """The before-validator only rewrites strings; other input still fails."""
    with pytest.raises(ValidationError):
        FirewallActionConfig.model_validate({"type": 123})


def _modules() -> Iterator[Any]:
    yield unifi_official_api
    for info in pkgutil.walk_packages(
        unifi_official_api.__path__, f"{unifi_official_api.__name__}."
    ):
        yield importlib.import_module(info.name)


def _models() -> list[type[BaseModel]]:
    """Every model the package defines, deduplicated by class identity."""
    models: list[type[BaseModel]] = []
    seen: set[int] = set()
    for module in _modules():
        for obj in vars(module).values():
            if getattr(obj, "__module__", None) != module.__name__:
                continue
            if not isinstance(obj, type) or not issubclass(obj, BaseModel):
                continue
            if obj is BaseModel or id(obj) in seen:
                continue
            seen.add(id(obj))
            models.append(obj)
    return models


def _union_modes(metadata: tuple[Any, ...]) -> list[str]:
    """Read ``union_mode`` from field metadata, including nested ``FieldInfo``."""
    modes: list[str] = []
    pending = list(metadata)
    while pending:
        item = pending.pop(0)
        mode = getattr(item, "union_mode", None)
        if isinstance(mode, str):
            modes.append(mode)
        pending.extend(getattr(item, "metadata", ()))
    return modes


def _is_str_enum(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, StrEnum)


def _is_enum_str_union(annotation: Any) -> bool:
    args = get_args(annotation)
    return str in args and any(_is_str_enum(arg) for arg in args)


def _enum_str_unions(
    annotation: Any, path: str, metadata: tuple[Any, ...] = ()
) -> Iterator[tuple[str, list[str]]]:
    """Yield every enum-or-``str`` union in an annotation, with its metadata."""
    own = getattr(annotation, "__metadata__", None)
    if own is not None:
        yield from _enum_str_unions(get_args(annotation)[0], path, metadata + tuple(own))
        return
    origin = get_origin(annotation)
    if origin in (types.UnionType, typing.Union):
        if _is_enum_str_union(annotation):
            yield path, _union_modes(metadata)
            return
        for arg in get_args(annotation):
            yield from _enum_str_unions(arg, path, metadata)
        return
    if origin is list:
        for arg in get_args(annotation):
            yield from _enum_str_unions(arg, f"{path}[]", metadata)


DISCOVERED: dict[str, list[str]] = {
    f"{model.__name__}.{path}": modes
    for model in _models()
    for name, field in model.model_fields.items()
    for path, modes in _enum_str_unions(field.annotation, name, tuple(field.metadata))
}

# Fields normalised by a before-validator instead of ``union_mode``: their
# models sit inside a ``Model | dict`` smart union, and a field-level union mode
# makes the model inexact for dict input, which would hand every dict to the
# ``dict`` branch and change the public representation (#70).
NORMALISED_BY_VALIDATOR = frozenset({"FirewallActionConfig.type", "FirewallRule.action"})

EXPECTED_DECLARATIONS = frozenset(
    {
        "ACLMetadata.origin",
        "ACLRule.action",
        "ACLRule.protocol_filter[]",
        "ACLRule.type",
        "Camera.recording_mode",
        "Camera.video_mode",
        "Client.type",
        "DNSPolicy.type",
        "Device.state",
        "Device.type",
        "Event.type",
        "FirewallActionConfig.type",
        "FirewallRule.action",
        "InnerSpaceAccessPoint.mount_type",
        "LAG.type",
        "McLagPeer.role",
        "Site.health",
        "SwitchStackUnit.role",
        "UlpUser.status",
        "VPNServer.type",
        "VPNTunnel.status",
        "WANInterface.status",
        "WifiNetwork.security",
    }
)


def test_the_walk_finds_the_known_declarations() -> None:
    """The guard's inventory is exact, so a walk that finds nothing fails."""
    assert set(DISCOVERED) == EXPECTED_DECLARATIONS


@pytest.mark.parametrize("path", sorted(DISCOVERED))
def test_every_enum_or_str_union_is_enum_first(path: str) -> None:
    """Every enum-or-``str`` union validates the enum before ``str``."""
    modes = DISCOVERED[path]

    if path in NORMALISED_BY_VALIDATOR:
        assert modes == []
        return

    assert modes == ["left_to_right"]
