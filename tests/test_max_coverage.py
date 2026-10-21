"""Comprehensive edge-case and branch coverage tests."""

from __future__ import annotations

from unittest.mock import patch

import aiohttp
import pytest
from aioresponses import aioresponses

from unifi_official_api import ApiKeyAuth, ConnectionType, LocalAuth
from unifi_official_api.carrier_fabric.models import HostLinkResponse, Subscriber
from unifi_official_api.exceptions import (
    UniFiConnectionError,
    UniFiError,
    UniFiResponseError,
    UniFiTimeoutError,
    UniFiValidationError,
)
from unifi_official_api.innerspace import UniFiInnerSpaceClient
from unifi_official_api.innerspace.endpoints.assets import _validate_asset_segment
from unifi_official_api.innerspace.endpoints.floor_plans import FloorPlansEndpoint
from unifi_official_api.innerspace.models.access_point import InnerSpaceMountType
from unifi_official_api.mobility import UniFiMobilityClient
from unifi_official_api.mobility.models.config import UpdateDeviceNameReq
from unifi_official_api.network import UniFiNetworkClient
from unifi_official_api.network.endpoints.vouchers import _validate_voucher
from unifi_official_api.network.models.acl import ACLRule
from unifi_official_api.network.models.client import Client
from unifi_official_api.network.models.dns import DNSPolicy, DNSPolicyMetadata, DNSPolicyType
from unifi_official_api.network.models.firewall import (
    FirewallAction,
    FirewallActionConfig,
    FirewallRule,
    FirewallZone,
)
from unifi_official_api.network.models.nat_rule import is_predefined_nat_rule
from unifi_official_api.protect import UniFiProtectClient
from unifi_official_api.protect.models.files import RTSPSStream
from unifi_official_api.protect.models.liveview import LiveView, LiveViewSlot
from unifi_official_api.protect.models.nvr import NVR, StorageInfo
from unifi_official_api.site_manager import UniFiSiteManagerClient
from unifi_official_api.site_manager.models.isp_metric import ISPMetricQuery


class TestMaxCoverage:
    """Tests for edge cases across all modules to reach >98% coverage."""

    @pytest.fixture
    def net_client(self) -> UniFiNetworkClient:
        return UniFiNetworkClient(
            auth=LocalAuth(api_key="key", verify_ssl=False),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        )

    @pytest.fixture
    def net_remote_client(self) -> UniFiNetworkClient:
        return UniFiNetworkClient(
            auth=ApiKeyAuth(api_key="key"),
            connection_type=ConnectionType.REMOTE,
            console_id="console-123",
        )

    @pytest.fixture
    def prot_client(self) -> UniFiProtectClient:
        return UniFiProtectClient(
            auth=LocalAuth(api_key="key", verify_ssl=False),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        )

    @pytest.fixture
    def prot_remote_client(self) -> UniFiProtectClient:
        return UniFiProtectClient(
            auth=ApiKeyAuth(api_key="key"),
            connection_type=ConnectionType.REMOTE,
            console_id="console-123",
        )

    @pytest.fixture
    def innerspace_client(self) -> UniFiInnerSpaceClient:
        return UniFiInnerSpaceClient(
            auth=LocalAuth(api_key="key", verify_ssl=False),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        )

    @pytest.fixture
    def mobility_client(self) -> UniFiMobilityClient:
        return UniFiMobilityClient(
            auth=ApiKeyAuth(api_key="key"),
            base_url="https://api.ui.com",
        )

    @pytest.fixture
    def site_manager_client(self) -> UniFiSiteManagerClient:
        return UniFiSiteManagerClient(
            auth=ApiKeyAuth(api_key="key"),
            base_url="https://api.ui.com",
        )

    async def test_network_client_branches(
        self,
        net_client: UniFiNetworkClient,
        net_remote_client: UniFiNetworkClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test network client remote paths and edge cases."""
        assert (
            net_remote_client.build_api_path("/sites")
            == "/v1/connector/consoles/console-123/network/integration/v1/sites"
        )
        assert net_remote_client.console_id == "console-123"

        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites?filter=name%3DDefault",
            payload={"data": [{"id": "default", "name": "Default", "isOwner": True}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/devices/dev-1/statistics/latest",
            payload={"data": {"cpu": 15.2, "memory": 45.0}},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/api/self/sites",
            payload={"data": [{"name": "default"}]},
        )

        async with net_client:
            sites = await net_client.sites.get_all(filter_str="name=Default")
            assert len(sites) == 1

            legacy_sites = await net_client.sites.get_legacy_all()
            assert len(legacy_sites) == 1

            stats = await net_client.devices.get_statistics("default", "dev-1")
            assert stats.get("cpu") == 15.2

    async def test_protect_client_extended_branches(
        self,
        prot_client: UniFiProtectClient,
        prot_remote_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test protect client and endpoint branches."""
        assert (
            prot_remote_client.build_api_path("/cameras")
            == "/v1/connector/consoles/console-123/protect/integration/v1/cameras"
        )

        # Protect list single object unwrapping
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/hub-1",
            payload={"data": [{"id": "hub-1", "name": "Hub List Item"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges/bridge-1",
            payload={"data": [{"id": "bridge-1", "name": "Bridge List Item"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations/station-1",
            payload={"data": [{"id": "station-1", "name": "Station List Item"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers/spk-1",
            payload={"data": [{"id": "spk-1", "name": "Speaker List Item"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/siren-1",
            payload={"data": [{"id": "siren-1", "name": "Siren List Item"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/fobs/fob-1",
            payload={"data": [{"id": "fob-1", "name": "Fob List Item"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/relays/relay-1",
            payload={"data": [{"id": "relay-1", "name": "Relay List Item"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/users/u-1",
            payload={"data": {"id": "u-1", "name": "User List Item"}},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/ulp-users/ulp-1",
            payload={
                "data": {
                    "id": "ulp-1",
                    "firstName": "A",
                    "lastName": "B",
                    "fullName": "A B",
                    "status": "ACTIVE",
                }
            },
        )

        async with prot_client:
            hub = await prot_client.alarm_hubs.get("hub-1")
            assert hub.id == "hub-1"

            br = await prot_client.bridges.get("bridge-1")
            assert br.id == "bridge-1"

            ls = await prot_client.link_stations.get("station-1")
            assert ls.id == "station-1"

            spk = await prot_client.speakers.get("spk-1")
            assert spk.id == "spk-1"

            sr = await prot_client.sirens.get("siren-1")
            assert sr.id == "siren-1"

            fb = await prot_client.fobs.get("fob-1")
            assert fb.id == "fob-1"

            rl = await prot_client.relays.get("relay-1")
            assert rl.id == "relay-1"

            u = await prot_client.users.get_user("u-1")
            assert u.id == "u-1"

            ulp = await prot_client.ulp_users.get("ulp-1")
            assert ulp.id == "ulp-1"

    async def test_protect_models_and_endpoints(
        self,
        prot_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test Protect models properties and endpoint dict site_id."""
        # LiveView camera_ids
        lv = LiveView(
            id="lv1",
            name="Test LV",
            slots=[LiveViewSlot(cameras=["cam1", "cam2"]), LiveViewSlot(cameras=["cam3"])],
        )
        assert lv.camera_ids == ["cam1", "cam2", "cam3"]

        # RTSPSStream available_qualities
        stream = RTSPSStream(high="rtsps://high", low="rtsps://low")
        assert stream.available_qualities == ["high", "low"]

        # NVR storage serialization and display_name
        nvr = NVR(
            id="nvr1",
            mac="AA:BB:CC:DD:EE:FF",
            name="Main NVR",
            storage_info=StorageInfo(total_size=1000, used_size=500),
        )
        dump = nvr.model_dump(by_alias=True)
        assert "storageInfo" in dump
        assert nvr.display_name == "Main NVR"
        nvr_no_name = NVR(id="nvr2", mac="11:22:33:44:55:66")
        assert nvr_no_name.display_name == "11:22:33:44:55:66"

        # ApplicationEndpoint.upload_file without data raises ValueError
        with pytest.raises(ValueError, match="File data is required"):
            await prot_client.application.upload_file(file_data=None, data=None)

        # ApplicationEndpoint.ingest_pos_transaction
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/pos/cameras/cam-1/transactions",
            payload={"data": {"created": True, "eventId": "evt-1"}},
        )
        async with prot_client:
            pos_resp = await prot_client.application.ingest_pos_transaction(
                "cam-1",
                {"type": "sale", "externalId": "tx-100", "amount": 42.0},
            )
            assert pos_resp.created is True
            assert pos_resp.event_id == "evt-1"

        # ProtectDeviceEndpoint update with keyword settings; AlarmHubsEndpoint
        # still accepts settings as a dict in the site_id position
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges/br-1",
            payload={"data": {"id": "br-1", "name": "Bridge Patched"}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/hub-1",
            payload={"data": {"id": "hub-1", "name": "Hub Patched"}},
        )
        async with prot_client:
            b_updated = await prot_client.bridges.update("br-1", name="Bridge Patched")
            assert b_updated.name == "Bridge Patched"

            h_updated = await prot_client.alarm_hubs.update(
                "hub-1",
                {"name": "Hub Patched"},
            )
            assert h_updated.name == "Hub Patched"

    async def test_innerspace_models_and_endpoints(
        self,
        innerspace_client: UniFiInnerSpaceClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test InnerSpace models, endpoints, and client methods."""
        # InnerSpaceMountType
        assert InnerSpaceMountType("ceiling") == InnerSpaceMountType.CEILING
        assert InnerSpaceMountType._missing_("nonexistent") is None
        assert InnerSpaceMountType._missing_(123) is None

        # _validate_asset_segment
        assert _validate_asset_segment("valid_segment") == "valid_segment"
        with pytest.raises(UniFiValidationError):
            _validate_asset_segment("../bad")
        with pytest.raises(UniFiValidationError):
            _validate_asset_segment("")
        assert FloorPlansEndpoint._validate_asset_segment("valid") == "valid"

        # innerspace_client._unwrap_object
        assert UniFiInnerSpaceClient._unwrap_object({"data": {"key": "val"}}, endpoint="test") == {
            "key": "val"
        }
        assert UniFiInnerSpaceClient._unwrap_object({"direct": "val"}, endpoint="test") == {
            "direct": "val"
        }
        with pytest.raises(UniFiResponseError):
            UniFiInnerSpaceClient._unwrap_object("not a dict", endpoint="test")

        # ApplicationEndpoint
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/innerspace/integration/v1/info",
            payload={"data": {"version": "1.2.3", "application": "innerspace"}},
        )
        async with innerspace_client:
            info = await innerspace_client.application.get_info()
            assert info.version == "1.2.3"

            # ApplicationEndpoint invalid response raises ValueError
            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/info",
                payload={"data": "invalid"},
            )
            with pytest.raises(ValueError, match="Unable to retrieve InnerSpace application info"):
                await innerspace_client.application.get_info()

            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/info",
                payload=None,
            )
            with pytest.raises(ValueError, match="Unable to retrieve InnerSpace application info"):
                await innerspace_client.application.get_info()

            # floor_plans.get_project
            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/project",
                payload={"data": {"id": "proj-1"}},
            )
            proj = await innerspace_client.floor_plans.get_project()
            assert proj.id == "proj-1"

            # floor_plans.download_image and get_image
            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/assets/plan-1/image.png",
                body=b"pngdata",
                headers={"Content-Type": "image/png"},
            )
            img_bytes, ct = await innerspace_client.floor_plans.download_image(
                "plan-1", "image.png"
            )
            assert img_bytes == b"pngdata"
            assert ct == "image/png"

            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/assets/plan-1/image.png",
                body=b"pngdata",
                headers={"Content-Type": "image/png"},
            )
            img = await innerspace_client.floor_plans.get_image("plan-1", "image.png")
            assert img == b"pngdata"

            # inventory.get_inventory
            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/inventory",
                payload={"data": [{"id": "inv-1", "mac": "11:22:33:44:55:66"}]},
            )
            inv = await innerspace_client.inventory.get_inventory()
            assert len(inv) == 1
            assert inv[0].id == "inv-1"

            # client.get_inventory and client.get_application_info
            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/inventory",
                payload={"data": [{"id": "inv-2", "mac": "11:22:33:44:55:77"}]},
            )
            inv2 = await innerspace_client.get_inventory()
            assert len(inv2) == 1

            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/info",
                payload={"data": {"version": "2.0.0"}},
            )
            app_info2 = await innerspace_client.get_application_info()
            assert app_info2.version == "2.0.0"

            # _list_collection with malformed item logs warning and skips
            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/inventory",
                payload={"data": [{"id": "good", "mac": "AA:BB"}, {"id": ""}]},
            )
            inv_filtered = await innerspace_client.inventory.list()
            assert len(inv_filtered) == 1

            # get_binary success and errors
            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/binary-data",
                body=b"binary_content",
                status=200,
            )
            bin_data = await innerspace_client.get_binary(
                "/proxy/innerspace/integration/v1/binary-data"
            )
            assert bin_data == b"binary_content"

            mock_aioresponse.get(
                "https://192.168.1.1/proxy/innerspace/integration/v1/binary-data-404",
                status=404,
            )
            with pytest.raises(UniFiResponseError) as not_found:
                await innerspace_client.get_binary(
                    "/proxy/innerspace/integration/v1/binary-data-404"
                )
            assert not_found.value.status_code == 404

            # get_binary timeout
            with patch.object(aiohttp.ClientSession, "get", side_effect=TimeoutError()):
                with pytest.raises(UniFiTimeoutError):
                    await innerspace_client.get_binary(
                        "/proxy/innerspace/integration/v1/binary-data-timeout"
                    )

            # get_binary client error
            with patch.object(
                aiohttp.ClientSession, "get", side_effect=aiohttp.ClientConnectionError("boom")
            ):
                with pytest.raises(UniFiConnectionError):
                    await innerspace_client.get_binary(
                        "/proxy/innerspace/integration/v1/binary-data-err"
                    )

    async def test_mobility_and_site_manager_branches(
        self,
        mobility_client: UniFiMobilityClient,
        site_manager_client: UniFiSiteManagerClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test mobility and site manager fallback branches."""
        # Mobility workspaces non-list fallback
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces",
            payload={"data": "not a list"},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/admins",
            payload={"data": "not a list"},
        )
        # Mobility clients non-list fallback
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1/clients",
            payload={"data": "not a list"},
        )
        # Mobility devices non-list fallback and get error
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices",
            payload={"data": "not a list"},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-missing",
            payload={"data": {}},
        )
        mock_aioresponse.put(
            "https://api.ui.com/v1/mobility/workspaces/ws-1/devices/dev-1",
            payload={"data": {"id": "dev-1"}},
        )
        async with mobility_client:
            assert await mobility_client.workspaces.get_all() == []
            assert await mobility_client.workspaces.get_admins("ws-1") == []
            assert await mobility_client.clients.get_all("ws-1", "dev-1") == []
            assert await mobility_client.devices.get_all("ws-1") == []
            with pytest.raises(ValueError, match="not found in workspace"):
                await mobility_client.devices.get("ws-1", "dev-missing")

            await mobility_client.devices.update_name(
                "ws-1", "dev-1", UpdateDeviceNameReq(name="NewName")
            )

        # Site manager sdwan property
        assert site_manager_client.sdwan is site_manager_client.sd_wan

        # Site manager validate_connection error handling
        with patch.object(site_manager_client, "_get", side_effect=UniFiError("fail")):
            assert await site_manager_client.validate_connection() is False
        with patch.object(site_manager_client, "_get", side_effect=ValueError("fail")):
            assert await site_manager_client.validate_connection() is False

        # Site manager isp_metrics non-list fallback and query
        mock_aioresponse.get(
            "https://api.ui.com/v1/isp-metrics/latency",
            payload={"data": "not a list"},
        )
        mock_aioresponse.post(
            "https://api.ui.com/v1/isp-metrics/latency/query",
            payload={"data": "not a dict"},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/sd-wan-configs",
            payload={"data": "not a list"},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/sd-wan-configs/cfg-missing",
            payload={"data": {}},
        )
        mock_aioresponse.get(
            "https://api.ui.com/v1/sd-wan-configs/cfg-missing/status",
            payload={"data": {}},
        )
        async with site_manager_client:
            metrics = await site_manager_client.isp_metrics.get_metrics("latency")
            assert metrics == []

            query_res = await site_manager_client.isp_metrics.query("latency", ISPMetricQuery())
            assert query_res.metrics == []

            configs = await site_manager_client.sd_wan.get_configs()
            assert configs == []

            with pytest.raises(ValueError, match="SD-WAN config cfg-missing not found"):
                await site_manager_client.sd_wan.get_config("cfg-missing")

            mock_aioresponse.get(
                "https://api.ui.com/v1/sd-wan-configs/cfg-none",
                payload=None,
            )
            with pytest.raises(ValueError, match="SD-WAN config cfg-none not found"):
                await site_manager_client.sd_wan.get_config("cfg-none")

            with pytest.raises(ValueError, match="SD-WAN status for cfg-missing not found"):
                await site_manager_client.sd_wan.get_status("cfg-missing")

            mock_aioresponse.get(
                "https://api.ui.com/v1/sd-wan-configs/cfg-none/status",
                payload=None,
            )
            with pytest.raises(ValueError, match="SD-WAN status for cfg-none not found"):
                await site_manager_client.sd_wan.get_status("cfg-none")

    async def test_network_models_and_switching(
        self,
        net_client: UniFiNetworkClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test network switching, models fallback, and device metrics."""
        # SwitchingEndpoint
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/lags/lag-missing",
            payload={"data": {}},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/mc-lag-domains?offset=10",
            payload={"data": []},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/mc-lag-domains/mclag-missing",
            payload={"data": {}},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks?offset=10",
            payload={"data": []},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks/stack-missing",
            payload={"data": {}},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/lags",
            status=200,
            payload=None,
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/mc-lag-domains",
            status=200,
            payload=None,
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/integration/v1/sites/default/switching/switch-stacks",
            status=200,
            payload=None,
        )
        # Device get_legacy_device_stats with non-list port_table
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/api/s/default/stat/device/11:22:33:44:55:66",
            payload={"data": [{"port_table": "not a list"}]},
        )

        async with net_client:
            with pytest.raises(ValueError, match="LAG lag-missing not found"):
                await net_client.switching.get_lag("default", "lag-missing")

            mc_page = await net_client.switching.get_mc_lag_domains("default", offset=10)
            assert mc_page.data == []

            with pytest.raises(ValueError, match="MC-LAG domain mclag-missing not found"):
                await net_client.switching.get_mc_lag_domain("default", "mclag-missing")

            stacks_page = await net_client.switching.get_switch_stacks("default", offset=10)
            assert stacks_page.data == []

            with pytest.raises(ValueError, match="Switch stack stack-missing not found"):
                await net_client.switching.get_switch_stack("default", "stack-missing")

            assert (await net_client.switching.get_lags("default")).data == []
            assert (await net_client.switching.get_mc_lag_domains("default")).data == []
            assert (await net_client.switching.get_switch_stacks("default")).data == []

            port_metrics = await net_client.devices.get_port_metrics("default", "11:22:33:44:55:66")
            assert port_metrics.poe_ports == {}

        # Vouchers _validate_voucher invalid
        with pytest.raises(ValueError, match="Invalid voucher data"):
            _validate_voucher({"quota": "invalid_number_type"})

        # NAT rules is_predefined_nat_rule
        assert is_predefined_nat_rule("not a dict") is False
        assert is_predefined_nat_rule({"is_predefined": True}) is True
        assert is_predefined_nat_rule({"setting_preference": "auto"}) is True
        assert is_predefined_nat_rule({"setting_preference": "manual"}) is False

        # ACL rule
        acl = ACLRule(
            id="acl1", name="AllowWeb", action="ALLOW", metadata={"origin": "USER_DEFINED"}
        )
        assert acl.display_name == "AllowWeb (ALLOW)"
        assert acl.is_user_defined is True
        acl_sys = ACLRule(id="acl2", name="SysBlock", action="BLOCK", metadata={"origin": "SYSTEM"})
        assert acl_sys.is_user_defined is False
        acl_str = ACLRule(id="acl3", name="StrMeta", action="BLOCK")
        object.__setattr__(acl_str, "metadata", "string_meta")
        assert acl_str.is_user_defined is False

        # Client model
        assert Client._populate_id_fallback("non-dict") == "non-dict"
        c1 = Client.model_validate({"_id": "c-1", "mac": "aa:bb:cc", "name": "Phone"})
        assert c1.id == "c-1"
        assert c1.ip_address is None
        assert c1.mac_address == "aa:bb:cc"
        c2 = Client.model_validate({"macAddress": "11:22:33"})
        assert c2.id == "11:22:33"

        # DNS policy
        assert DNSPolicyType._missing_("a_record") == DNSPolicyType.A_RECORD
        assert DNSPolicyType._missing_("invalid") is None
        assert DNSPolicyType._missing_(99) is None
        dns_p = DNSPolicy(
            id="dns-1",
            type=DNSPolicyType.A_RECORD,
            ipv4_address="1.2.3.4",
            domain="example.com",
            metadata={"origin": "USER_DEFINED"},
        )
        assert dns_p.is_user_defined is True
        assert dns_p.value == "1.2.3.4"
        assert dns_p.display_name == "example.com (A_RECORD: 1.2.3.4)"
        dns_p2 = DNSPolicy(
            id="dns-2",
            type="TXT_RECORD",
            domain="test.com",
            metadata=DNSPolicyMetadata(origin="SYSTEM"),
        )
        assert dns_p2.is_user_defined is False
        assert dns_p2.display_name == "test.com (TXT_RECORD)"
        dns_p3 = DNSPolicy(id="dns-3", type="TXT_RECORD", metadata=None)
        assert dns_p3.is_user_defined is False

        # Firewall models
        assert FirewallAction._missing_("allow") == FirewallAction.ALLOW
        assert FirewallAction._missing_("invalid") is None
        assert FirewallAction._missing_(99) is None

        assert FirewallRule._populate_id_fallback("non-dict") == "non-dict"
        fw_rule = FirewallRule.model_validate(
            {"_id": "fw-1", "name": "DropAll", "action": {"type": "DROP"}}
        )
        assert fw_rule.id == "fw-1"
        assert fw_rule.action_type == "DROP"
        assert fw_rule.display_name == "DropAll"

        fw_rule2 = FirewallRule.model_validate(
            {
                "id": "fw-2",
                "name": "AcceptHTTP",
                "action": FirewallActionConfig(type=FirewallAction.ACCEPT),
            }
        )
        assert fw_rule2.action_type == "accept"

        fw_rule3 = FirewallRule.model_validate(
            {"id": "fw-3", "name": "BlockSSH", "action": FirewallAction.BLOCK}
        )
        assert fw_rule3.action_type == "BLOCK"

        assert FirewallZone._populate_id_fallback("non-dict") == "non-dict"
        fw_zone = FirewallZone.model_validate({"_id": "zone-1", "name": "Internal"})
        assert fw_zone.id == "zone-1"
        assert fw_zone.display_name == "Internal"

        # Carrier Fabric HostLinkResponse.data
        sub = Subscriber(id="sub-1", first_name="John", last_name="Doe")
        resp = HostLinkResponse(subscriber=sub)
        assert resp.data == sub
