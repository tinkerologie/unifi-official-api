"""Webhook endpoint registration for the UniFi Access developer API."""

from typing import TYPE_CHECKING, Any

from ...exceptions import UniFiValidationError
from ..errors import ensure_success_envelope
from ..models import AccessWebhookEndpoint, parse_record, parse_records
from .common import safe_id

if TYPE_CHECKING:
    from ..client import UniFiAccessClient

_ENDPOINTS_PATH = "webhooks/endpoints"


class WebhooksEndpoint:
    """
    Manage webhook endpoints (``view:webhook`` / ``edit:webhook``).

    Verified against the Ubiquiti UniFi Access API Reference V2.2.10
    (Sections 11.3-11.6, minimum Access application version ``2.2.10+``).
    Create, update and delete responses include the signing secret, so their
    bodies are never logged.
    """

    def __init__(self, client: UniFiAccessClient) -> None:
        """Initialize the endpoint group."""
        self._client = client

    async def get_all(self) -> list[AccessWebhookEndpoint]:
        """Return every registered webhook endpoint."""
        response = await self._client._get(_ENDPOINTS_PATH)
        return parse_records(response, AccessWebhookEndpoint, _ENDPOINTS_PATH)

    async def create(
        self,
        *,
        name: str,
        endpoint: str,
        events: list[str],
    ) -> AccessWebhookEndpoint:
        """Register an HTTPS endpoint for the given events; returns its secret."""
        response = await self._client._post(
            _ENDPOINTS_PATH,
            json_data=self._body(name=name, endpoint=endpoint, events=events),
            log_body=False,
        )
        return parse_record(response, AccessWebhookEndpoint, _ENDPOINTS_PATH)

    async def update(
        self,
        endpoint_id: str,
        *,
        name: str,
        endpoint: str,
        events: list[str],
    ) -> AccessWebhookEndpoint:
        """Replace an endpoint's name, URL and events."""
        path = f"{_ENDPOINTS_PATH}/{safe_id(endpoint_id)}"
        response = await self._client._put(
            path,
            json_data=self._body(name=name, endpoint=endpoint, events=events),
            log_body=False,
        )
        return parse_record(response, AccessWebhookEndpoint, path)

    async def delete(self, endpoint_id: str) -> None:
        """Delete a webhook endpoint."""
        path = f"{_ENDPOINTS_PATH}/{safe_id(endpoint_id)}"
        response = await self._client._delete(path, log_body=False)
        ensure_success_envelope(response, path)

    @staticmethod
    def _body(*, name: str, endpoint: str, events: list[str]) -> dict[str, Any]:
        """Return the request body shared by create and update."""
        if not name or not endpoint or not events:
            msg = "Webhook name, endpoint and events are required"
            raise UniFiValidationError(msg)
        return {"name": name, "endpoint": endpoint, "events": list(events)}
