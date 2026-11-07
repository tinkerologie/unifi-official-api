# UniFi Official API

[![PyPI version](https://badge.fury.io/py/unifi-official-api.svg)](https://badge.fury.io/py/unifi-official-api)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![codecov](https://codecov.io/gh/tinkerologie/unifi-official-api/branch/main/graph/badge.svg)](https://codecov.io/gh/tinkerologie/unifi-official-api)

This Python library sends asynchronous requests to these UniFi APIs.

- **UniFi Network API** (v10.4.57+)
- **UniFi Protect API** (v7.2.105+)
- **UniFi InnerSpace API** (v1.3.23+)
- **UniFi Site Manager API** (v1.0.0+)
- **UniFi Mobility API** (v1.0.0+)
- **UniFi Carrier Fabric API** (v1.0.0+)

## Features

- The library uses `aiohttp` for asynchronous requests.
- The library uses Pydantic v2 models and passes `mypy --strict`.
- Clients can connect to a local console or use the UniFi cloud connector.
- Home Assistant and other Python applications can use these clients.

## Requirements

- Python 3.11 or higher
- A local or cloud API key. Get a cloud key from
  [developer.ui.com](https://developer.ui.com). Get a local key on your console.

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
| **UniFiProtectClient** | Cameras (Streams, Snapshots, PTZ Presets & Patrols, Talkback), Sirens, Key Fobs, Relays, Speakers, Bridges, Link Stations, Alarm Hubs, Alarm Manager Webhooks, Arm Profiles, Local & Identity Users, POS Transaction Ingestion, Sensors, Lights, Chimes, NVR (read-only), LiveViews, Viewers, Real-time Device & Event WebSockets |
| **UniFiInnerSpaceClient** | Full Project Data (Shapes, Walls, Attenuation), Floor Plans, Placed Access Points, Placed Switches, Unplaced Inventory, Blueprint Image Assets |
| **UniFiSiteManagerClient** | Hosts/Consoles, Multi-site Aggregation, Cross-console Devices, ISP Performance Telemetry & Queries, SD-WAN Configs & Health Status, Cloud Connector Arbitrary Proxy |
| **UniFiMobilityClient** | Workspaces, Workspace Admins, UMR Device Gateways & Location Coordinates, Connected Clients, Remote LAN/DHCP Configuration, Remote Wireless WiFi Configuration |
| **UniFiCarrierFabricClient** | Subscribers Lifecycle (Create, Update, Suspend, Resume), Gateway Host Attach/Detach, Service Plan Assignment, Bandwidth QoS Service Plans |

`UniFiProtectClient` uses operations from the Protect OpenAPI specification.
`PROTECT_SPEC_VERSION` gives the specification version (7.3.70). A test compares
each public Protect method with the copy of the specification in this repository.

## Error Handling

Use these exceptions to respond to errors.

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

`UniFiNotFoundError` shows that the server returned HTTP 404 or HTTP 200
without a record. If a record fails validation, the client raises
`UniFiResponseError` with `status_code == 200`. The message gives only the field
names. Network rule and route listings with `strict=True` raise
`UniFiValidationError` for invalid records.

For HTTP errors, including errors for binary downloads, the client raises
these exceptions.

| HTTP status | Exception |
| --- | --- |
| 401 or 403 | `UniFiAuthenticationError` |
| 404 | `UniFiNotFoundError` |
| 429 | `UniFiRateLimitError` |
| Other 4xx or 5xx | `UniFiResponseError` or a subclass |

If the client cannot reach the console, it raises `UniFiConnectionError` or
`UniFiTimeoutError`. Invalid arguments can cause `ValueError` or `TypeError`
before the client sends the request.

### Protect listing completeness

Use the result of the request to decide if a missing record can cause removal.

```python
result = await client.cameras.get_all_result()
if result.complete:
    reconcile_inventory(result.records)
```

`records` is a tuple in response order. `skipped` gives the number of records
that fail validation. `shape_valid` is true if the response is a list or if
its `data` field is a list. `complete` is true if `shape_valid` is true and
`skipped` is zero. A valid empty list is complete. HTTP and transport failures
raise the usual exceptions.

The legacy `get_all()` method returns a list. Concurrent calls to that method
use the same `last_result_complete` attribute. Liveview and file listings
validate each record and raise an exception if validation fails.

### Shared request budgets

Protect and Mobility clients have independent request budgets by default.
Use one budget for clients on the same event loop and server quota.

```python
budget = UniFiProtectClient.create_request_budget()
first = UniFiProtectClient(auth, base_url=console_url, request_budget=budget)
second = UniFiProtectClient(auth, base_url=console_url, request_budget=budget)
```

The budget controls when the clients can start requests. It also shares
short delays after HTTP 429 responses. A budget applies to one application,
connection mode, origin, and route prefix. For remote Protect, it also
applies to one console ID. Use the same credential scope for the clients
that share a budget. Use a budget in one event loop and one process.

## Configuration Options

### Network client

These examples show local and remote configurations for the Network client.

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

Use this configuration for a direct connection to a local Protect console.

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

Read the [glossary](GLOSSARY.md) for project terms. Read the
[architecture decisions](docs/adr/README.md) for the design of the library.

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

The pre-commit hooks run these checks before each commit.

- **Ruff** - Linting and formatting
- **Mypy** - Static type checking
- **Bandit** - Security vulnerability scanning
- **Markdownlint** - Markdown file linting
- **Codespell** - Spell checking
- **Pyupgrade** - Python syntax modernization
- **File checks** - YAML, TOML, JSON validation, trailing whitespace, etc.

Use these commands to install the pre-commit hooks.

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# (Optional) Run against all files
pre-commit run --all-files
```

If a check fails, Git stops the commit. Correct the errors before you try again.

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

Read the [contributor guide](CONTRIBUTING.md) before you submit a pull request.

## License

This project uses the Apache License 2.0. See [LICENSE](LICENSE). Earlier releases used the MIT license. See [NOTICE](NOTICE).

## Disclaimer

This is an unofficial library. UniFi is a trademark of Ubiquiti Inc. Ubiquiti Inc. has no affiliation with this project and does not endorse or sponsor it.

## Related Projects

- [Home Assistant](https://www.home-assistant.io/) - Open source home automation
- [UniFi Developer Documentation](https://developer.ui.com/) - Official API documentation
