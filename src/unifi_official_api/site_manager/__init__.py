"""UniFi Site Manager API module."""

from .client import UniFiSiteManagerClient
from .models import (
    DeviceListResponse,
    Host,
    HostListResponse,
    HostReportedState,
    HostUserData,
    ISPMetric,
    ISPMetricQuery,
    ISPMetricQueryResult,
    SDWanConfig,
    SDWanConfigDetail,
    SDWanStatus,
    SiteListResponse,
    SiteManagerDevice,
    SiteManagerHostDevices,
    SiteManagerSite,
    SiteMeta,
    SiteStatistics,
)

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
    "UniFiSiteManagerClient",
]
