# UniFi Official API

[![PyPI version](https://badge.fury.io/py/unifi-official-api.svg)](https://badge.fury.io/py/unifi-official-api)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![codecov](https://codecov.io/gh/tinkerologie/unifi-official-api/branch/main/graph/badge.svg)](https://codecov.io/gh/tinkerologie/unifi-official-api)

Async Python library for the official UniFi APIs:

- **UniFi Network API** (v10.4.57+)
- **UniFi Protect API** (v7.2.105+)
- **UniFi InnerSpace API** (v1.3.23+)
- **UniFi Site Manager API** (v1.0.0+)
- **UniFi Mobility API** (v1.0.0+)
- **UniFi Carrier Fabric API** (v1.0.0+)

## Features

- **Async-first**: Built with `aiohttp` for efficient non-blocking operations
- **Strict Typing**: 100% typed, passing `mypy --strict` with Pydantic v2 models
- **Full Coverage**: Comprehensive support for all 6 official UniFi API suites
- **Dual Connection Support**: Works locally with direct device consoles or via `api.ui.com` cloud integrations
- **Home Assistant & Automation Ready**: Designed for clean integration into automation environments

## Requirements

> **Python 3.11 or higher is required.**

- Python 3.11, 3.12, or 3.13
- UniFi API Key from [developer.ui.com](https://developer.ui.com) or generated locally on your console

## Installation

```bash
pip install unifi-official-api
```

## Quick Start

### 1. UniFi Network Client (Local / Cloud)

```python
import asyncio
from unifi_official_api import LocalAuth, ConnectionType
from unifi_official_api.network import UniFiNetworkClient

async def main():
    async with UniFiNetworkClient(
        auth=LocalAuth(api_key="your-local-api-key", verify_ssl=False),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    ) as client:
        sites = await client.sites.get_all()
        devices = await client.devices.get_all(sites[0].id)
        for device in devices:
            print(f"Device: {device.name} ({device.mac})")

asyncio.run(main())
```

### 2. UniFi Protect Client (Cameras, Sirens, Chimes, Relays, POS)

```python
import asyncio
from unifi_official_api import LocalAuth, ConnectionType
from unifi_official_api.protect import UniFiProtectClient

async def main():
    async with UniFiProtectClient(
        auth=LocalAuth(api_key="your-local-api-key", verify_ssl=False),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    ) as client:
        cameras = await client.cameras.get_all()
        for cam in cameras:
            print(f"Camera: {cam.display_name}")

asyncio.run(main())
```

### 3. UniFi InnerSpace Client (Floor Plans, AP/Switch Placements)

```python
import asyncio
from unifi_official_api import LocalAuth, ConnectionType
from unifi_official_api.innerspace import UniFiInnerSpaceClient

async def main():
    async with UniFiInnerSpaceClient(
        auth=LocalAuth(api_key="your-local-api-key", verify_ssl=False),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    ) as client:
        plans = await client.floor_plans.get_all()
        aps = await client.access_points.get_all()
        print(f"Loaded {len(plans)} floor plans and {len(aps)} placed APs")

asyncio.run(main())
```

### 4. UniFi Site Manager Client (Cloud Multi-Site & Telemetry)

```python
import asyncio
from unifi_official_api import ApiKeyAuth
from unifi_official_api.site_manager import UniFiSiteManagerClient

async def main():
    async with UniFiSiteManagerClient(
        auth=ApiKeyAuth(api_key="your-cloud-api-key")
    ) as client:
        hosts = await client.hosts.get_all()
        sites = await client.sites.get_all()
        metrics = await client.isp_metrics.get_metrics("latency", duration="24h")
        print(f"Monitored {len(hosts.data)} consoles across {len(sites.data)} sites")

asyncio.run(main())
```

### 5. UniFi Mobility Client (UMR Gateways & Fleets)

```python
import asyncio
from unifi_official_api import ApiKeyAuth
from unifi_official_api.mobility import UniFiMobilityClient

async def main():
    async with UniFiMobilityClient(
        auth=ApiKeyAuth(api_key="your-cloud-api-key")
    ) as client:
        workspaces = await client.workspaces.get_all()
        ws_id = workspaces[0].workspace_id
        devices = await client.devices.get_all(ws_id)
        print(f"Found {len(devices)} mobility gateways")

asyncio.run(main())
```

### 6. UniFi Carrier Fabric Client (ISP Subscribers & Plans)

```python
import asyncio
from unifi_official_api import ApiKeyAuth
from unifi_official_api.carrier_fabric import UniFiCarrierFabricClient

async def main():
    async with UniFiCarrierFabricClient(
        auth=ApiKeyAuth(api_key="your-cloud-api-key")
    ) as client:
        subscribers = await client.subscribers.get_all()
        plans = await client.service_plans.get_all()
        print(f"Loaded {len(subscribers.data)} subscribers and {len(plans)} service plans")

asyncio.run(main())
```

## API Coverage Summary

| Client / API | Endpoints / Resources Covered |
| -------------- | ------------------------------- |
| **UniFiNetworkClient** | Sites, Devices, Clients, Networks, WiFi/SSIDs, Firewall & Zones, Vouchers, ACL Rules, Switching (LAGs, MC-LAG domains, Switch Stacks), Traffic Matching, Resources (WAN, VPN, RADIUS) |
| **UniFiProtectClient** | Cameras (Streams, Snapshots, PTZ, Talkback), Sirens, Key Fobs, Relays, Speakers, Bridges, Link Stations, Alarm Hubs, Alarm Manager Webhooks, Arm Profiles, Local & Identity Users, POS Transaction Ingestion, Sensors, Lights, Chimes, NVR, LiveViews, Viewers, Real-time WebSockets |
| **UniFiInnerSpaceClient** | Full Project Data (Shapes, Walls, Attenuation), Floor Plans, Placed Access Points, Placed Switches, Unplaced Inventory, Blueprint Image Assets |
| **UniFiSiteManagerClient** | Hosts/Consoles, Multi-site Aggregation, Cross-console Devices, ISP Performance Telemetry & Queries, SD-WAN Configs & Health Status, Cloud Connector Arbitrary Proxy |
| **UniFiMobilityClient** | Workspaces, Workspace Admins, UMR Device Gateways & Location Coordinates, Connected Clients, Remote LAN/DHCP Configuration, Remote Wireless WiFi Configuration |
| **UniFiCarrierFabricClient** | Subscribers Lifecycle (Create, Update, Suspend, Resume), Gateway Host Attach/Detach, Service Plan Assignment, Bandwidth QoS Service Plans |

## Error Handling

The library provides specific exceptions for different error types:

```python
from unifi_official_api import (
    UniFiError,
    UniFiAuthenticationError,
    UniFiConnectionError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiTimeoutError,
)

try:
    devices = await client.devices.get_all(host_id)
except UniFiAuthenticationError:
    print("Invalid API key")
except UniFiConnectionError:
    print("Failed to connect to API")
except UniFiRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except UniFiNotFoundError:
    print("Resource not found")
except UniFiError as e:
    print(f"API error: {e.message}")
```

## Configuration Options

Both clients accept the following configuration options:

```python
from unifi_official_api import LocalAuth, ConnectionType
from unifi_official_api.network import UniFiNetworkClient

# Local connection
client = UniFiNetworkClient(
    auth=LocalAuth(
        api_key="your-local-api-key",
        verify_ssl=False,  # For self-signed certificates
    ),
    base_url="https://192.168.1.1",  # Your device IP
    connection_type=ConnectionType.LOCAL,
    timeout=30,  # Request timeout in seconds
    connect_timeout=10,  # Connection timeout in seconds
)

# Remote/Cloud connection
from unifi_official_api import ApiKeyAuth

client = UniFiNetworkClient(
    auth=ApiKeyAuth(api_key="your-cloud-api-key"),
    connection_type=ConnectionType.REMOTE,
    console_id="your-console-id",  # Required for REMOTE connections
    timeout=30,
    connect_timeout=10,
)
```

### Local Protect Installation

For connecting directly to a local UniFi Protect installation:

```python
from unifi_official_api import LocalAuth
from unifi_official_api.protect import UniFiProtectClient

client = UniFiProtectClient(
    auth=LocalAuth(
        api_key="local-api-key",
        verify_ssl=False,  # Disable SSL verification for self-signed certs
    ),
    base_url="https://192.168.1.1:7443",
)
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/tinkerologie/unifi-official-api.git
cd unifi-official-api

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (recommended)
pre-commit install

# Run tests
pytest

# Run linting
ruff check src tests

# Run type checking
mypy src
```

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality before commits. The hooks automatically run:

- **Ruff** - Linting and formatting
- **Mypy** - Static type checking
- **Bandit** - Security vulnerability scanning
- **Markdownlint** - Markdown file linting
- **Codespell** - Spell checking
- **Pyupgrade** - Python syntax modernization
- **File checks** - YAML, TOML, JSON validation, trailing whitespace, etc.

To set up pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# (Optional) Run against all files
pre-commit run --all-files
```

Once installed, the hooks will automatically run on every commit. If any check fails, the commit will be blocked until you fix the issues.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=unifi_official_api --cov-report=html

# Run specific test file
pytest tests/network/test_client.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details. Earlier releases were MIT licensed; see [NOTICE](NOTICE).

## Disclaimer

This is an unofficial library. UniFi is a trademark of Ubiquiti Inc. This project is not affiliated with, endorsed by, or sponsored by Ubiquiti Inc.

## Related Projects

- [Home Assistant](https://www.home-assistant.io/) - Open source home automation
- [UniFi Developer Documentation](https://developer.ui.com/) - Official API documentation
