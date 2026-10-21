# Copyright 2026 UniFi Insights contributors
"""Test fixtures for port forward and traffic rule responses.

Sources:
- Port forward keys are taken from a live Network 11 probe (2026-10-09),
  exactly 14 keys.
- Traffic rule keys mirror aiounifi v96 TRAFFIC_RULES[0] (Home Assistant core unifi
  dependency); not observed on a live console (0 records on Network 11, 2026-10-09).
- NAT keys mirror the sirkirby/unifi-mcp Network 10.6 fixture; reference-derived,
  not live-observed (0 records on Network 11, 2026-10-12).
- Static route keys mirror the sirkirby/unifi-network-rules PRD sample cross-checked
  with go-unifi Routing.json; reference-derived, not live-observed (0 records on
  Network 11, 2026-10-12).
Values in records are synthetic unless noted.
"""

from typing import Any

LIVE_PORT_FORWARD_KEYS: frozenset[str] = frozenset(
    {
        "_id",
        "destination_ip",
        "destination_ips",
        "dst_port",
        "enabled",
        "fwd",
        "fwd_port",
        "log",
        "name",
        "pfwd_interface",
        "proto",
        "site_id",
        "src",
        "src_limiting_enabled",
    }
)

AIOUNIFI_TRAFFIC_RULE_KEYS: frozenset[str] = frozenset(
    {
        "_id",
        "action",
        "app_category_ids",
        "app_ids",
        "bandwidth_limit",
        "description",
        "domains",
        "enabled",
        "ip_addresses",
        "ip_ranges",
        "matching_target",
        "network_ids",
        "regions",
        "schedule",
        "target_devices",
    }
)


REFERENCE_NAT_RULE_KEYS: frozenset[str] = frozenset(
    {
        "_id",
        "description",
        "destination_filter",
        "enabled",
        "exclude",
        "in_interface",
        "ip_address",
        "ip_version",
        "is_predefined",
        "logging",
        "port",
        "pppoe_use_base_interface",
        "protocol",
        "rule_index",
        "setting_preference",
        "source_filter",
        "type",
    }
)

REFERENCE_STATIC_ROUTE_KEYS: frozenset[str] = frozenset(
    {
        "_id",
        "enabled",
        "gateway_device",
        "gateway_type",
        "name",
        "site_id",
        "static-route_distance",
        "static-route_interface",
        "static-route_network",
        "static-route_type",
        "type",
    }
)


def port_forward_record(**overrides: Any) -> dict[str, Any]:
    """Return a synthetic port forward record with the 14 live keys."""
    record: dict[str, Any] = {
        "_id": "pf-plex",
        "name": "Plex",
        "enabled": True,
        "proto": "tcp_udp",
        "dst_port": "32400",
        "fwd_port": "32400",
        "pfwd_interface": "wan",
        "log": False,
        "src_limiting_enabled": False,
        "site_id": "classic-site-id",
        "destination_ips": [],
        "fwd": "192.168.1.50",
        "src": "198.51.100.0/24",
        "destination_ip": "203.0.113.7",
    }
    record.update(overrides)
    return record


def traffic_rule_record(**overrides: Any) -> dict[str, Any]:
    """Return a synthetic traffic rule record with the aiounifi v96 keys."""
    record: dict[str, Any] = {
        "_id": "tr-bedtime",
        "action": "BLOCK",
        "app_category_ids": [],
        "app_ids": [],
        "bandwidth_limit": {
            "download_limit_kbps": 10000,
            "enabled": False,
            "upload_limit_kbps": 5000,
        },
        "description": "Bedtime",
        "domains": ["blocked.example"],
        "enabled": True,
        "ip_addresses": [],
        "ip_ranges": [
            {
                "ip_start": "192.168.1.100",
                "ip_stop": "192.168.1.110",
                "ip_version": "v4",
            }
        ],
        "matching_target": "INTERNET",
        "network_ids": [],
        "regions": [],
        "schedule": {
            "date_end": "",
            "date_start": "",
            "mode": "ALWAYS",
            "repeat_on_days": [],
            "time_all_day": True,
            "time_range_end": "",
            "time_range_start": "",
        },
        "target_devices": [
            {
                "client_mac": "aa:bb:cc:dd:ee:01",
                "type": "CLIENT",
            }
        ],
    }
    record.update(overrides)
    return record


def nat_rule_record(**overrides: Any) -> dict[str, Any]:
    """Return a synthetic NAT rule (reference-derived, not live-observed)."""
    record: dict[str, Any] = {
        "_id": "nat-dns",
        "type": "DNAT",
        "description": "All DNS to resolver",
        "enabled": True,
        "rule_index": 3,
        "protocol": "tcp_udp",
        "ip_version": "IPV4",
        "in_interface": "6f0000000000000000000010",
        "ip_address": "192.0.2.53",
        "port": "53",
        "logging": False,
        "exclude": False,
        "is_predefined": False,
        "setting_preference": "manual",
        "pppoe_use_base_interface": False,
        "source_filter": {
            "filter_type": "NONE",
            "firewall_group_ids": [],
            "invert_address": False,
            "invert_port": False,
        },
        "destination_filter": {
            "filter_type": "ADDRESS_AND_PORT",
            "firewall_group_ids": [],
            "invert_address": True,
            "invert_port": False,
            "address": "192.0.2.54",
            "port": "53",
        },
    }
    record.update(overrides)
    return record


def static_route_record(**overrides: Any) -> dict[str, Any]:
    """Return a synthetic static route (reference-derived, not live-observed)."""
    record: dict[str, Any] = {
        "_id": "route-lab",
        "site_id": "classic-site-id",
        "name": "Lab",
        "enabled": True,
        "type": "static-route",
        "static-route_type": "interface-route",
        "static-route_network": "192.168.2.0/24",
        "static-route_interface": "600ee7cccccccccccccccccc",
        "gateway_type": "default",
        "gateway_device": "aa:bb:cc:dd:ee:ff",
        "static-route_distance": 1,
    }
    record.update(overrides)
    return record


def static_route_next_hop_record(**overrides: Any) -> dict[str, Any]:
    """Return synthetic next-hop static route (reference-derived, not live-observed)."""
    record: dict[str, Any] = {
        "_id": "route-nexthop",
        "site_id": "classic-site-id",
        "name": "NextHop",
        "enabled": True,
        "type": "static-route",
        "static-route_type": "nexthop-route",
        "static-route_network": "198.51.100.0/24",
        "static-route_nexthop": "192.0.2.1",
        "gateway_type": "default",
        "gateway_device": "aa:bb:cc:dd:ee:ff",
        "static-route_distance": "",
    }
    record.update(overrides)
    return record
