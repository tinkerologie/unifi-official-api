"""Pydantic models for UniFi Network statistics series."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

STATS_PERIODS = frozenset({"HOUR", "DAY", "WEEK", "MONTH"})


def _finite_float(value: object) -> float | None:
    """Return ``value`` as a finite float, or None for bool, non-numeric or out-of-range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric = float(value)
    except OverflowError:
        return None
    return numeric if math.isfinite(numeric) else None


def _coerce_optional_bytes(value: object) -> float | None:
    """Coerce a stats byte value to a non-negative float or return None."""
    numeric = _finite_float(value)
    if numeric is not None and numeric >= 0:
        return numeric
    return None


class StatisticsSource(RootModel[Literal["LEGACY", "MODERN"]]):
    """
    Controller-wide statistics engine source mode.

    Network 10.x returns "LEGACY"; Network 11.x returns "MODERN".
    """

    root: Literal["LEGACY", "MODERN"]


class StatsSeriesBucket(BaseModel):
    """
    One bucket in a Network 11 statistics series.

    Observed live evidence (Network 11.1.47) indicates that rx_bytes and
    tx_bytes represent additive per-bucket byte totals (fractional floats)
    accumulated over the bucket's duration (in milliseconds), rather than
    rates, bits, or cumulative counters.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    timestamp: int = Field(description="Bucket start timestamp in milliseconds since epoch")
    duration: int = Field(description="Bucket duration in milliseconds")
    rx_bytes: float | None = Field(
        default=None,
        alias="rxBytes",
        description=(
            "Additive download byte total for this bucket interval "
            "(bytes as float), or None if absent"
        ),
    )
    tx_bytes: float | None = Field(
        default=None,
        alias="txBytes",
        description=(
            "Additive upload byte total for this bucket interval "
            "(bytes as float), or None if absent"
        ),
    )

    @field_validator("timestamp", "duration", mode="before")
    @classmethod
    def _validate_milliseconds(cls, value: object) -> int:
        """Preserve integer milliseconds and accept whole numbers from JSON floats."""
        if type(value) is int and value >= 0:
            return value
        if isinstance(value, float) and value >= 0 and value.is_integer():
            return int(value)
        msg = "timestamp and duration must be nonnegative whole milliseconds"
        raise ValueError(msg)

    @field_validator("rx_bytes", "tx_bytes", mode="before")
    @classmethod
    def _validate_optional_bytes(cls, value: object) -> float | None:
        """Treat missing, nonfinite, negative, or bool byte fields as absent (None)."""
        return _coerce_optional_bytes(value)


class StatsSeries(BaseModel):
    """
    Statistics time series group for a UniFi Network site.

    Contains the controller's internal site UUID and an ordered list of
    observed statistics buckets.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    site_id: str = Field(alias="siteId", description="Internal site UUID")
    series: list[StatsSeriesBucket] = Field(description="List of statistics buckets")

    @field_validator("site_id", mode="before")
    @classmethod
    def _validate_site_id(cls, value: object) -> str:
        """Validate that siteId is a nonempty string."""
        if not isinstance(value, str) or not value.strip():
            msg = "siteId must be a nonempty string"
            raise ValueError(msg)
        return value.strip()
