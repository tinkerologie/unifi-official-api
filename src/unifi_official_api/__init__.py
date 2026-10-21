"""UniFi Official API - Async Python library for UniFi APIs.

This library provides async Python clients for the official UniFi APIs:
- UniFi Network API: Manage network devices, clients, WiFi, and more
- UniFi Protect API: Manage cameras, sensors, lights, and read NVR information
- UniFi Access API: Manage doors, emergency modes, users, and webhooks
- UniFi InnerSpace API: Floor plans, CAD imports, and WiFi heatmaps
- UniFi Mobility API: LTE/5G mobile routers, failover, and data usage
- UniFi Site Manager API: Organization-level multi-console fleet management
- UniFi Carrier Fabric API: Enterprise carrier infrastructure

Supports both LOCAL (direct to device) and REMOTE (via cloud) connections.
"""

from __future__ import annotations

from ._version import __version__
from .access import UniFiAccessClient
from .auth import AccessTokenAuth, ApiKeyAuth, ApiKeyType, LocalAuth
from .carrier_fabric import UniFiCarrierFabricClient
from .const import ConnectionType
from .exceptions import (
    UniFiAuthenticationError,
    UniFiConnectionError,
    UniFiError,
    UniFiGlobalAlarmManagerError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiResponseError,
    UniFiRuleNotEditableError,
    UniFiTimeoutError,
    UniFiUnsupportedError,
    UniFiValidationError,
)
from .innerspace import UniFiInnerSpaceClient
from .mobility import UniFiMobilityClient
from .network import UniFiNetworkClient
from .protect import UniFiProtectClient
from .site_manager import UniFiSiteManagerClient

__all__ = [
    # Version
    "__version__",
    # Authentication
    "AccessTokenAuth",
    "ApiKeyAuth",
    "ApiKeyType",
    "LocalAuth",
    # Clients
    "UniFiAccessClient",
    "UniFiCarrierFabricClient",
    "UniFiInnerSpaceClient",
    "UniFiMobilityClient",
    "UniFiNetworkClient",
    "UniFiProtectClient",
    "UniFiSiteManagerClient",
    # Connection types
    "ConnectionType",
    # Exceptions
    "UniFiAuthenticationError",
    "UniFiConnectionError",
    "UniFiError",
    "UniFiGlobalAlarmManagerError",
    "UniFiNotFoundError",
    "UniFiRateLimitError",
    "UniFiResponseError",
    "UniFiRuleNotEditableError",
    "UniFiTimeoutError",
    "UniFiUnsupportedError",
    "UniFiValidationError",
]
