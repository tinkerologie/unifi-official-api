"""Cameras endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, get_args

from pydantic import ValidationError

from ...validation import created_record, require_record, written_record
from ..models import Camera, RecordingMode
from ..models.files import RTSPSStream, TalkbackSession

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)

SnapshotChannel = Literal["main", "package"]
_SNAPSHOT_CHANNELS: frozenset[str] = frozenset(get_args(SnapshotChannel))


class CamerasEndpoint:
    """Endpoint for managing UniFi Protect cameras."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the cameras endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError. Callers need to tell a complete listing from a short
        # one: a device absent because its payload would not parse is still
        # adopted, and must not be treated as removed.
        self.last_result_complete: bool = True

    async def get_all(
        self,
        site_id: str | None = None,
        *,
        expected_unsupported: bool = False,
    ) -> list[Camera]:
        """
        List all cameras.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal.

        Returns:
            List of cameras.

        """
        path = self._client.build_api_path("/cameras", site_id)
        self.last_result_complete = True
        response = await self._client._get(path, expected_unsupported=expected_unsupported)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(data, list):
            return []

        cameras: list[Camera] = []
        for item in data:
            try:
                cameras.append(Camera.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping camera that failed to parse (id=%s): %s",
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return cameras

    async def get(self, camera_id: str, site_id: str | None = None) -> Camera:
        """
        Get a specific camera.

        Args:
            camera_id: The camera ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The camera.

        Raises:
            UniFiNotFoundError: If the response holds no camera with an ``id``.
            UniFiResponseError: If the camera in the response fails validation.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}", site_id)
        return require_record(await self._client._get(path), Camera, f"Camera {camera_id}")

    async def update(
        self,
        camera_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> Camera:
        """
        Update camera settings.

        Args:
            camera_id: The camera ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            The updated camera.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no camera.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), Camera)
        if written is not None:
            return written
        return await self.get(camera_id, site_id)

    async def set_recording_mode(
        self,
        camera_id: str,
        mode: RecordingMode,
        site_id: str | None = None,
    ) -> Camera:
        """
        Set camera recording mode.

        Args:
            camera_id: The camera ID.
            mode: The recording mode.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated camera.

        """
        return await self.update(camera_id, site_id, recordingMode=mode.value)

    async def get_snapshot(
        self,
        camera_id: str,
        site_id: str | None = None,
        *,
        high_quality: bool = False,
        channel: SnapshotChannel | None = None,
    ) -> bytes:
        """
        Get a snapshot from the camera.

        Args:
            camera_id: The camera ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            high_quality: Request a 1080p or higher snapshot (only supported on
                some cameras; ignored by the API when unsupported).
            channel: Camera channel to capture, ``"main"`` or ``"package"``.
                Use ``"package"`` for cameras with a package camera
                (``hasPackageCamera``). Not sent when None.

        Returns:
            The raw snapshot image bytes.

        Raises:
            ValueError: If the channel is not ``"main"`` or ``"package"``.
            UniFiAuthenticationError: If the console answers 401 or 403.
            UniFiNotFoundError: If the console answers 404.
            UniFiRateLimitError: If the console still answers 429 after one retry.
            UniFiResponseError: If the console answers any other 4xx or 5xx status,
                e.g. 400 when the camera cannot take the requested snapshot.
            UniFiConnectionError: If the console cannot be reached.

        """
        if channel is not None and channel not in _SNAPSHOT_CHANNELS:
            raise ValueError("Snapshot channel must be 'main' or 'package'")
        params: dict[str, Any] = {}
        if high_quality:
            params["highQuality"] = "true"
        if channel is not None:
            params["channel"] = channel

        path = self._client.build_api_path(f"/cameras/{camera_id}/snapshot", site_id)
        return await self._client._get_binary(path, params=params or None)

    async def set_microphone_volume(
        self,
        camera_id: str,
        volume: int,
        site_id: str | None = None,
    ) -> Camera:
        """
        Set camera microphone volume.

        Args:
            camera_id: The camera ID.
            volume: Volume level (0-100).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated camera.

        """
        if not 1 <= volume <= 100:
            raise ValueError("Volume must be between 1 and 100")
        return await self.update(camera_id, site_id, micVolume=volume)

    async def set_speaker_volume(
        self,
        camera_id: str,
        volume: int,
        site_id: str | None = None,
    ) -> Camera:
        """
        Set camera speaker volume.

        Args:
            camera_id: The camera ID.
            volume: Volume level (0-100).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated camera.

        """
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be between 0 and 100")
        return await self.update(camera_id, site_id, speakerVolume=volume)

    async def ptz_goto_preset(
        self,
        camera_id: str,
        preset_id: str,
        site_id: str | None = None,
    ) -> bool:
        """
        Move PTZ camera to a preset position.

        Args:
            camera_id: The camera ID.
            preset_id: The preset position ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}/ptz/goto/{preset_id}", site_id)
        await self._client._post(path)
        return True

    async def ptz_patrol_start(
        self,
        camera_id: str,
        slot: int,
        site_id: str | None = None,
    ) -> bool:
        """
        Start PTZ patrol.

        Args:
            camera_id: The camera ID.
            slot: Patrol slot number (0-4).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            True if successful.

        """
        if not 0 <= slot <= 4:
            raise ValueError("Slot must be between 0 and 4")
        path = self._client.build_api_path(f"/cameras/{camera_id}/ptz/patrol/start/{slot}", site_id)
        await self._client._post(path)
        return True

    async def ptz_patrol_stop(
        self,
        camera_id: str,
        site_id: str | None = None,
    ) -> bool:
        """
        Stop active PTZ patrol.

        Args:
            camera_id: The camera ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}/ptz/patrol/stop", site_id)
        await self._client._post(path)
        return True

    async def create_rtsps_stream(
        self,
        camera_id: str,
        qualities: list[str] | None = None,
        site_id: str | None = None,
    ) -> RTSPSStream:
        """
        Create RTSPS stream for camera.

        Args:
            camera_id: The camera ID.
            qualities: List of stream qualities to enable (e.g., ["high"], ["medium", "low"]).
                      Valid values are typically "high", "medium", "low".
                      Defaults to ["high"] if not specified.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            RTSPS stream configuration.

        Raises:
            UniFiNotFoundError: If the response holds no stream configuration and
                the follow-up ``get_rtsps_stream()`` finds none either.
            UniFiResponseError: If the follow-up response fails validation.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}/rtsps-stream", site_id)
        body = {"qualities": qualities or ["high"]}
        written = written_record(
            await self._client._post(path, json_data=body), RTSPSStream, id_key=None
        )
        if written is not None:
            return written
        return await self.get_rtsps_stream(camera_id, site_id)

    async def get_rtsps_stream(
        self,
        camera_id: str,
        site_id: str | None = None,
    ) -> RTSPSStream:
        """
        Get RTSPS stream configuration.

        Args:
            camera_id: The camera ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            RTSPS stream configuration.

        Raises:
            UniFiNotFoundError: If the response holds no stream configuration.
            UniFiResponseError: If the stream configuration fails validation.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}/rtsps-stream", site_id)
        return require_record(
            await self._client._get(path),
            RTSPSStream,
            f"RTSPS stream for camera {camera_id}",
            id_key=None,
        )

    async def delete_rtsps_stream(
        self,
        camera_id: str,
        qualities: list[str] | None = None,
        site_id: str | None = None,
    ) -> bool:
        """
        Delete RTSPS stream.

        Args:
            camera_id: The camera ID.
            qualities: List of stream qualities to delete (e.g., ["high"], ["medium", "low"]).
                      Defaults to ["high"] if not specified.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}/rtsps-stream", site_id)
        params = {"qualities": qualities or ["high"]}
        await self._client._delete(path, params=params)
        return True

    async def create_talkback_session(
        self,
        camera_id: str,
        site_id: str | None = None,
    ) -> TalkbackSession:
        """
        Create a talkback (two-way audio) session.

        Args:
            camera_id: The camera ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            Talkback session configuration with URL and audio settings.

        Raises:
            UniFiResponseError: If the console accepted the request but the response
                holds no valid talkback session.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}/talkback-session", site_id)
        response = await self._client._post(path)
        return created_record(
            response, TalkbackSession, f"Talkback session for camera {camera_id}", id_key=None
        )

    async def disable_mic_permanently(
        self,
        camera_id: str,
        site_id: str | None = None,
    ) -> Camera:
        """
        Permanently disable camera microphone.

        This action cannot be undone.

        Args:
            camera_id: The camera ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated camera with microphone disabled.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no camera.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/cameras/{camera_id}/disable-mic-permanently", site_id)
        written = written_record(await self._client._post(path), Camera)
        if written is not None:
            return written
        return await self.get(camera_id, site_id)

    async def set_hdr_mode(
        self,
        camera_id: str,
        mode: str,
        site_id: str | None = None,
    ) -> Camera:
        """
        Set camera HDR mode.

        Args:
            camera_id: The camera ID.
            mode: HDR mode (auto, on, off).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated camera.

        """
        if mode not in ("auto", "on", "off"):
            raise ValueError("HDR mode must be 'auto', 'on', or 'off'")
        return await self.update(camera_id, site_id, hdrType=mode)

    async def set_video_mode(
        self,
        camera_id: str,
        mode: str,
        site_id: str | None = None,
    ) -> Camera:
        """
        Set camera video mode.

        Args:
            camera_id: The camera ID.
            mode: Video mode (default, highFps, sport, slowShutter, etc).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated camera.

        """
        return await self.update(camera_id, site_id, videoMode=mode)
