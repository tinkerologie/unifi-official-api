"""Access point models for UniFi InnerSpace API."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .project import InnerSpaceBaseModel


class InnerSpaceMountType(StrEnum):
    """Access point mounting orientation in InnerSpace."""

    CEILING = "CEILING"
    WALL = "WALL"

    @classmethod
    def _missing_(cls, value: object) -> InnerSpaceMountType | None:
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None


class InnerSpaceAccessPoint(InnerSpaceBaseModel):
    """Access point placement entry returned by ``GET /v1/access_points``."""

    id: str = Field(min_length=1)
    name: str = ""
    mac: str | None = None
    model: str | None = None
    floor_plan_id: str | None = Field(default=None, alias="floorPlanId")
    x: float | None = None
    y: float | None = None
    height: float | None = None
    mount_type: InnerSpaceMountType | str | None = Field(
        default=None, alias="mountType", union_mode="left_to_right"
    )
    orientation: float | None = None
    tx_power_2g: float | None = Field(default=None, alias="txPower2g")
    tx_power_5g: float | None = Field(default=None, alias="txPower5g")
    tx_power_6g: float | None = Field(default=None, alias="txPower6g")


__all__ = [
    "InnerSpaceAccessPoint",
    "InnerSpaceMountType",
]
