# UniFi Official API

[![PyPI version](https://badge.fury.io/py/unifi-official-api.svg)](https://badge.fury.io/py/unifi-official-api)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![codecov](https://codecov.io/gh/tinkerologie/unifi-official-api/branch/main/graph/badge.svg)](https://codecov.io/gh/tinkerologie/unifi-official-api)

This Python library sends asynchronous requests to these UniFi APIs.

- **UniFi Network API** (v10.4.57+)
- **UniFi Protect API** (v7.2.105+)
- **UniFi InnerSpace API** (v1.3.23+)
- **UniFi Site Manager API** (v1.0.0+)
- **UniFi Mobility API** (v1.0.0+)
- **UniFi Carrier Fabric API** (v1.0.0+)
- **UniFi Access API**

## Features

- The library uses `aiohttp` for asynchronous requests.
- The library uses Pydantic v2 models. The type check uses `mypy --strict`.
- Clients can connect to a local console or use the UniFi cloud connector.
- Home Assistant and other Python applications can use these clients.

## Requirements

- Python 3.14 or a subsequent version
- A local or cloud API key. Get a cloud key from
  [developer.ui.com](https://developer.ui.com). Get a local key on your console.

## Installation

```bash
pip install unifi-official-api
```

## Quick Start

**Warning.** Use a trusted certificate when possible. The examples with
`verify_ssl=False` disable certificate verification. An attacker can then
intercept the API key.

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
        if not sites:
            return
        devices = await client.devices.get_all(sites[0].id)
        for device in devices:
            print(f"Device: {device.name} ({device.mac})")

asyncio.run(main())
```

#### Network 11 WAN traffic history

Call `await client.stats.get_source()` to read the statistics engine. For
`source.root == "MODERN"`, call `client.stats.get_recent_series()` with
`schema="wanBySite"` and the Classic site `_id` from
`client.sites.get_legacy_all()`. Set `period` to `HOUR`, `DAY`, `WEEK`, or `MONTH`
and set `end_ms` to the end of the interval in Unix milliseconds. Add the byte
totals of each bucket to calculate traffic totals. Use the reported duration
for the newest bucket, which can be partial.

These controller-wide routes are outside the published Integration API.
Use an admin API key. A View-Only key gets HTTP 403.

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

        nvr = await client.nvr.get()
        if nvr.use_external_alarm_manager:
            profiles = await client.external_arm_profiles.get_all()
            print(f"External arm profiles: {len(profiles)}")

asyncio.run(main())
```

To stop a siren that is playing on a speaker, call `stop_siren` with the ID of
that speaker. This silences an active alarm without a confirmation, so call it
only from an explicit user action:

```python
await client.speakers.stop_siren("speaker-id")
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
        metrics = await client.isp_metrics.get_metrics("5m", duration="24h")
        print(f"First pages: {len(hosts.data)} consoles and {len(sites.data)} sites")

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
        if not workspaces:
            return
        ws_id = workspaces[0].workspace_id
        devices = await client.devices.get_all(ws_id)
        print(f"Found {len(devices)} mobile routers")

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
        print(f"Loaded {len(subscribers)} subscribers and {len(plans)} service plans")

asyncio.run(main())
```

## Site Manager and Mobility read methods

| Resource | Typed method and result | Dictionary method and result |
| --- | --- | --- |
| Site Manager hosts | `hosts.get_all()` returns one `HostListResponse` page. Pass its `next_token` to the next call. | `list_hosts()` returns host dictionaries from all pages. |
| Site Manager host detail | `hosts.get()` returns one `Host`. | `get_host()` returns one dictionary. |
| Site Manager ISP metrics | `isp_metrics.get_metrics()` returns `list[ISPMetric]` in one call. | `get_isp_metrics()` returns a list of dictionaries in one call. |
| Site Manager ISP query | `isp_metrics.query()` returns `ISPMetricQueryResult` in one call. | `query_isp_metrics()` returns the `data` dictionary in one call. |
| Mobility workspaces | `workspaces.get_all()` returns `list[WorkspaceSummary]` in one call. | `list_workspaces()` returns a list of dictionaries in one call. |
| Mobility workspace admins | `workspaces.get_admins()` returns `list[AdminSummary]` in one call. | `list_workspace_admins()` returns a list of dictionaries in one call. |
| Mobility devices | `devices.get_all()` returns one page as `list[MobilityDeviceSummary]`. Pass `limit` and `offset` to read subsequent pages. | `list_devices()` returns device dictionaries from all pages. |
| Mobility device detail | `devices.get()` returns one `MobilityDeviceDetail`. | `get_device()` returns one dictionary. |
| Mobility connected clients | `clients.get_all()` returns one page as `list[MobilityDeviceClient]`. | `list_device_clients()` returns connected client dictionaries from all pages. |

For typed hosts, stop when `next_token` is empty or `None`. For typed Mobility devices, set `limit` from 1 to 200 and start at `offset=0`. Increase `offset` by the number of records received. Stop when a page is shorter than `limit`. Use `list_device_clients()` to read all connected clients. The Mobility API uses 200 as the default page size for devices and connected clients.

The dictionary methods in the table preserve missing keys and explicit `0` and `False` values. Typed models can supply defaults for missing fields. Check `model_fields_set` for fields such as `is_blocked`, `model`, `state`, and `status` to see which values the API supplied.

### ISP metrics intervals and site queries

Use `5m` for five-minute samples and `1h` for hourly samples. The API accepts `duration="24h"` for `5m` and `duration="7d"` or `duration="30d"` for `1h`. To specify a time range, use timezone-aware `begin_timestamp` and `end_timestamp` arguments. The API rejects a duration combined with either timestamp.

Each `ISPMetric` record identifies a host and site. Its `periods` contain timestamped samples. A sample can include measurements in `period.data.wan`. A missing `periods` field gives `None`, and an empty periods list gives `[]`. A missing WAN measurement gives `None`. A measurement of zero gives `0`.

To query selected sites, supply each site's host ID and site ID. Each site can also have a timezone-aware time range.

```python
from unifi_official_api.site_manager import ISPMetricQuery, ISPMetricQuerySite

query = ISPMetricQuery(sites=[ISPMetricQuerySite(host_id=host_id, site_id=site_id)])
result = await client.isp_metrics.query("1h", query)
if result.status == "partialSuccess":
    print(result.message)
```

The API can return accessible metrics with `status="partialSuccess"` and a message. The published query uses the `sites` body. Existing dictionary payloads and legacy typed query fields still pass through. The legacy fields `hostIds`, `timeRangeStart`, and `timeRangeEnd` and the legacy GET filter `hostId` are outside the published schema. Use `sites` on its own when building a typed site query.

## API Coverage Summary

| Client / API | Endpoints / Resources Covered |
| -------------- | ------------------------------- |
| **UniFiNetworkClient** | Sites, Devices, Clients, Networks, WiFi/SSIDs, Firewall & Zones, Vouchers, ACL Rules, Switching (LAGs, MC-LAG domains, Switch Stacks), Traffic Matching, Resources (WAN, VPN, RADIUS) |
| **UniFiProtectClient** | Cameras (streams, snapshots, PTZ, talkback), sirens, key fobs, relays, speakers (test sound, stop siren), bridges, link stations, alarm hubs, Alarm Manager webhooks, arm profiles, and external alarm manager arm profiles.<br>Local and Identity users, POS transactions, sensors, lights, chimes, read-only NVR, liveviews, viewers, and device, event and unified update WebSockets. |
| **UniFiInnerSpaceClient** | Full Project Data (Shapes, Walls, Attenuation), Floor Plans, Placed Access Points, Placed Switches, Unplaced Inventory, Blueprint Image Assets |
| **UniFiSiteManagerClient** | Hosts/Consoles, Multi-site Aggregation, Cross-console Devices, ISP Performance Telemetry & Queries, SD-WAN Configs & Health Status, Cloud Connector Arbitrary Proxy |
| **UniFiMobilityClient** | Workspaces, Workspace Admins, Mobile routers and location coordinates, Connected Clients, Remote LAN/DHCP Configuration, Remote Wireless WiFi Configuration |
| **UniFiAccessClient** | Doors and lock rules, device lists, emergency state, user PIN and status changes, webhooks, notification WebSocket |
| **UniFiCarrierFabricClient** | Subscribers Lifecycle (Create, Update, Suspend, Resume), Gateway Host Attach/Detach, Service Plan Assignment, Bandwidth QoS Service Plans |

Access uses its own bearer token. The default console port is 12445.

An offline test compares the HTTP methods and paths from public Protect calls
with the OpenAPI fixture for `PROTECT_SPEC_VERSION` (7.4.96). The test skips
`client.close` and `chimes.play` because they send no requests. The test checks
only methods and paths.

External alarm manager arm profiles need an NVR that reports
`nvr.use_external_alarm_manager is True`. When the flag is false, Protect runs
the local alarm manager and the external endpoints refuse requests.
The property keeps `nvr.feature_flags` compatible with existing dictionary access.
The value is also available at `nvr.feature_flags["useExternalAlarmManager"]`
when Protect supplies the key.
`client.speakers.stop_siren` stops a siren playing on a speaker.
`client.websocket.subscribe_updates` sends one `modelKeys` query pair per key
and yields raw add, update and remove messages:

```python
async with client.websocket.subscribe_updates(["camera", "event"]) as updates:
    async for message in updates:
        print(message)
```

## Error Handling

The library raises these exceptions for API errors. This example uses a
Network client and a Network site ID.

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
    devices = await client.devices.get_all(site_id)
except UniFiAuthenticationError:
    print("The API key is invalid or lacks permission")
except UniFiConnectionError:
    print("Failed to connect to API")
except UniFiTimeoutError:
    print("Request timed out")
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

The client raises `UniFiConnectionError` if the connection fails. It raises
`UniFiTimeoutError` if the request times out.

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
Remote Network discovery with `get_hosts()` needs no `console_id`.

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
    console_id="your-console-id",  # Required for console paths in remote Network mode
    timeout=30,
    connect_timeout=10,
)
```

### Local Protect Installation

Use this configuration for a direct connection to a local Protect console.
For a remote Protect connection, give `console_id` when you create the client.

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

The development extra installs pre-commit. Use these commands to install
the Git hooks and run them on all files.

```bash
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
