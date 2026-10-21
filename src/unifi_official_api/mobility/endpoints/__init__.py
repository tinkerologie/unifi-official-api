"""Endpoint modules for UniFi Mobility API."""

from .clients import ClientsEndpoint
from .devices import DevicesEndpoint
from .network import NetworkEndpoint
from .wireless import WirelessEndpoint
from .workspaces import WorkspacesEndpoint

__all__ = [
    "ClientsEndpoint",
    "DevicesEndpoint",
    "NetworkEndpoint",
    "WirelessEndpoint",
    "WorkspacesEndpoint",
]
