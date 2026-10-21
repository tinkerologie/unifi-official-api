"""Alarm Manager endpoint for UniFi Protect API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import UniFiProtectClient


class AlarmManagerEndpoint:
    """Endpoint for triggering UniFi Protect Alarm Manager webhooks."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """Initialize the Alarm Manager endpoint."""
        self._client = client

    async def send_webhook(
        self,
        trigger_id: str,
        site_id: str | None = None,
    ) -> bool:
        """Send a webhook to the Alarm Manager to trigger configured alarms.

        Args:
            trigger_id: User-defined trigger ID matching a configured alarm rule.
            site_id: Optional site ID (unused in local API).

        Returns:
            True if the webhook was accepted (HTTP 204).

        """
        return await self._client.application.trigger_alarm_webhook(trigger_id, site_id=site_id)
