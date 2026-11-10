"""ISP Metrics models for UniFi Site Manager."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ISPMetricWAN(BaseModel):
    """WAN measurements for one ISP metrics period."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    avg_latency: int | float | None = Field(default=None, alias="avgLatency")
    max_latency: int | float | None = Field(default=None, alias="maxLatency")
    packet_loss: int | float | None = Field(default=None, alias="packetLoss")
    uptime: int | float | None = None
    downtime: int | float | None = None
    download_kbps: int | float | None = None
    upload_kbps: int | float | None = None
    isp_name: str | None = Field(default=None, alias="ispName")
    isp_asn: str | None = Field(default=None, alias="ispAsn")


class ISPMetricPeriodData(BaseModel):
    """Measurements from a single ISP metrics period."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    wan: ISPMetricWAN | None = None


class ISPMetricPeriod(BaseModel):
    """Timestamped sample in a host and site record."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    metric_time: AwareDatetime | None = Field(default=None, alias="metricTime")
    version: str | None = None
    data: ISPMetricPeriodData | None = None


class ISPMetric(BaseModel):
    """ISP metrics record for one host and site, with legacy flat fields."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    metric_type: str | None = Field(default=None, alias="metricType")
    host_id: str | None = Field(default=None, alias="hostId")
    site_id: str | None = Field(default=None, alias="siteId")
    periods: list[ISPMetricPeriod | None] | None = None
    timestamp: int | str | None = None
    value: float | None = None
    details: dict[str, Any] | None = None


class ISPMetricQuerySite(BaseModel):
    """Site and optional time range for an ISP metrics query."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    host_id: str = Field(alias="hostId")
    site_id: str = Field(alias="siteId")
    begin_timestamp: AwareDatetime | None = Field(default=None, alias="beginTimestamp")
    end_timestamp: AwareDatetime | None = Field(default=None, alias="endTimestamp")


class ISPMetricQuery(BaseModel):
    """Query payload for ISP metrics."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    host_ids: list[str] = Field(default_factory=list, alias="hostIds")
    time_range_start: int | str | None = Field(default=None, alias="timeRangeStart")
    time_range_end: int | str | None = Field(default=None, alias="timeRangeEnd")
    sites: list[ISPMetricQuerySite] | None = None


class ISPMetricQueryResult(BaseModel):
    """Result of querying ISP metrics."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    metrics: list[ISPMetric] = Field(default_factory=list)
    status: str | None = None
    message: str | None = None
