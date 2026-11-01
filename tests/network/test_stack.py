"""Tests for the switch stack models and their pinned-spec conformance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from unifi_official_api.const import NETWORK_SPEC_VERSION
from unifi_official_api.network.models import switching
from unifi_official_api.network.models.lag import LagMember
from unifi_official_api.network.models.stack import (
    SwitchStack,
    SwitchStackLag,
    SwitchStackLagMember,
    SwitchStackMember,
    SwitchStackPage,
    SwitchStackUnit,
    SwitchStackUnitRole,
)

SPEC_PATH = (
    Path(__file__).parent.parent / "fixtures" / f"network_openapi_{NETWORK_SPEC_VERSION}.json"
)

# Network 11.0.97 shape, as reported in issue #68.
V11_STACK: dict[str, Any] = {
    "id": "7c1d4f0e-0000-4000-8000-000000000001",
    "name": "Core stack",
    "deviceId": "7c1d4f0e-0000-4000-8000-000000000002",
    "metadata": {},
    "units": [
        {"id": 1, "macAddress": "aa:bb:cc:00:00:01", "order": 1, "role": "ACTIVE_CONTROLLER"},
        {"id": 2, "macAddress": "aa:bb:cc:00:00:02", "order": 2, "role": "MEMBER"},
    ],
    "lags": [
        {
            "id": "7c1d4f0e-0000-4000-8000-000000000003",
            "metadata": {},
            "members": [{"unitId": 1, "unitMacAddress": "aa:bb:cc:00:00:01", "portIdxs": [1, 2]}],
        }
    ],
}

# Network 10.4.57 shape: the legacy ``members`` field, no units.
LEGACY_STACK: dict[str, Any] = {
    "id": "stack-1",
    "name": "Legacy stack",
    "members": [
        {
            "deviceId": "dev-1",
            "switchMac": "aa:bb:cc:00:00:01",
            "role": "MASTER",
            "state": "CONNECTED",
        },
        {"switchMac": "aa:bb:cc:00:00:02"},
    ],
    "lags": [{"id": "lag-1", "members": [{"deviceId": "dev-1", "portIdxs": [3]}]}],
}

SPEC_MODELS: dict[str, type[BaseModel]] = {
    "IntegrationSwitchStackDto": SwitchStack,
    "IntegrationSwitchStackUnitDto": SwitchStackUnit,
    "IntegrationSwitchStackLagLocalDto": SwitchStackLag,
    "IntegrationSwitchStackLagMemberDto": SwitchStackLagMember,
    "IntegrationSwitchStackDtoPageDto": SwitchStackPage,
}


def _load_spec() -> dict[str, Any]:
    """Return the pinned Network OpenAPI document."""
    spec: dict[str, Any] = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    return spec


def _declared_keys(model: type[BaseModel]) -> set[str]:
    """Return every field name and alias a model accepts."""
    keys: set[str] = set()
    for name, field in model.model_fields.items():
        keys.add(name)
        if field.alias:
            keys.add(field.alias)
    return keys


class TestSwitchStackV11:
    """Tests for the Network 11.0.97 switch stack payload."""

    def test_units_are_typed(self) -> None:
        """Units, their role enum and the stack device ID are typed."""
        stack = SwitchStack.model_validate(V11_STACK)

        assert stack.device_id == "7c1d4f0e-0000-4000-8000-000000000002"
        assert [unit.id for unit in stack.units] == [1, 2]
        unit = stack.units[0]
        assert unit.mac_address == "aa:bb:cc:00:00:01"
        assert unit.order == 1
        assert isinstance(unit.role, SwitchStackUnitRole)
        assert unit.role == SwitchStackUnitRole.ACTIVE_CONTROLLER

    def test_lag_members_carry_unit_references(self) -> None:
        """Stack LAG members are typed, with the unit fields the spec defines."""
        stack = SwitchStack.model_validate(V11_STACK)

        lag = stack.lags[0]
        assert isinstance(lag, SwitchStackLag)
        member = lag.members[0]
        assert isinstance(member, SwitchStackLagMember)
        assert isinstance(member, LagMember)
        assert member.unit_id == 1
        assert member.unit_mac_address == "aa:bb:cc:00:00:01"
        assert member.port_idxs == [1, 2]
        assert member.device_id is None

    def test_no_spec_field_falls_into_extra(self) -> None:
        """Every v11 field is declared, so none survives as an untyped extra."""
        stack = SwitchStack.model_validate(V11_STACK)

        assert stack.members == []
        assert stack.model_extra == {}

    def test_round_trip_writes_the_camel_case_keys(self) -> None:
        """Dumping by alias emits the spec's keys."""
        dumped = SwitchStack.model_validate(V11_STACK).model_dump(by_alias=True)

        assert dumped["deviceId"] == "7c1d4f0e-0000-4000-8000-000000000002"
        assert dumped["units"][0]["macAddress"] == "aa:bb:cc:00:00:01"
        lag_member = dumped["lags"][0]["members"][0]
        assert lag_member["unitId"] == 1
        assert lag_member["unitMacAddress"] == "aa:bb:cc:00:00:01"
        assert lag_member["portIdxs"] == [1, 2]

    def test_page_parses_the_v11_shape(self) -> None:
        """The page model validates the v11 stack inside its data list."""
        page = SwitchStackPage.model_validate(
            {
                "data": [V11_STACK],
                "count": 1,
                "limit": 25,
                "offset": 0,
                "totalCount": 1,
            }
        )

        assert isinstance(page.data[0], SwitchStack)
        assert page.data[0].units[1].role == SwitchStackUnitRole.MEMBER
        assert page.total_count == 1


class TestSwitchStackUnitRole:
    """Tests for the stack unit role enum."""

    def test_lowercase_role_maps_to_the_member(self) -> None:
        """A lower-cased role is accepted as its enum member."""
        assert SwitchStackUnitRole("active_controller") is SwitchStackUnitRole.ACTIVE_CONTROLLER
        unit = SwitchStackUnit(id=1, mac_address="aa:bb:cc:00:00:01", role="member")
        assert unit.role is SwitchStackUnitRole.MEMBER

    def test_unknown_role_stays_a_string(self) -> None:
        """A role outside the enum's values is kept as the string the API sent."""
        unit = SwitchStackUnit(id=1, mac_address="aa:bb:cc:00:00:01", role="SUPERVISOR")

        assert unit.role == "SUPERVISOR"
        assert not isinstance(unit.role, SwitchStackUnitRole)
        assert SwitchStackUnitRole._missing_("SUPERVISOR") is None

    def test_non_string_role_is_not_matched(self) -> None:
        """Only strings can be matched case-insensitively."""
        assert SwitchStackUnitRole._missing_(1) is None


class TestSwitchStackLegacy:
    """Tests for the deprecated 10.4.57 switch stack payload."""

    def test_legacy_members_parse_and_units_stay_empty(self) -> None:
        """The legacy ``members`` field still parses, with no units."""
        stack = SwitchStack.model_validate(LEGACY_STACK)

        assert stack.units == []
        assert stack.device_id is None
        assert isinstance(stack.members[0], SwitchStackMember)
        assert stack.members[0].device_id == "dev-1"
        assert stack.members[0].switch_mac == "aa:bb:cc:00:00:01"
        assert stack.members[0].role == "MASTER"
        assert stack.members[0].state == "CONNECTED"
        assert stack.members[1].device_id is None

    def test_legacy_lag_members_are_typed(self) -> None:
        """Stack LAG members validate the legacy device ID shape too."""
        stack = SwitchStack.model_validate(LEGACY_STACK)

        member = stack.lags[0].members[0]
        assert member.device_id == "dev-1"
        assert member.port_idxs == [3]
        assert member.unit_id is None
        assert member.unit_mac_address is None


def test_switching_module_reexports_the_canonical_models() -> None:
    """Both endpoints return the same stack classes."""
    assert switching.SwitchStack is SwitchStack
    assert switching.SwitchStackMember is SwitchStackMember
    assert switching.SwitchStackPage is SwitchStackPage


@pytest.mark.parametrize(("schema_name", "model"), sorted(SPEC_MODELS.items()))
def test_model_declares_every_spec_property(schema_name: str, model: type[BaseModel]) -> None:
    """Every property of the pinned spec schema is a field name or alias."""
    schema = _load_spec()["components"]["schemas"][schema_name]

    missing = set(schema["properties"]) - _declared_keys(model)
    assert missing == set(), f"{schema_name} -> {model.__name__}"


def test_unit_role_enum_matches_the_spec() -> None:
    """The unit role enum holds exactly the spec's role values."""
    schema = _load_spec()["components"]["schemas"]["IntegrationSwitchStackUnitDto"]

    assert schema["properties"]["role"]["enum"] == [role.value for role in SwitchStackUnitRole]
