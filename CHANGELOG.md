# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- **Breaking:** `TalkbackStream` no longer takes the unused third positional argument; everything after `media_source` is keyword-only, so `TalkbackStream(session, url, hass)` raises `TypeError` (#47). Migration: `TalkbackStream(session, url, loop=hass.loop)` or `TalkbackStream(session, url, executor=hass.async_add_executor_job)`.
- **Breaking:** the `TalkbackStream.media_url` compatibility alias is removed (#47). Migration: read `media_source`.

### Changed

- `TalkbackStream` documents its `loop` and `executor` keywords: the worker runs in a dedicated daemon thread unless `executor` (an awaitable-returning callable such as `hass.async_add_executor_job`) is given (#47).
- `pre-commit run --all-files` passes again on Python 3.14: every hook is updated to its current release, mypy checks the whole package like CI, pyupgrade targets 3.14 (dropping the now redundant `from __future__ import annotations`), and `tests/fixtures/` is no longer checked as test modules.

## [2.0.0] - 2026-10-18

### Added

- **v2.0.0 Architecture & Endpoint Uplift (Issue #41)**:
  - Full Python ≥ 3.14 compatibility with strict static typing across all 173 source modules (`mypy src/ --strict`).
  - Protect API expansion: cameras (with backward-compatible snapshot endpoint), alarm hubs, bridges, chimes, door locks, fobs, lights, link stations, live views, NVR, POS, relays, sensors, sirens, speakers, users, ULP users, viewers, talkback transcode/streaming, and WebSocket subscriptions.
  - Network API expansion: firewall policies, static routes, LAGs, NAT rules, port forwards, traffic rules, vouchers, and VPN clients.
  - Innerspace, Carrier Fabric, Mobility, and Site Manager client and endpoint additions.
  - Strict ≥ 95% per-file branch coverage enforcement (`script/check_coverage_per_file.py`) with 3,263 tests passing at 100.00% total branch and statement coverage across all 173 source files with zero `# pragma: no cover` additions.

### Fixed

- Fixed release workflow tag validation f-string syntax in `.github/workflows/release.yml`.
- Updated `.pre-commit-config.yaml` pyupgrade hook to `--py312-plus`.

### Security

- Requires aiohttp 3.14.3 or later (was capped below 3.14.0), fixing the aiohttp advisories that affected every version the old range allowed. The lock file also moves to multidict 7.1.0, urllib3 2.8.0 and virtualenv 21.14.7, clearing their advisories. Home Assistant core already ships aiohttp 3.14.5.
- The test suite works with aiohttp 3.14 through a small shim for aioresponses 0.7.9, whose response builder does not pass aiohttp 3.14's new `stream_writer` argument (pnuckowski/aioresponses#288). The Dependabot rule that ignored aiohttp 3.14 is removed.

### Changed

- Pull requests get path labels and at most one type label, `bug` or `enhancement`, from the shared tinkerologie PR labeler. Dependabot pull requests whose largest update is a patch or minor version merge automatically once the checks and commit statuses on their head commit have finished without a failure (a Codecov check that is still pending is not waited for; a Codecov failure blocks); majors, and pull requests with open review threads, stay for review.
- Dependabot updates `uv.lock` (the `uv` ecosystem instead of `pip`), so version and security updates reach the lock file.
- Release workflows hardened (least-privilege job permissions, no expressions in shell scripts, no persisted checkout credentials, no dependency caches); scheduled workflows run on Australia/Brisbane time. Relicensed from MIT to the Apache License 2.0; NOTICE retains the MIT notice for earlier releases.
- Tinkerologie-Bot governance report updated to v1.4.3: an older run can no longer post a stale report after a newer run passed. Workflow formatting tidied.
- Repository standardised to the tinkerologie layout (STANDARDS.md in tinkerologie/.github): workflows renamed to the standard set (CI, Validate, Release, PR Governance, ...), every action pinned to a commit SHA, shared Dependabot, `.editorconfig`, `.gitattributes` and `CODEOWNERS` files, and organization-wide labels and community files.
- Tinkerologie-Bot's comment is now a readable "Pull request checklist": each problem is a numbered heading with plain-English guidance and its items listed underneath, and report updates for a pull request are serialised so an older run can never overwrite a newer one.
- Contribution governance: issues without a `bug` or `enhancement` label are labeled automatically when their type can be determined (issues labeled `question`, `duplicate`, `invalid`, `wontfix`, or `no-type` are skipped), so CodeRabbit can plan them. Pull requests that conflict with the default branch are labeled, and their authors are notified in a comment. Stale issues and pull requests are labeled after 14 days without activity and closed 30 days later. PR governance now re-validates a human-authored, non-draft PR when a bot such as CodeRabbit edits its description, instead of skipping the check and reporting a pass, only maintainers with write access may use `None` instead of linking an issue, and a link to an issue that does not exist now fails the check. Codecov patch coverage must now reach 90%.
- Tinkerologie-Bot now posts one comment on pull requests that fail PR governance, listing every problem to fix, and updates it once they are fixed. PR governance runs from the default branch's workflow (`pull_request_target`), so a pull request cannot change its own check.
- Configured Codecov GitHub Actions workflow for tokenless coverage uploads

## [1.4.0] - 2026-08-26

### Added

#### Full Official UniFi API Coverage (6 Suites)

- **UniFi Network API**:
  - **Switching**: Complete switching management (`client.switching`)
    - `get_lags()` / `get_lag()`: List and retrieve Link Aggregation Groups (LAGs)
    - `get_mc_lag_domains()` / `get_mc_lag_domain()`: List and retrieve Multi-Chassis LAG (MC-LAG) domains
    - `get_switch_stacks()` / `get_switch_stack()`: List and retrieve Switch Stacks and member units
    - Models: `Lag`, `LagMember`, `LagType`, `LagPage`, `McLagDomain`, `McLagPeer`, `McLagDomainPage`, `SwitchStack`, `SwitchStackMember`, `SwitchStackPage`

- **UniFi Protect API**:
  - **Sirens**: `client.sirens` for managing siren devices (`get_all`, `get`, `update`, `play`, `stop`, `test_sound`)
  - **Key Fobs**: `client.fobs` for managing key fobs (`get_all`, `get`, `update`)
  - **Relays**: `client.relays` for managing relay devices and output activation (`get_all`, `get`, `update`, `activate_output`)
  - **Speakers**: `client.speakers` for managing Protect speakers and test sounds (`get_all`, `get`, `update`, `test_sound`)
  - **Bridges & Link Stations**: `client.bridges` and `client.link_stations` for managing bridges and link stations
  - **Alarm Hubs & Alarm Manager**: `client.alarm_hubs` for alarm hub devices and output triggers, and `client.alarm_manager` for alarm manager webhook dispatch
  - **Arm Profiles**: `client.arm_profiles` for arm profile lifecycle, global arm settings, enable, and disable
  - **Users**: `client.users` for local Protect users and UniFi Identity (ULP) users (`get_users`, `get_user`, `get_ulp_users`, `get_ulp_user`)
  - **Point of Sale (POS)**: `client.pos` for ingesting POS transactions overlaid onto camera footage (`ingest_transaction`)
  - Models: `Siren`, `Fob`, `Relay`, `Speaker`, `Bridge`, `LinkStation`, `AlarmHub`, `ArmProfile`, `ArmProfileSettings`, `ProtectUser`, `ULPUser`, `POSTransactionRequest`, `POSLineItem`, `POSLocation`

- **UniFi InnerSpace API (`UniFiInnerSpaceClient`)**:
  - New dedicated client supporting direct `LOCAL` and cloud `REMOTE` connections
  - **Project**: `client.project.get()` for full RF geometry, wall types, and attenuation shapes
  - **Floor Plans**: `client.floor_plans.get_all()` for floor plan definitions and scale
  - **Placed APs & Switches**: `client.access_points.get_all()` and `client.switches.get_all()` for placed network hardware coordinates
  - **Inventory**: `client.inventory.get_all()` for unplaced hardware devices
  - **Blueprint Assets**: `client.assets.download()` for downloading floor plan raster blueprint images
  - Models: `ProjectData`, `ProjectMeta`, `FloorPlan`, `InnerSpaceAccessPoint`, `InnerSpaceMountType`, `InnerSpaceSwitch`, `InventoryDevice`

- **UniFi Site Manager API (`UniFiSiteManagerClient`)**:
  - New dedicated client for cloud-level console management via `https://api.ui.com`
  - **Hosts**: `client.hosts.get_all()`, `client.hosts.get()` for registered console hosts
  - **Sites**: `client.sites.get_all()` for cross-console site aggregation
  - **Devices**: `client.devices.get_all()` for cross-console device inventories
  - **ISP Metrics**: `client.isp_metrics.get_metrics()`, `client.isp_metrics.query()` for WAN performance telemetry
  - **SD-WAN**: `client.sd_wan.get_configs()`, `client.sd_wan.get_config()`, `client.sd_wan.get_status()` for SD-WAN topologies and tunnel health
  - **Cloud Connector**: `client.connector.proxy()` for proxying arbitrary HTTP requests to remote consoles
  - Models: `Host`, `HostUserData`, `HostReportedState`, `HostListResponse`, `SiteManagerSite`, `SiteListResponse`, `SiteManagerDevice`, `SiteManagerHostDevices`, `DeviceListResponse`, `ISPMetric`, `ISPMetricQuery`, `ISPMetricQueryResult`, `SDWanConfig`, `SDWanConfigDetail`, `SDWanStatus`

- **UniFi Mobility API (`UniFiMobilityClient`)**:
  - New dedicated client for UMR cellular gateway router fleets via `https://api.ui.com`
  - **Workspaces & Admins**: `client.workspaces.get_all()`, `client.workspaces.get_admins()`
  - **Device Gateways**: `client.devices.get_all()`, `client.devices.get()`, `client.devices.update_name()` with GPS location coordinates
  - **Connected Clients**: `client.clients.get_all()` for connected wireless and wired client monitoring
  - **Remote Network & Wireless**: `client.network.update()` for LAN/DHCP settings and `client.wireless.update()` for WiFi SSIDs/passwords
  - Models: `WorkspaceSummary`, `AdminSummary`, `AdminPermission`, `MobilityDeviceSummary`, `MobilityDeviceDetail`, `DeviceLocation`, `MobilityDeviceClient`, `UpdateDeviceNameReq`, `UpdateNetworkReq`, `UpdateWirelessReq`

- **UniFi Carrier Fabric API (`UniFiCarrierFabricClient`)**:
  - New dedicated client for ISP subscriber provisioning via `https://api.ui.com`
  - **Subscribers**: `client.subscribers.get_all()`, `create()`, `get()`, `update()`, `attach_host()`, `detach_host()`, `assign_plan()`, `suspend()`, `resume()`
  - **Service Plans**: `client.service_plans.get_all()`, `get()` for bandwidth and QoS plans
  - Models: `Subscriber`, `SubscriberCreate`, `SubscriberPatch`, `HostLinkResponse`, `SubscriberListResponse`, `ServicePlan`, `ServicePlanListResponse`, `Meta`

### Changed

- Update repository URLs and documentation references to tinkerologie organization.

- Modernized `(str, Enum)` definitions across all network and protect models to standard Python 3.11+ `StrEnum`
- Exported all 6 official clients (`UniFiNetworkClient`, `UniFiProtectClient`, `UniFiInnerSpaceClient`, `UniFiSiteManagerClient`, `UniFiMobilityClient`, `UniFiCarrierFabricClient`) from root `unifi_official_api` package
- Updated `pyproject.toml` dependency constraint `aiohttp>=3.9.0,<3.14.0` for `aioresponses` mock compatibility
- Expanded unit test suite to 657 tests with 96% overall code coverage

## [1.3.0] - 2026-03-30

### Added

#### Network API

- **Sites**: `get_legacy_all()` method for retrieving raw legacy site dictionaries from `/self/sites`
- **Auto-pagination**: `clients.get_all()` and `firewall.list_rules()` now automatically paginate to retrieve all results when called without explicit `offset`/`limit` parameters
- **Device model**: Added `DeviceState.GETTING_READY` state and flexible `state`/`type` fields accepting raw strings for forward compatibility with new device states

### Changed

- Update repository URLs and documentation references to tinkerologie organization.

#### Network API

- **REMOTE URL paths**: Removed `/proxy/` prefix from REMOTE connector URLs — the connector now adds this during forwarding
- **Lazy console_id validation**: Network client no longer raises at `__init__` when `console_id` is missing for REMOTE connections; validation deferred to when API paths are built, allowing `get_hosts()` without a console_id
- **`firewall.update_rule()`**: Changed from PATCH to GET+PUT pattern for compatibility with current UniFi controller versions
- **`firewall.patch_rule()`**: **Breaking behavioral change** — no longer performs an HTTP PATCH / partial update. `patch_rule()` now delegates to `update_rule()`, which fetches the full rule via GET and writes it back via PUT. Fields not included in the call may be overwritten with server defaults. Callers relying on partial-update semantics should switch to `update_rule()` with all desired fields, or implement a custom read-modify-write workflow
- **`wifi.update()`**: Changed from PATCH to GET+PUT pattern for compatibility with current UniFi controller versions
- **PoE port metrics**: `get_port_metrics()` now requires `port_poe` flag on port data before including PoE metrics

#### Protect API

- **REMOTE URL paths**: Removed `/proxy/` prefix from REMOTE connector URLs
- **REMOTE site paths**: REMOTE Protect API paths no longer include `/sites/{site_id}/` segments; all Protect endpoints now use site-agnostic paths

### Removed

- **`devices.execute_port_action()`**: Removed non-functional method

## [1.2.0] - 2026-02-17

### Added

#### Network API

- **DNS Policies**: DNS policy management
  - `get_all()`: List all DNS policies with pagination and filtering
  - `get()`: Get specific DNS policy
  - `create()`: Create DNS record (A, AAAA, CNAME, MX, TXT, SRV, forward domain)
  - `update()`: Update existing DNS policy
  - `delete()`: Remove DNS policy

- **Firewall Policy**: Advanced firewall policy operations
  - `patch_rule()`: Partial update of firewall policy fields
  - `get_policy_ordering()`: Get user-defined policy ordering for zone pair
  - `update_policy_ordering()`: Reorder policies (before/after system-defined)

- **ACL Rule Ordering**: ACL rule priority management
  - `get_ordering()`: Get current ACL rule order
  - `update_ordering()`: Reorder user-defined ACL rules

### Changed

- Update repository URLs and documentation references to tinkerologie organization.

- `FirewallRule.action` now accepts both dict format (`{"type": "ALLOW", "allowReturnTraffic": true}`) and legacy string format for API v10+ compatibility
- Added `FirewallActionConfig` model to parse structured firewall action responses from newer API versions

### Fixed

- **Protect API**: Fixed `Sensor.battery_status` field type - now correctly parses as `BatteryStatus` model with `percentage` and `is_low` fields instead of string
- **Network API**: Added missing `params` parameter support to `_put()` method in base client (required for firewall policy ordering endpoints)
- DNS endpoint now properly handles both `DNSRecordType` enum and string values for `record_type` parameter

## [1.1.0] - 2025-01-22

### Added

#### Network API

- **Vouchers**: Hotspot voucher management
  - `get_all()`: List vouchers with pagination and filtering
  - `get()`: Get specific voucher details
  - `create()`: Generate new vouchers with rate limits and time restrictions
  - `delete()`: Delete single voucher
  - `delete_multiple()`: Bulk delete vouchers

- **ACL Rules**: Access control list management
  - `get_all()`: List ACL rules
  - `get()`: Get specific rule
  - `create()`: Create new rule with source/destination filters
  - `update()`: Modify existing rule
  - `delete()`: Remove rule

- **Traffic Matching**: Traffic matching lists and DPI
  - `get_all_lists()`: List traffic matching lists
  - `get_list()`: Get specific list details
  - `create_list()`: Create IP/port/domain lists
  - `update_list()`: Modify list entries
  - `delete_list()`: Remove list
  - `get_dpi_categories()`: Get DPI categories
  - `get_dpi_applications()`: Get DPI applications
  - `get_countries()`: Get countries for geo-blocking

- **Resources**: Supporting network resources
  - `get_wan_interfaces()`: List WAN interfaces with filter support
  - `get_vpn_tunnels()`: List site-to-site VPN tunnels with filter support
  - `get_vpn_servers()`: List VPN servers (WireGuard, OpenVPN, L2TP) with filter support
  - `get_radius_profiles()`: List RADIUS profiles with filter support
  - `get_device_tags()`: List device tags with filter support

- **Firewall Enhancements**:
  - `get_zone()`: Get specific firewall zone
  - `create_zone()`: Create custom firewall zone
  - `update_zone()`: Update firewall zone
  - `delete_zone()`: Delete custom firewall zone
  - Added pagination and filter support to `list_zones()` and `list_rules()`

- **Networks Enhancements**:
  - `get_references()`: Get references to a network (what uses a network)

- **Device Actions**: Device management operations
  - `execute_port_action()`: Control device ports (enable/disable PoE, speed)
  - `execute_action()`: Device actions (restart, locate, adopt, forget)
  - `get_pending_adoption()`: List devices pending adoption
  - `get_statistics()`: Get device statistics

- **Client Actions**: Client management operations
  - `execute_action()`: Client actions (block, unblock, reconnect, forget)

- **Application Info**: `get_application_info()` method on client

- **Filter Query Support**: All list endpoints now support the UniFi filter query syntax
  - Property expressions: `id.eq(123)`, `name.like('guest*')`
  - Compound expressions: `and(name.isNull(), createdAt.gt(2025-01-01))`
  - Negation expressions: `not(name.like('guest*'))`

#### Protect API

- **Viewers**: Viewport device management
  - `get_all()`: List all viewers
  - `get()`: Get specific viewer
  - `update()`: Modify viewer settings
  - `set_liveview()`: Set viewer's current liveview

- **Application**: System management
  - `get_info()`: Get Protect application info
  - `get_files()`: List device asset files
  - `upload_file()`: Upload animation/asset files
  - `trigger_alarm_webhook()`: Trigger alarm manager webhook

- **Camera Enhancements**:
  - `ptz_patrol_start()`: Start PTZ patrol on slot
  - `ptz_patrol_stop()`: Stop PTZ patrol
  - `ptz_goto_preset()`: Move camera to PTZ preset position
  - `create_rtsps_stream()`: Create RTSPS stream for camera (requires `qualities` parameter)
  - `get_rtsps_stream()`: Get existing RTSPS stream info
  - `delete_rtsps_stream()`: Remove RTSPS stream
  - `create_talkback_session()`: Create two-way audio session
  - `disable_mic_permanently()`: Permanently disable camera microphone
  - `set_hdr_mode()`: Set HDR mode (off, auto, always)
  - `set_video_mode()`: Set video mode (default, highFps, sport)
  - `get_snapshot()`: Retrieve camera snapshot image
  - `construct_rtsp_url()`: Helper method to construct RTSP URLs for cameras

- **WebSocket Subscriptions**: Real-time event streaming
  - `subscribe_devices()`: Subscribe to device state updates
  - `subscribe_events()`: Subscribe to Protect events
  - `get_host_id()`: Helper method to get host ID for WebSocket subscriptions

### Changed

- Update repository URLs and documentation references to tinkerologie organization.

- Renamed `list()` methods to `get_all()` to avoid shadowing Python built-in
- Standardized filter parameter naming to `filter_str` across all endpoints
- Fixed `create_rtsps_stream()` to require `qualities` parameter per API spec
- Fixed `delete_rtsps_stream()` to pass qualities as query parameters
- Fixed WAN interfaces endpoint path from `/wan` to `/wans`
- Fixed `ClientType` enum serialization to return string values instead of enum objects
- Made WAN/VPN model fields optional for better API compatibility

### Fixed

- RTSPS stream creation now properly sends `qualities` in request body
- Client type field now returns string ("WIRED"/"WIRELESS") instead of enum object
- WAN interfaces API now uses correct endpoint path

## [1.0.0] - 2025-01-17

### Added

- Initial release with async Python library for UniFi APIs
- UniFi Network API support:
  - Hosts management
  - Sites management
  - Devices (list, get, update, restart)
  - Clients (list, get)
  - Networks (CRUD)
  - WiFi/WLAN (CRUD)
  - Firewall rules (CRUD)
- UniFi Protect API support:
  - Cameras (list, get, update, PTZ control)
  - Lights (list, get, update)
  - Sensors (list, get, update)
  - Chimes (list, get, update)
  - Liveviews (CRUD)
  - Events (list, get, download)
  - NVR (get, update)
- API Key authentication
- Pydantic v2 models for all API responses
- Full type annotations with strict mypy compliance
- Comprehensive test suite with 95%+ coverage
- Modern Python packaging with pyproject.toml
