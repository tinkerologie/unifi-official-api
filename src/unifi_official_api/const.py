"""Constants for the UniFi Official API library."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from ._version import __version__

# Credential keys redacted in transport response logs and caller diagnostics.
# Identifiers, privacy keys, and integration-specific constants are excluded
# and managed separately by consumers.
SENSITIVE_CREDENTIAL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "token",
        "accessToken",
        "access_token",
        "refreshToken",
        "refresh_token",
        "password",
        "psk",
        "passphrase",
        "qr_code",
        "secret",
        "voucher",
        "fingerprint",
        "api_key",
        "x_passphrase",
        "x_authkey",
        "x_fingerprint",
        "x_iapp_key",
        "x_ssh_hostkey_fingerprint",
        "x_vwirekey",
    }
)


class ConnectionType(StrEnum):
    """
    Connection type for UniFi API access.

    LOCAL: Direct connection to the UniFi console (e.g., https://192.168.1.1)
           - Uses local API key generated on the console
           - Endpoints: /proxy/{service}/integration/v1/...

    REMOTE: Cloud connection via Ubiquiti's API (https://api.ui.com)
            - Uses cloud API key from account.ui.com
            - Endpoints: /v1/connector/consoles/{consoleId}/{service}/integration/v1/...
    """

    LOCAL = "local"
    REMOTE = "remote"


# API Base URLs
NETWORK_API_BASE_URL: Final[str] = "https://api.ui.com"
PROTECT_API_BASE_URL: Final[str] = "https://api.ui.com"
INNERSPACE_API_BASE_URL: Final[str] = "https://api.ui.com"
SITE_MANAGER_API_BASE_URL: Final[str] = "https://api.ui.com"
MOBILITY_API_BASE_URL: Final[str] = "https://api.ui.com"
CARRIER_FABRIC_API_BASE_URL: Final[str] = "https://api.ui.com"
CARRIER_FABRIC_BASE_URL: Final[str] = CARRIER_FABRIC_API_BASE_URL

# API Versions
NETWORK_API_VERSION: Final[str] = "v1"
PROTECT_API_VERSION: Final[str] = "v1"
INNERSPACE_API_VERSION: Final[str] = "v1"
SITE_MANAGER_API_VERSION: Final[str] = "v1"
MOBILITY_API_VERSION: Final[str] = "v1"
CARRIER_FABRIC_API_VERSION: Final[str] = "v1"

# Pinned upstream OpenAPI / documentation specification versions
NETWORK_SPEC_VERSION: Final[str] = "11.0.97"
PROTECT_SPEC_VERSION: Final[str] = "7.3.70"
INNERSPACE_SPEC_VERSION: Final[str] = "1.3.23"
MOBILITY_SPEC_VERSION: Final[str] = "1.0.0"
SITE_MANAGER_SPEC_VERSION: Final[str] = "1.0.0"
CARRIER_FABRIC_SPEC_VERSION: Final[str] = "1.0.0"
ACCESS_DOC_VERSION: Final[str] = "2.2.10"

# Network Integration API path prefix (used for both local and remote)
NETWORK_INTEGRATION_PATH: Final[str] = "/proxy/network/integration/v1"

# Network legacy API path prefix (used for both local and remote)
NETWORK_LEGACY_PATH: Final[str] = "/proxy/network/api"

# Network legacy v2 API path prefix (used for traffic routes / policy-based routes)
NETWORK_LEGACY_V2_PATH: Final[str] = "/proxy/network/v2/api"

# Network legacy v2 endpoints
ENDPOINT_TRAFFIC_ROUTES: Final[str] = "trafficroutes"
# Traffic rules (app, domain, IP and internet blocking); separate from trafficroutes.
ENDPOINT_TRAFFIC_RULES: Final[str] = "trafficrules"
# Custom NAT rules (v2 only; reference-derived, no GET-by-id).
ENDPOINT_NAT_RULES: Final[str] = "nat"

# Network legacy REST endpoints
ENDPOINT_NETWORKCONF: Final[str] = "rest/networkconf"
# Port forwarding rules (classic API only; v2 "portforwards" is 404 on Network 11).
ENDPOINT_PORT_FORWARD: Final[str] = "rest/portforward"
# Static routes (classic API only; v2 "static-route" is 404 on Network 11).
ENDPOINT_STATIC_ROUTES: Final[str] = "rest/routing"
# Live state of VPN clients and site-to-site tunnels (v2, per connection).
ENDPOINT_VPN_CONNECTIONS: Final[str] = "vpn/connections"

# Protect Integration API path prefix (used for both local and remote)
PROTECT_INTEGRATION_PATH: Final[str] = "/proxy/protect/integration/v1"

# InnerSpace Integration API path prefix (used for both local and remote)
INNERSPACE_INTEGRATION_PATH: Final[str] = "/proxy/innerspace/integration/v1"

# Carrier Fabric API path prefix
CARRIER_FABRIC_PATH: Final[str] = "/v1/carrier"

# Carrier Fabric pagination
CARRIER_FABRIC_DEFAULT_PAGE_SIZE: Final[int] = 50
CARRIER_FABRIC_MAX_PAGE_SIZE: Final[int] = 500
CARRIER_FABRIC_MAX_PAGES: Final[int] = 200

# Default timeouts (in seconds)
DEFAULT_TIMEOUT: Final[int] = 30
DEFAULT_CONNECT_TIMEOUT: Final[int] = 10

# Rate limiting
DEFAULT_RATE_LIMIT_RETRY_AFTER: Final[int] = 60

# The local Protect Integration API allows 10 requests per fixed 1-second
# window per API key, and advertises it on every response
# (`RateLimit-Policy: "10-in-1sec"; q=10; w=1`). A 429 carries
# `Retry-After: 1`. The Network Integration API sends no rate-limit headers
# and its requests do not draw from the Protect allowance.
PROTECT_RATE_LIMIT_REQUESTS: Final[int] = 10
PROTECT_RATE_LIMIT_WINDOW: Final[float] = 1.0
# The cloud Mobility API allows 100 requests per minute per API key, shared by
# every Mobility endpoint, and answers a 429 `rate_limit` beyond that.
MOBILITY_RATE_LIMIT_REQUESTS: Final[int] = 100
MOBILITY_RATE_LIMIT_WINDOW: Final[float] = 60.0
# Added to the window on the client side so request-arrival jitter cannot
# land an 11th request inside one of the server's fixed windows.
RATE_LIMIT_WINDOW_MARGIN: Final[float] = 0.1
# A 429 is retried once after its Retry-After only when the server asks for a
# short wait; a longer (or missing, i.e. defaulted) Retry-After is raised to
# the caller as before, so a request never blocks for a minute.
RATE_LIMIT_MAX_RETRY_AFTER: Final[int] = 5

# User agent - uses version from single source of truth
USER_AGENT: Final[str] = f"unifi-official-api/{__version__}"

# HTTP Headers
HEADER_CONTENT_TYPE: Final[str] = "Content-Type"
HEADER_ACCEPT: Final[str] = "Accept"
HEADER_USER_AGENT: Final[str] = "User-Agent"
HEADER_API_KEY: Final[str] = "X-API-Key"

# Content types
CONTENT_TYPE_JSON: Final[str] = "application/json"

__all__ = [
    "__version__",
    "ACCESS_DOC_VERSION",
    "CARRIER_FABRIC_API_BASE_URL",
    "CARRIER_FABRIC_API_VERSION",
    "CARRIER_FABRIC_BASE_URL",
    "CARRIER_FABRIC_DEFAULT_PAGE_SIZE",
    "CARRIER_FABRIC_MAX_PAGES",
    "CARRIER_FABRIC_MAX_PAGE_SIZE",
    "CARRIER_FABRIC_PATH",
    "CARRIER_FABRIC_SPEC_VERSION",
    "CONTENT_TYPE_JSON",
    "ConnectionType",
    "DEFAULT_CONNECT_TIMEOUT",
    "DEFAULT_RATE_LIMIT_RETRY_AFTER",
    "DEFAULT_TIMEOUT",
    "ENDPOINT_NAT_RULES",
    "ENDPOINT_NETWORKCONF",
    "ENDPOINT_PORT_FORWARD",
    "ENDPOINT_STATIC_ROUTES",
    "ENDPOINT_TRAFFIC_ROUTES",
    "ENDPOINT_TRAFFIC_RULES",
    "ENDPOINT_VPN_CONNECTIONS",
    "HEADER_ACCEPT",
    "HEADER_API_KEY",
    "HEADER_CONTENT_TYPE",
    "HEADER_USER_AGENT",
    "INNERSPACE_API_BASE_URL",
    "INNERSPACE_API_VERSION",
    "INNERSPACE_INTEGRATION_PATH",
    "INNERSPACE_SPEC_VERSION",
    "MOBILITY_API_BASE_URL",
    "MOBILITY_API_VERSION",
    "MOBILITY_RATE_LIMIT_REQUESTS",
    "MOBILITY_RATE_LIMIT_WINDOW",
    "MOBILITY_SPEC_VERSION",
    "NETWORK_API_BASE_URL",
    "NETWORK_API_VERSION",
    "NETWORK_INTEGRATION_PATH",
    "NETWORK_LEGACY_PATH",
    "NETWORK_LEGACY_V2_PATH",
    "NETWORK_SPEC_VERSION",
    "PROTECT_API_BASE_URL",
    "PROTECT_API_VERSION",
    "PROTECT_INTEGRATION_PATH",
    "PROTECT_RATE_LIMIT_REQUESTS",
    "PROTECT_RATE_LIMIT_WINDOW",
    "PROTECT_SPEC_VERSION",
    "RATE_LIMIT_MAX_RETRY_AFTER",
    "RATE_LIMIT_WINDOW_MARGIN",
    "SENSITIVE_CREDENTIAL_KEYS",
    "SITE_MANAGER_API_BASE_URL",
    "SITE_MANAGER_API_VERSION",
    "SITE_MANAGER_SPEC_VERSION",
    "USER_AGENT",
]
