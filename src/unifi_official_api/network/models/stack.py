"""Switch stack models for UniFi Network API."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .lag import LagMember


class SwitchStackUnitRole(StrEnum):
    """Role of a unit inside a switch stack."""

    ACTIVE_CONTROLLER = "ACTIVE_CONTROLLER"
    BACKUP_CONTROLLER = "BACKUP_CONTROLLER"
    MEMBER = "MEMBER"

    @classmethod
    def _missing_(cls, value: object) -> SwitchStackUnitRole | None:
        """Handle unknown-cased stack unit roles."""
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None


class SwitchStackUnit(BaseModel):
    """A switch unit inside a switch stack (Network 11.0.97 shape)."""

    id: int
    mac_address: str = Field(alias="macAddress")
    order: int | None = None
    role: SwitchStackUnitRole | str | None = Field(default=None, union_mode="left_to_right")

    model_config = {"populate_by_name": True, "extra": "allow"}


class SwitchStackLagMember(LagMember):
    """A member of a LAG local to a switch stack (Network 11.0.97 shape)."""

    unit_id: int | None = Field(default=None, alias="unitId")
    unit_mac_address: str | None = Field(default=None, alias="unitMacAddress")


class SwitchStackLag(BaseModel):
    """A LAG that is local to a switch stack."""

    id: str
    members: list[SwitchStackLagMember] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class SwitchStackMember(BaseModel):
    """
    A device that is a member of a switch stack.

    Covers the legacy 10.4.57 ``members`` entry (``deviceId``) plus the
    ``switchMac``, ``role`` and ``state`` fields the former
    ``switching.SwitchStackMember`` declared.
    """

    device_id: str | None = Field(default=None, alias="deviceId")
    switch_mac: str | None = Field(default=None, alias="switchMac")
    role: str | None = None
    state: str | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class SwitchStack(BaseModel):
    """
    Model representing a switch stack.

    ``members`` is the legacy 10.4.57 field: it is deprecated in favour of the
    typed ``units`` Network 11.0.97 reports, and will be removed in the next
    major release.
    """

    id: str
    name: str | None = None
    device_id: str | None = Field(default=None, alias="deviceId")
    units: list[SwitchStackUnit] = Field(default_factory=list)
    members: list[SwitchStackMember] = Field(default_factory=list)
    lags: list[SwitchStackLag] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class SwitchStackPage(BaseModel):
    """Paginated list of switch stacks."""

    data: list[SwitchStack] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    total_count: int = Field(default=0, alias="totalCount")

    model_config = {"populate_by_name": True, "extra": "allow"}
