"""WebSocket subscription support for UniFi Protect API."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import aiohttp

from unifi_official_api.base import parse_retry_after
from unifi_official_api.const import RATE_LIMIT_MAX_RETRY_AFTER

if TYPE_CHECKING:
    from .client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)


class ProtectWebSocket:
    """
    WebSocket subscription manager for UniFi Protect.

    Provides real-time event streaming for device updates and Protect events.

    To use WebSocket subscriptions, you need a `host_id` and `site_id`:
    - `host_id`: The NVR ID, obtainable via `await client.get_host_id()`
    - `site_id`: For local connections, use "default". For remote, get from cloud API.

    `host_id`/`site_id` are accepted for API compatibility and potential future
    multi-site routing, but the subscribe path is currently built the same way
    as every other Protect endpoint - via `client.build_api_path()` - so that it
    honours LOCAL (`/proxy/protect/integration/v1/subscribe/...`) vs REMOTE
    (`/v1/connector/consoles/{console_id}/protect/integration/v1/subscribe/...`)
    routing consistently with the REST endpoints on this client.
    """

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize WebSocket manager.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._running = False

    def _subscribe_path(self, subscription_type: str) -> str:
        """
        Build the subscribe path for the given subscription type.

        Uses the same `build_api_path()` convention as every other Protect
        endpoint on this client, so LOCAL and REMOTE connections are routed
        correctly (see class docstring).
        """
        return self._client.build_api_path(f"/subscribe/{subscription_type}")

    async def _connect(self, path: str) -> aiohttp.ClientWebSocketResponse:
        """
        Establish WebSocket connection.

        Args:
            path: WebSocket endpoint path.

        Returns:
            WebSocket connection.

        """
        session = await self._client._ensure_session()
        url = str(self._client._build_url(path)).replace("https://", "wss://")
        headers = self._client._get_headers()

        await self._client._throttle()
        try:
            return await session.ws_connect(url, headers=headers, heartbeat=30)
        except aiohttp.WSServerHandshakeError as err:
            if err.status == HTTPStatus.TOO_MANY_REQUESTS:
                self._client._defer_after_rate_limit(
                    min(
                        parse_retry_after(err.headers or {}),
                        RATE_LIMIT_MAX_RETRY_AFTER,
                    )
                )
            raise

    @asynccontextmanager
    async def subscribe_devices(
        self,
        host_id: str,
        site_id: str,
    ) -> AsyncIterator[AsyncIterator[dict[str, Any]]]:
        """
        Subscribe to device update messages.

        Args:
            host_id: The host ID.
            site_id: The site ID.

        Yields:
            Async iterator of device update messages.

        """
        del host_id, site_id
        path = self._subscribe_path("devices")
        ws = await self._connect(path)
        self._running = True

        async def message_iterator() -> AsyncIterator[dict[str, Any]]:
            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            yield data
                        except json.JSONDecodeError:
                            continue
                    elif msg.type in (
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSED,
                    ):
                        break
            finally:
                self._running = False

        try:
            yield message_iterator()
        finally:
            self._running = False
            await ws.close()

    @asynccontextmanager
    async def subscribe_events(
        self,
        host_id: str,
        site_id: str,
    ) -> AsyncIterator[AsyncIterator[dict[str, Any]]]:
        """
        Subscribe to Protect event messages.

        Args:
            host_id: The host ID.
            site_id: The site ID.

        Yields:
            Async iterator of event messages.

        """
        del host_id, site_id
        path = self._subscribe_path("events")
        ws = await self._connect(path)
        self._running = True

        async def message_iterator() -> AsyncIterator[dict[str, Any]]:
            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            yield data
                        except json.JSONDecodeError:
                            continue
                    elif msg.type in (
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSED,
                    ):
                        break
            finally:
                self._running = False

        try:
            yield message_iterator()
        finally:
            self._running = False
            await ws.close()

    async def subscribe_with_callback(
        self,
        host_id: str,
        site_id: str,
        subscription_type: str,
        callback: Callable[[dict[str, Any]], None],
        *,
        reconnect: bool = True,
        reconnect_delay: float = 5.0,
        on_connection_state_change: Callable[[bool], None] | None = None,
    ) -> None:
        """
        Subscribe with a callback function.

        Args:
            host_id: The host ID.
            site_id: The site ID.
            subscription_type: Type of subscription ("devices" or "events").
            callback: Function to call for each message.
            reconnect: Whether to automatically reconnect on disconnect.
            reconnect_delay: Delay in seconds before reconnecting.
            on_connection_state_change: Optional callback invoked with True/False.

        """
        if subscription_type not in ("devices", "events"):
            raise ValueError("subscription_type must be 'devices' or 'events'")

        path = self._subscribe_path(subscription_type)
        self._running = True

        def _report_state(*, connected: bool) -> None:
            if on_connection_state_change is None:
                return
            try:
                on_connection_state_change(connected)
            except Exception:
                _LOGGER.exception(
                    "ProtectWebSocket: on_connection_state_change callback raised "
                    "for %s subscription",
                    subscription_type,
                )

        while self._running:
            ws: aiohttp.ClientWebSocketResponse | None = None
            retry_delay = reconnect_delay
            try:
                ws = await self._connect(path)
                _LOGGER.debug(
                    "ProtectWebSocket: connected for %s subscription (host_id=%s, site_id=%s)",
                    subscription_type,
                    host_id,
                    site_id,
                )
                _report_state(connected=True)

                async for msg in ws:
                    if not self._running:
                        break
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            callback(data)
                        except json.JSONDecodeError:
                            _LOGGER.debug("ProtectWebSocket: dropped non-JSON message")
                            continue
                    elif msg.type in (
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSED,
                    ):
                        break
            except asyncio.CancelledError:
                raise
            except aiohttp.WSServerHandshakeError as err:
                if err.status == HTTPStatus.TOO_MANY_REQUESTS:
                    cooldown = min(
                        parse_retry_after(err.headers or {}),
                        RATE_LIMIT_MAX_RETRY_AFTER,
                    )
                    retry_delay = max(reconnect_delay, cooldown)
                    _LOGGER.debug(
                        "ProtectWebSocket: rate-limited %s handshake; requests deferred for %ss",
                        subscription_type,
                        cooldown,
                    )
                else:
                    _LOGGER.warning(
                        "ProtectWebSocket: connection error subscribing to %s at %s: %s",
                        subscription_type,
                        path,
                        err,
                    )
            except aiohttp.ClientError as err:
                _LOGGER.warning(
                    "ProtectWebSocket: connection error subscribing to %s at %s: %s",
                    subscription_type,
                    path,
                    err,
                )
            finally:
                _report_state(connected=False)
                if ws is not None and not ws.closed:
                    await ws.close()

            if self._running and reconnect:
                await asyncio.sleep(retry_delay)
            else:
                break

    def stop(self) -> None:
        """Stop the WebSocket subscription."""
        self._running = False
