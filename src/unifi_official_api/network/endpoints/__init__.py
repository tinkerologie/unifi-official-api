"""Endpoint modules for UniFi Network API."""

from .acl import ACLEndpoint
from .clients import ClientsEndpoint
from .devices import DevicesEndpoint
from .dns import DNSEndpoint
from .firewall import FirewallEndpoint
from .lags import LagsEndpoint
from .nat_rules import NatRulesEndpoint
from .networks import NetworksEndpoint
from .port_forwards import PortForwardsEndpoint
from .reports import ReportsEndpoint
from .resources import ResourcesEndpoint
from .routes import RoutesEndpoint
from .sites import SitesEndpoint
from .stacks import StacksEndpoint
from .static_routes import StaticRoutesEndpoint
from .switching import SwitchingEndpoint
from .traffic import TrafficEndpoint
from .traffic_rules import TrafficRulesEndpoint
from .vouchers import VouchersEndpoint
from .vpn_clients import VpnClientsEndpoint
from .wifi import WifiEndpoint

__all__ = [
    "ACLEndpoint",
    "ClientsEndpoint",
    "DNSEndpoint",
    "DevicesEndpoint",
    "FirewallEndpoint",
    "LagsEndpoint",
    "NatRulesEndpoint",
    "NetworksEndpoint",
    "PortForwardsEndpoint",
    "ReportsEndpoint",
    "ResourcesEndpoint",
    "RoutesEndpoint",
    "SitesEndpoint",
    "StacksEndpoint",
    "StaticRoutesEndpoint",
    "SwitchingEndpoint",
    "TrafficEndpoint",
    "TrafficRulesEndpoint",
    "VouchersEndpoint",
    "VpnClientsEndpoint",
    "WifiEndpoint",
]
