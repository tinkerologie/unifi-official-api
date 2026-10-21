"""Notification WebSocket for the UniFi Access developer API."""

from __future__ import annotations

import asyncio
import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from collections.abc import Callable

    from .client import UniFiAccessClient

_LOGGER = logging.getLogger(__name__)

_NOTIFICATIONS_PATH = "devices/notifications"
_HEARTBEAT_SECONDS = 30
_MAX_RECONNECT_DELAY = 300.0
_CLOSE_TIMEOUT_SECONDS = 5.0
# A handshake answer that repeats on retry. 401 means the token was rejected;
# 403 and 404 mean this token or console does not offer notifications. Every
# other failure (5xx, 429, timeouts, transport errors) is treated as transient.
PERMANENT_HANDSHAKE_STATUSES = frozenset(
    {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND}
)


def _parse_frame(text: str) -> dict[str, Any] | None:
    """Return a JSON object frame, or None for anything else."""
    try:
        frame = json.loads(text)
    except json.JSONDecodeError:
        _LOGGER.debug("Dropped a non-JSON Access notification frame")
        return None
    if not isinstance(frame, dict):
        _LOGGER.debug("Dropped a non-object Access notification frame")
        return None
    return frame


class AccessNotificationSocket:
    """
    Hold the Access notification socket open, reconnecting after transient failures.

    Documented in the Ubiquiti UniFi Access API Reference V2.2.10 (Section 11.1,
    minimum Access application version ``1.20.11+``).

    The handshake is the capability probe: the console answers it with 403 or
    404 when notifications are not offered, and with 401 when the token is
    rejected. Those answers are permanent. ``on_stop`` receives the status once
    and ``run`` returns, so the owner decides what the answer means. ``run``
    never awaits its owner.
    """

    def __init__(self, client: UniFiAccessClient) -> None:
        """Bind the socket to an Access client's session, headers and TLS policy."""
        self._client = client

    async def _connect(self) -> aiohttp.ClientWebSocketResponse:
        """Open the socket with the bearer header and the client's TLS setting."""
        session = await self._client._ensure_session()
        url = str(self._client._build_url(_NOTIFICATIONS_PATH)).replace("https://", "wss://", 1)
        headers = self._client._get_headers()
        await self._client._throttle()
        # A shared caller session verifies TLS by default. The client passes
        # its own verify_ssl setting per request so a self-signed console still
        # connects when verification is turned off.
        return await session.ws_connect(
            url,
            headers=headers,
            heartbeat=_HEARTBEAT_SECONDS,
            ssl=self._client._ssl_for_request() is not False,
        )

    async def run(
        self,
        on_frame: Callable[[dict[str, Any]], None],
        *,
        on_stop: Callable[[int], None],
        reconnect_delay: float = 5.0,
    ) -> None:
        """
        Deliver JSON object frames to ``on_frame`` until a permanent answer or cancel.

        A permanent handshake answer calls ``on_stop`` with its HTTP status and
        returns. Transient failures wait with exponential backoff (capped) and
        reconnect. The backoff restarts after each successful handshake.
        """
        delay = reconnect_delay
        while True:
            ws: aiohttp.ClientWebSocketResponse | None = None
            try:
                ws = await self._connect()
                _LOGGER.debug("Connected to the UniFi Access notification socket")
                delay = reconnect_delay
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        frame = _parse_frame(msg.data)
                        if frame is not None:
                            self._deliver(on_frame, frame)
                    elif msg.type in (
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSED,
                    ):
                        break
            except asyncio.CancelledError:
                raise
            except aiohttp.WSServerHandshakeError as err:
                if err.status in PERMANENT_HANDSHAKE_STATUSES:
                    _LOGGER.info("UniFi Access notifications stopped (HTTP %s)", err.status)
                    on_stop(err.status)
                    return
                _LOGGER.warning(
                    "UniFi Access notification handshake failed (HTTP %s); retrying",
                    err.status,
                )
            except (aiohttp.ClientError, TimeoutError) as err:
                # TimeoutError covers a connect timeout, which aiohttp does not
                # wrap in ClientError.
                _LOGGER.warning(
                    "UniFi Access notification socket failed (%s); reconnecting",
                    type(err).__name__,
                )
            finally:
                if ws is not None and not ws.closed:
                    try:
                        # aiohttp's close timer restarts on incoming frames. An
                        # Access console that keeps sending notifications can
                        # otherwise hold cleanup before reconnect indefinitely.
                        # Cancellation closes aiohttp's underlying response.
                        async with asyncio.timeout(_CLOSE_TIMEOUT_SECONDS):
                            await ws.close()
                    except TimeoutError:
                        _LOGGER.debug("Timed out closing the Access notification socket")
            await asyncio.sleep(delay)
            delay = min(delay * 2, _MAX_RECONNECT_DELAY)

    @staticmethod
    def _deliver(on_frame: Callable[[dict[str, Any]], None], frame: dict[str, Any]) -> None:
        """Pass one frame on. A failing handler is logged by type only."""
        try:
            on_frame(frame)
        except Exception as err:
            _LOGGER.warning("UniFi Access notification handler failed (%s)", type(err).__name__)
