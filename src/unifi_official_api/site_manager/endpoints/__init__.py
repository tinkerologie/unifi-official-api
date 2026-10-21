"""Endpoint modules for UniFi Site Manager API."""

from .connector import ConnectorEndpoint
from .devices import DevicesEndpoint
from .hosts import HostsEndpoint
from .isp_metrics import ISPMetricsEndpoint
from .sd_wan import SDWanEndpoint
from .sites import SitesEndpoint

__all__ = [
    "ConnectorEndpoint",
    "DevicesEndpoint",
    "HostsEndpoint",
    "ISPMetricsEndpoint",
    "SDWanEndpoint",
    "SitesEndpoint",
]
