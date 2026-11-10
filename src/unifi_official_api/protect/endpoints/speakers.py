"""Speaker endpoint for UniFi Protect API."""

from __future__ import annotations

from ..models import Speaker
from ._base import ProtectDeviceEndpoint


class SpeakersEndpoint(ProtectDeviceEndpoint[Speaker]):
    """Endpoint for managing UniFi Protect speakers."""

    _resource = "speakers"
    _model = Speaker

    async def test_sound(self, speaker_id: str, site_id: str | None = None) -> bool:
        """
        Play the speaker test sound.

        Args:
            speaker_id: The speaker ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            True if the request was accepted.

        """
        path = self._client.build_api_path(f"/speakers/{speaker_id}/test-sound", site_id)
        await self._client._post(path)
        return True

    async def stop_siren(self, speaker_id: str, site_id: str | None = None) -> bool:
        """
        Stop the siren that is playing on the speaker.

        Args:
            speaker_id: The speaker ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            True if the request was accepted.

        Raises:
            UniFiResponseError: If the speaker is offline or runs firmware too
                old for siren (HTTP 400).

        """
        path = self._client.build_api_path(f"/speakers/{speaker_id}/stop-siren", site_id)
        await self._client._post(path)
        return True
