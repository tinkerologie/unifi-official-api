"""Tests for newly added UniFi Protect endpoints."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from unifi_official_api import ConnectionType, LocalAuth
from unifi_official_api.exceptions import UniFiNotFoundError, UniFiResponseError
from unifi_official_api.protect import (
    AlarmHub,
    ArmProfile,
    ArmProfileSettings,
    Bridge,
    Fob,
    LinkStation,
    POSTransactionRequest,
    ProtectUser,
    Relay,
    Siren,
    Speaker,
    ULPUser,
    UniFiProtectClient,
)


class TestProtectExtendedEndpoints:
    """Tests for extended Protect endpoints."""

    @pytest.fixture
    def client(self) -> UniFiProtectClient:
        """Create a local protect client."""
        return UniFiProtectClient(
            auth=LocalAuth(api_key="test-key", verify_ssl=False),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        )

    async def test_sirens_endpoints(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test sirens endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens",
            payload={"data": [{"id": "siren-1", "name": "Main Siren", "volume": 90}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/siren-1",
            payload={"data": {"id": "siren-1", "name": "Main Siren", "volume": 90}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/siren-1",
            payload={"data": {"id": "siren-1", "name": "Main Siren Updated", "volume": 100}},
            repeat=True,
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/siren-1/play",
            status=200,
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/siren-1/stop",
            status=200,
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/siren-1/test-sound",
            status=200,
        )

        async with client:
            sirens = await client.sirens.get_all()
            assert len(sirens) == 1
            assert isinstance(sirens[0], Siren)

            siren = await client.sirens.get("siren-1")
            assert siren.id == "siren-1"

            updated = await client.sirens.update("siren-1", volume=100)
            assert updated.volume == 100

            await client.sirens.play("siren-1", duration=10)
            await client.sirens.set_volume("siren-1", 80)
            await client.sirens.stop("siren-1")
            await client.sirens.test_sound("siren-1")

    async def test_sirens_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test sirens empty and error branches."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/bad-id", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/bad-id", payload={}
        )
        # The empty PATCH body makes update() re-fetch the resource.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/sirens/bad-id",
            payload={"data": {"id": "bad-id"}},
        )

        async with client:
            assert await client.sirens.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.sirens.get("bad-id")
            updated = await client.sirens.update("bad-id", volume=50)
            assert updated.id == "bad-id"

    async def test_fobs_endpoints(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test fobs endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/fobs",
            payload={"data": [{"id": "fob-1", "name": "Key 1"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/fobs/fob-1",
            payload={"data": {"id": "fob-1", "name": "Key 1"}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/fobs/fob-1",
            payload={"data": {"id": "fob-1", "name": "Key 1 Updated"}},
        )

        async with client:
            fobs = await client.fobs.get_all()
            assert len(fobs) == 1
            assert isinstance(fobs[0], Fob)

            fob = await client.fobs.get("fob-1")
            assert fob.name == "Key 1"

            updated = await client.fobs.update("fob-1", name="Key 1 Updated")
            assert updated.name == "Key 1 Updated"

    async def test_fobs_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test fobs empty and error branches."""
        mock_aioresponse.get("https://192.168.1.1/proxy/protect/integration/v1/fobs", payload=None)
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/fobs/bad-id", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/fobs/bad-id", payload={}
        )
        # The empty PATCH body makes update() re-fetch the resource.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/fobs/bad-id",
            payload={"data": {"id": "bad-id"}},
        )

        async with client:
            assert await client.fobs.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.fobs.get("bad-id")
            updated = await client.fobs.update("bad-id", name="x")
            assert updated.id == "bad-id"

    async def test_relays_endpoints(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test relays endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/relays",
            payload={
                "data": [
                    {"id": "relay-1", "name": "Gate Relay", "outputs": [{"id": 1, "state": "OPEN"}]}
                ]
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/relays/relay-1",
            payload={
                "data": {
                    "id": "relay-1",
                    "name": "Gate Relay",
                    "outputs": [{"id": 1, "state": "OPEN"}],
                }
            },
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/relays/relay-1",
            payload={"data": {"id": "relay-1", "name": "Gate Relay 2"}},
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/relays/relay-1/outputs/1/activate",
            status=200,
        )

        async with client:
            relays = await client.relays.get_all()
            assert len(relays) == 1
            assert isinstance(relays[0], Relay)
            assert len(relays[0].outputs) == 1

            relay = await client.relays.get("relay-1")
            assert relay.id == "relay-1"

            updated = await client.relays.update("relay-1", name="Gate Relay 2")
            assert updated.name == "Gate Relay 2"

            await client.relays.activate_output("relay-1", 1, duration_ms=500)

    async def test_relays_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test relays error branches."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/relays", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/relays/bad-id", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/relays/bad-id", payload={}
        )
        # The empty PATCH body makes update() re-fetch the resource.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/relays/bad-id",
            payload={"data": {"id": "bad-id"}},
        )

        async with client:
            assert await client.relays.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.relays.get("bad-id")
            updated = await client.relays.update("bad-id", name="x")
            assert updated.id == "bad-id"

    async def test_speakers_endpoints(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test speakers endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers",
            payload={"data": [{"id": "spk-1", "name": "Horn Speaker", "volume": 80}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers/spk-1",
            payload={"data": {"id": "spk-1", "name": "Horn Speaker", "volume": 80}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers/spk-1",
            payload={"data": {"id": "spk-1", "name": "Horn Speaker 2", "volume": 95}},
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers/spk-1/test-sound",
            status=200,
        )

        async with client:
            speakers = await client.speakers.get_all()
            assert len(speakers) == 1
            assert isinstance(speakers[0], Speaker)

            spk = await client.speakers.get("spk-1")
            assert spk.id == "spk-1"

            updated = await client.speakers.update("spk-1", volume=95)
            assert updated.volume == 95

            await client.speakers.test_sound("spk-1")

    async def test_speakers_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test speakers error branches."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers/bad-id", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers/bad-id", payload={}
        )
        # The empty PATCH body makes update() re-fetch the resource.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/speakers/bad-id",
            payload={"data": {"id": "bad-id"}},
        )

        async with client:
            assert await client.speakers.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.speakers.get("bad-id")
            updated = await client.speakers.update("bad-id", volume=10)
            assert updated.id == "bad-id"

    async def test_bridges_endpoints(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test bridges endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges",
            payload={"data": [{"id": "bridge-1", "name": "Bridge 1"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges/bridge-1",
            payload={"data": {"id": "bridge-1", "name": "Bridge 1"}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges/bridge-1",
            payload={"data": {"id": "bridge-1", "name": "Bridge Updated"}},
        )

        async with client:
            bridges = await client.bridges.get_all()
            assert len(bridges) == 1
            assert isinstance(bridges[0], Bridge)

            br = await client.bridges.get("bridge-1")
            assert br.id == "bridge-1"

            up = await client.bridges.update("bridge-1", name="Bridge Updated")
            assert up.name == "Bridge Updated"

    async def test_bridges_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test bridges error branches."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges/bad-id", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges/bad-id", payload={}
        )
        # The empty PATCH body makes update() re-fetch the resource.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/bridges/bad-id",
            payload={"data": {"id": "bad-id"}},
        )

        async with client:
            assert await client.bridges.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.bridges.get("bad-id")
            updated = await client.bridges.update("bad-id", name="x")
            assert updated.id == "bad-id"

    async def test_link_stations_endpoints(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test link stations endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations",
            payload={"data": [{"id": "station-1", "name": "Station 1"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations/station-1",
            payload={"data": {"id": "station-1", "name": "Station 1"}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations/station-1",
            payload={"data": {"id": "station-1", "name": "Station Updated"}},
        )

        async with client:
            stations = await client.link_stations.get_all()
            assert len(stations) == 1
            assert isinstance(stations[0], LinkStation)

            st = await client.link_stations.get("station-1")
            assert st.id == "station-1"

            up = await client.link_stations.update("station-1", name="Station Updated")
            assert up.name == "Station Updated"

    async def test_link_stations_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test link stations error branches."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations/bad-id", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations/bad-id", payload={}
        )
        # The empty PATCH body makes update() re-fetch the resource.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/link-stations/bad-id",
            payload={"data": {"id": "bad-id"}},
        )

        async with client:
            assert await client.link_stations.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.link_stations.get("bad-id")
            updated = await client.link_stations.update("bad-id", name="x")
            assert updated.id == "bad-id"

    async def test_alarm_hubs_endpoints(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test alarm hubs endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs",
            payload={"data": [{"id": "hub-1", "name": "Alarm Hub 1"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/hub-1",
            payload={"data": {"id": "hub-1", "name": "Alarm Hub 1"}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/hub-1",
            payload={"data": {"id": "hub-1", "name": "Alarm Hub Updated"}},
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/hub-1/outputs/1/trigger",
            status=200,
        )

        async with client:
            hubs = await client.alarm_hubs.get_all()
            assert len(hubs) == 1
            assert isinstance(hubs[0], AlarmHub)

            hb = await client.alarm_hubs.get("hub-1")
            assert hb.id == "hub-1"

            up = await client.alarm_hubs.update("hub-1", name="Alarm Hub Updated")
            assert up.name == "Alarm Hub Updated"

            await client.alarm_hubs.trigger_output("hub-1", 1)

    async def test_alarm_hubs_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test alarm hubs error branches."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/bad-id", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/bad-id", payload={}
        )
        # The empty PATCH body makes update() re-fetch the hub.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-hubs/bad-id", payload={}
        )

        async with client:
            assert await client.alarm_hubs.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.alarm_hubs.get("bad-id")
            with pytest.raises(UniFiNotFoundError):
                await client.alarm_hubs.update("bad-id", name="x")

    async def test_arm_profiles_and_alarm(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test arm profiles and alarm manager."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles",
            payload={"data": [{"id": "arm-1", "name": "Night Mode"}]},
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles",
            payload={"data": {"id": "arm-2", "name": "Away Mode"}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles/settings",
            payload={"data": {"activeProfileId": "arm-1", "isArmed": True}},
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles/arm-1",
            payload={"data": {"id": "arm-1", "name": "Night Mode Updated"}},
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles/enable",
            status=200,
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles/disable",
            status=200,
        )
        mock_aioresponse.delete(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles/arm-2",
            status=200,
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-manager/webhook/hook-1",
            status=200,
        )

        async with client:
            profiles = await client.arm_profiles.get_all()
            assert len(profiles) == 1
            assert isinstance(profiles[0], ArmProfile)

            created = await client.arm_profiles.create(name="Away Mode")
            assert created.id == "arm-2"

            settings = await client.arm_profiles.update_settings(
                activeProfileId="arm-1", isArmed=True
            )
            assert isinstance(settings, ArmProfileSettings)
            assert settings.is_armed is True

            updated = await client.arm_profiles.update("arm-1", name="Night Mode Updated")
            assert updated.name == "Night Mode Updated"

            await client.arm_profiles.enable()
            await client.arm_profiles.disable()
            await client.arm_profiles.delete("arm-2")
            await client.alarm_manager.send_webhook("hook-1", {"event": "motion"})

    async def test_arm_profiles_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test arm profiles error branches."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles", payload=None
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles/settings", payload={}
        )
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles/arm-x", payload={}
        )
        # The empty PATCH body makes update() search the listing for the profile.
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/arm-profiles", payload=None
        )

        async with client:
            assert await client.arm_profiles.get_all() == []
            with pytest.raises(UniFiResponseError):
                await client.arm_profiles.create(name="Bad")
            # An accepted settings write without a settings body still succeeded.
            assert await client.arm_profiles.update_settings() is True
            with pytest.raises(UniFiNotFoundError):
                await client.arm_profiles.update("arm-x")

    async def test_users_and_pos(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test user and POS endpoints."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/users",
            payload={"data": [{"id": "u-1", "name": "John Doe", "email": "john@example.com"}]},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/users/u-1",
            payload={"data": {"id": "u-1", "name": "John Doe", "email": "john@example.com"}},
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/ulp-users",
            payload={
                "data": [
                    {
                        "id": "ulp-1",
                        "firstName": "John",
                        "lastName": "Doe",
                        "fullName": "John Doe",
                        "email": "john@example.com",
                        "status": "ACTIVE",
                    }
                ]
            },
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/ulp-users/ulp-1",
            payload={
                "data": {
                    "id": "ulp-1",
                    "firstName": "John",
                    "lastName": "Doe",
                    "fullName": "John Doe",
                    "email": "john@example.com",
                    "status": "ACTIVE",
                }
            },
        )
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/pos/cameras/cam-1/transactions",
            payload={"created": True, "eventId": "tx-123"},
            status=200,
        )

        async with client:
            users = await client.users.get_users()
            assert len(users) == 1
            assert isinstance(users[0], ProtectUser)

            u = await client.users.get_user("u-1")
            assert u.id == "u-1"

            ulp_users = await client.ulp_users.get_all()
            assert len(ulp_users) == 1
            assert isinstance(ulp_users[0], ULPUser)

            ulp_u = await client.ulp_users.get("ulp-1")
            assert ulp_u.id == "ulp-1"

            req = POSTransactionRequest(
                type="sale",
                externalId="tx-123",
                amount=49.99,
                currency="USD",
            )
            res = await client.pos.ingest_transaction("cam-1", req)
            assert res.created is True

    async def test_users_error_branches(
        self, client: UniFiProtectClient, mock_aioresponse: aioresponses
    ) -> None:
        """Test users error branches."""
        mock_aioresponse.get("https://192.168.1.1/proxy/protect/integration/v1/users", payload=None)
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/users/bad-id", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/ulp-users", payload=None
        )
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/ulp-users/bad-id", payload=None
        )

        async with client:
            assert await client.users.get_users() == []
            with pytest.raises(UniFiNotFoundError):
                await client.users.get_user("bad-id")
            assert await client.ulp_users.get_all() == []
            with pytest.raises(UniFiNotFoundError):
                await client.ulp_users.get("bad-id")
