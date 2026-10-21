"""Tests for new Protect API endpoints (viewers, application, camera additions)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from aioresponses import aioresponses

from unifi_official_api.protect import UniFiProtectClient
from unifi_official_api.protect.models import FileType


class TestViewersEndpoint:
    """Tests for viewers endpoint."""

    async def test_viewers_get_all(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing viewers."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/viewers",
            payload={
                "data": [
                    {
                        "id": "viewer-1",
                        "modelKey": "viewer",
                        "state": "CONNECTED",
                        "name": "Living Room Viewer",
                        "mac": "aa:bb:cc:dd:ee:ff",
                        "streamLimit": 4,
                    }
                ]
            },
        )

        viewers = await protect_client.viewers.get_all()
        assert len(viewers) == 1
        assert viewers[0].name == "Living Room Viewer"
        assert viewers[0].is_connected is True

    async def test_viewers_get_all_empty(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test listing viewers with empty response."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/viewers",
            payload={"data": []},
        )

        viewers = await protect_client.viewers.get_all()
        assert viewers == []

    async def test_viewers_get(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting a specific viewer."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/viewers/viewer-1",
            payload={
                "data": {
                    "id": "viewer-1",
                    "modelKey": "viewer",
                    "state": "CONNECTED",
                    "name": "Living Room Viewer",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "streamLimit": 4,
                }
            },
        )

        viewer = await protect_client.viewers.get("viewer-1")
        assert viewer.id == "viewer-1"
        assert viewer.display_name == "Living Room Viewer"

    async def test_viewers_get_not_found(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting a viewer that doesn't exist."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/viewers/viewer-999",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="not found"):
            await protect_client.viewers.get("viewer-999")

    async def test_viewers_update(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test updating a viewer."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/viewers/viewer-1",
            payload={
                "data": {
                    "id": "viewer-1",
                    "modelKey": "viewer",
                    "state": "CONNECTED",
                    "name": "Updated Viewer",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "streamLimit": 4,
                }
            },
        )

        viewer = await protect_client.viewers.update("viewer-1", name="Updated Viewer")
        assert viewer.name == "Updated Viewer"

    async def test_viewers_update_failed(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test updating a viewer failure."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/viewers/viewer-1",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="Failed"):
            await protect_client.viewers.update("viewer-1", name="Test")

    async def test_viewers_set_liveview(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test setting a viewer's liveview."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/viewers/viewer-1",
            payload={
                "data": {
                    "id": "viewer-1",
                    "modelKey": "viewer",
                    "state": "CONNECTED",
                    "name": "Viewer",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "liveview": "lv-1",
                    "streamLimit": 4,
                }
            },
        )

        viewer = await protect_client.viewers.set_liveview("viewer-1", "lv-1")
        assert viewer.liveview == "lv-1"


class TestApplicationEndpoint:
    """Tests for application endpoint."""

    async def test_application_get_info(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting application info."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/meta/info",
            payload={"data": {"applicationVersion": "6.2.83"}},
        )

        info = await protect_client.application.get_info()
        assert info.application_version == "6.2.83"

    async def test_application_get_info_failed(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting application info failure."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/meta/info",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="Failed"):
            await protect_client.application.get_info()

    async def test_application_get_files(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting files."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/files/animations",
            payload={
                "data": [
                    {
                        "name": "file-1",
                        "type": "animations",
                        "originalName": "logo.gif",
                        "path": "/files/logo.gif",
                    }
                ]
            },
        )

        files = await protect_client.application.get_files()
        assert len(files) == 1
        assert files[0].original_name == "logo.gif"

    async def test_application_get_files_empty(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting files with empty response."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/files/animations",
            payload={"data": []},
        )

        files = await protect_client.application.get_files()
        assert files == []

    async def test_application_upload_file(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test uploading a file."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/files/animations",
            payload={
                "data": {
                    "name": "file-new",
                    "type": "animations",
                    "originalName": "new.gif",
                    "path": "/files/new.gif",
                }
            },
        )

        file = await protect_client.application.upload_file(
            file_data=b"GIF89a...",
            filename="new.gif",
            content_type="image/gif",
            file_type=FileType.ANIMATIONS,
        )
        assert file.original_name == "new.gif"

    async def test_application_upload_file_failed(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test uploading a file failure."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/files/animations",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="Failed"):
            await protect_client.application.upload_file(file_data=b"...", filename="test.gif")

    async def test_application_trigger_alarm_webhook(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test triggering alarm webhook."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/alarm-manager/webhook/trigger-1",
            status=204,
        )

        result = await protect_client.application.trigger_alarm_webhook("trigger-1")
        assert result is True

    async def test_application_trigger_alarm_webhook_no_id(
        self,
        protect_client: UniFiProtectClient,
    ) -> None:
        """Test triggering alarm webhook without trigger ID."""
        with pytest.raises(ValueError, match="Trigger ID is required"):
            await protect_client.application.trigger_alarm_webhook("")


class TestCameraNewMethods:
    """Tests for new camera endpoint methods."""

    async def test_camera_ptz_patrol_start(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test starting PTZ patrol."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/ptz/patrol/start/0",
            status=204,
        )

        result = await protect_client.cameras.ptz_patrol_start("cam-1", slot=0)
        assert result is True

    async def test_camera_ptz_patrol_start_invalid_slot(
        self,
        protect_client: UniFiProtectClient,
    ) -> None:
        """Test starting PTZ patrol with invalid slot."""
        with pytest.raises(ValueError, match="Slot must be between 0 and 4"):
            await protect_client.cameras.ptz_patrol_start("cam-1", slot=5)

    async def test_camera_ptz_patrol_stop(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test stopping PTZ patrol."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/ptz/patrol/stop",
            status=204,
        )

        result = await protect_client.cameras.ptz_patrol_stop("cam-1")
        assert result is True

    async def test_camera_create_rtsps_stream(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test creating RTSPS stream."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/rtsps-stream",
            payload={"data": {"high": "rtsps://192.168.1.1:7441/stream"}},
        )

        stream = await protect_client.cameras.create_rtsps_stream("cam-1")
        assert stream.high == "rtsps://192.168.1.1:7441/stream"
        assert stream.get_url("high") == "rtsps://192.168.1.1:7441/stream"

    async def test_camera_create_rtsps_stream_with_qualities(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test creating RTSPS stream with multiple qualities."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/rtsps-stream",
            payload={
                "data": {
                    "high": "rtsps://192.168.1.1:7441/stream-high",
                    "medium": "rtsps://192.168.1.1:7441/stream-medium",
                }
            },
        )

        stream = await protect_client.cameras.create_rtsps_stream(
            "cam-1", qualities=["high", "medium"]
        )
        assert stream.high == "rtsps://192.168.1.1:7441/stream-high"
        assert stream.medium == "rtsps://192.168.1.1:7441/stream-medium"

    async def test_camera_create_rtsps_stream_failed(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test creating RTSPS stream failure."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/rtsps-stream",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="Failed"):
            await protect_client.cameras.create_rtsps_stream("cam-1")

    async def test_camera_get_rtsps_stream(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting RTSPS stream."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/rtsps-stream",
            payload={"data": {"url": "rtsps://192.168.1.1:7441/stream", "channel": 0}},
        )

        stream = await protect_client.cameras.get_rtsps_stream("cam-1")
        assert stream.url == "rtsps://192.168.1.1:7441/stream"

    async def test_camera_get_rtsps_stream_not_found(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test getting RTSPS stream that doesn't exist."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/rtsps-stream",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="not found"):
            await protect_client.cameras.get_rtsps_stream("cam-1")

    async def test_camera_delete_rtsps_stream(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test deleting RTSPS stream."""
        # Note: aioresponses doesn't match query params by default, so we use a pattern
        mock_aioresponse.delete(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/rtsps-stream?qualities=high",
            status=204,
        )

        result = await protect_client.cameras.delete_rtsps_stream("cam-1")
        assert result is True

    async def test_camera_delete_rtsps_stream_with_qualities(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test deleting RTSPS stream with multiple qualities."""
        mock_aioresponse.delete(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/rtsps-stream?qualities=high&qualities=medium",
            status=204,
        )

        result = await protect_client.cameras.delete_rtsps_stream(
            "cam-1", qualities=["high", "medium"]
        )
        assert result is True

    async def test_camera_create_talkback_session(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test creating talkback session."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/talkback-session",
            payload={
                "data": {
                    "url": "rtp://192.168.1.1:7004",
                    "codec": "opus",
                    "samplingRate": 24000,
                    "bitsPerSample": 16,
                }
            },
        )

        session = await protect_client.cameras.create_talkback_session("cam-1")
        assert session.url == "rtp://192.168.1.1:7004"
        assert session.codec == "opus"

    async def test_camera_create_talkback_session_failed(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test creating talkback session failure."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/talkback-session",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="Failed"):
            await protect_client.cameras.create_talkback_session("cam-1")

    async def test_camera_disable_mic_permanently(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test disabling camera microphone permanently."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/disable-mic-permanently",
            payload={
                "data": {
                    "id": "cam-1",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "isMicEnabled": False,
                }
            },
        )

        camera = await protect_client.cameras.disable_mic_permanently("cam-1")
        assert camera.id == "cam-1"

    async def test_camera_disable_mic_permanently_failed(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test disabling camera microphone failure."""
        mock_aioresponse.post(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1/disable-mic-permanently",
            payload={"data": []},
        )

        with pytest.raises(ValueError, match="Failed"):
            await protect_client.cameras.disable_mic_permanently("cam-1")

    async def test_camera_set_hdr_mode(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test setting HDR mode."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1",
            payload={"data": {"id": "cam-1", "mac": "aa:bb:cc:dd:ee:ff", "hdrType": "auto"}},
        )

        camera = await protect_client.cameras.set_hdr_mode("cam-1", "auto")
        assert camera.id == "cam-1"

    async def test_camera_set_hdr_mode_invalid(
        self,
        protect_client: UniFiProtectClient,
    ) -> None:
        """Test setting invalid HDR mode."""
        with pytest.raises(ValueError, match="HDR mode must be"):
            await protect_client.cameras.set_hdr_mode("cam-1", "invalid")

    async def test_camera_set_video_mode(
        self,
        protect_client: UniFiProtectClient,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test setting video mode."""
        mock_aioresponse.patch(
            "https://192.168.1.1/proxy/protect/integration/v1/cameras/cam-1",
            payload={"data": {"id": "cam-1", "mac": "aa:bb:cc:dd:ee:ff", "videoMode": "highFps"}},
        )

        camera = await protect_client.cameras.set_video_mode("cam-1", "highFps")
        assert camera.id == "cam-1"


class TestViewerModel:
    """Tests for Viewer model."""

    def test_viewer_display_name_with_name(self) -> None:
        """Test display_name with name set."""
        from unifi_official_api.protect.models import Viewer

        viewer = Viewer.model_validate(
            {
                "id": "v-1",
                "modelKey": "viewer",
                "state": "CONNECTED",
                "name": "Living Room",
                "mac": "aa:bb:cc:dd:ee:ff",
                "streamLimit": 4,
            }
        )
        assert viewer.display_name == "Living Room"

    def test_viewer_display_name_without_name(self) -> None:
        """Test display_name without name set."""
        from unifi_official_api.protect.models import Viewer

        viewer = Viewer.model_validate(
            {
                "id": "v-1",
                "modelKey": "viewer",
                "state": "CONNECTED",
                "mac": "aa:bb:cc:dd:ee:ff",
                "streamLimit": 4,
            }
        )
        assert viewer.display_name == "aa:bb:cc:dd:ee:ff"


class TestACLRuleModel:
    """Tests for ACL Rule model."""

    def test_acl_rule_is_user_defined_true(self) -> None:
        """Test is_user_defined when user-defined."""
        from unifi_official_api.network.models import ACLRule

        rule = ACLRule.model_validate(
            {
                "id": "acl-1",
                "type": "IPV4",
                "name": "Test",
                "action": "BLOCK",
                "enabled": True,
                "index": 0,
                "metadata": {"origin": "USER_DEFINED"},
            }
        )
        assert rule.is_user_defined is True

    def test_acl_rule_is_user_defined_false(self) -> None:
        """Test is_user_defined when system-defined."""
        from unifi_official_api.network.models import ACLRule

        rule = ACLRule.model_validate(
            {
                "id": "acl-1",
                "type": "IPV4",
                "name": "Test",
                "action": "BLOCK",
                "enabled": True,
                "index": 0,
                "metadata": {"origin": "SYSTEM_DEFINED"},
            }
        )
        assert rule.is_user_defined is False

    def test_acl_rule_is_user_defined_no_metadata(self) -> None:
        """Test is_user_defined without metadata."""
        from unifi_official_api.network.models import ACLRule

        rule = ACLRule.model_validate(
            {
                "id": "acl-1",
                "type": "IPV4",
                "name": "Test",
                "action": "BLOCK",
                "enabled": True,
                "index": 0,
            }
        )
        assert rule.is_user_defined is True


class TestTrafficMatchingListModel:
    """Tests for Traffic Matching List model."""

    def test_traffic_list_is_user_defined_true(self) -> None:
        """Test is_user_defined when user-defined."""
        from unifi_official_api.network.models import TrafficMatchingList

        traffic_list = TrafficMatchingList.model_validate(
            {
                "id": "list-1",
                "type": "IP_ADDRESS",
                "name": "Test",
                "entries": [],
                "metadata": {"origin": "USER_DEFINED"},
            }
        )
        assert traffic_list.is_user_defined is True

    def test_traffic_list_is_user_defined_false(self) -> None:
        """Test is_user_defined when system-defined."""
        from unifi_official_api.network.models import TrafficMatchingList

        traffic_list = TrafficMatchingList.model_validate(
            {
                "id": "list-1",
                "type": "IP_ADDRESS",
                "name": "Test",
                "entries": [],
                "metadata": {"origin": "SYSTEM_DEFINED"},
            }
        )
        assert traffic_list.is_user_defined is False


class TestVoucherModel:
    """Tests for Voucher model."""

    def test_voucher_is_active_not_expired(self) -> None:
        """Test is_active when not expired."""
        from unifi_official_api.network.models import Voucher

        voucher = Voucher.model_validate(
            {
                "id": "v-1",
                "code": "1234567890",
                "expired": False,
                "authorizedGuestCount": 0,
            }
        )
        assert voucher.is_active is True

    def test_voucher_is_active_expired(self) -> None:
        """Test is_active when expired."""
        from unifi_official_api.network.models import Voucher

        voucher = Voucher.model_validate(
            {
                "id": "v-1",
                "code": "1234567890",
                "expired": True,
                "authorizedGuestCount": 0,
            }
        )
        assert voucher.is_active is False

    def test_voucher_is_active_uses_exhausted(self) -> None:
        """Test is_active when uses are exhausted."""
        from unifi_official_api.network.models import Voucher

        voucher = Voucher.model_validate(
            {
                "id": "v-1",
                "code": "1234567890",
                "expired": False,
                "authorizedGuestLimit": 1,
                "authorizedGuestCount": 1,
            }
        )
        assert voucher.is_active is False


class TestWebSocketSubscription:
    """Tests for WebSocket subscription."""

    async def test_websocket_subscribe_invalid_type(
        self,
        protect_client: UniFiProtectClient,
    ) -> None:
        """Test websocket subscribe with invalid type."""
        with pytest.raises(ValueError, match="subscription_type must be"):
            await protect_client.websocket.subscribe_with_callback(
                "host-123", "site-1", "invalid", lambda _: None
            )

    def test_websocket_stop(self) -> None:
        """Test websocket stop method."""
        from unifi_official_api.protect.websocket import ProtectWebSocket

        mock_client = MagicMock()
        ws = ProtectWebSocket(mock_client)
        ws._running = True
        ws.stop()
        assert ws._running is False
