"""Pydantic models for UniFi Site Manager API."""

from .device import DeviceListResponse, SiteManagerDevice, SiteManagerHostDevices
from .host import Host, HostListResponse, HostReportedState, HostUserData
from .isp_metric import ISPMetric, ISPMetricQuery, ISPMetricQueryResult
from .sd_wan import SDWanConfig, SDWanConfigDetail, SDWanStatus
from .site import SiteListResponse, SiteManagerSite, SiteMeta, SiteStatistics

__all__ = [
    "DeviceListResponse",
    "Host",
    "HostListResponse",
    "HostReportedState",
    "HostUserData",
    "ISPMetric",
    "ISPMetricQuery",
    "ISPMetricQueryResult",
    "SDWanConfig",
    "SDWanConfigDetail",
    "SDWanStatus",
    "SiteListResponse",
    "SiteManagerDevice",
    "SiteManagerHostDevices",
    "SiteManagerSite",
    "SiteMeta",
    "SiteStatistics",
]
