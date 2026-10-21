"""ISP Metrics models for UniFi Site Manager."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ISPMetric(BaseModel):
    """ISP metric data point."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    metric_type: str | None = Field(default=None, alias="metricType")
    timestamp: int | str | None = None
    value: float | None = None
    details: dict[str, Any] | None = None


class ISPMetricQuery(BaseModel):
    """Query payload for ISP metrics."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    host_ids: list[str] = Field(default_factory=list, alias="hostIds")
    time_range_start: int | str | None = Field(default=None, alias="timeRangeStart")
    time_range_end: int | str | None = Field(default=None, alias="timeRangeEnd")


class ISPMetricQueryResult(BaseModel):
    """Result of querying ISP metrics."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    metrics: list[ISPMetric] = Field(default_factory=list)
