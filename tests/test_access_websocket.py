# Copyright 2026 UniFi Insights contributors
"""Verify the Access notification socket's stop, retry and frame behaviour."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from attrs import evolve
from yarl import URL

from unifi_official_api.access.websocket import (
    AccessNotificationSocket,
)


class _StopLoopError(Exception):
    """Raised by the test sleep to end an otherwise endless reconnect loop."""


class _FakeWebSocket:
    """Yield queued messages, then end as if the console closed the socket."""

    def __init__(self, messages: list[aiohttp.WSMessage]) -> None:
        self._messages = list(messages)
        self.closed = False
        self.close = AsyncMock(side_effect=self._mark_closed)

    async def _mark_closed(self) -> None:
        self.closed = True

    def __aiter__(self) -> _FakeWebSocket:
        return self

    async def __anext__(self) -> aiohttp.WSMessage:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


def _text(payload: str) -> aiohttp.WSMessage:
    return aiohttp.WSMessage(aiohttp.WSMsgType.TEXT, payload, None)


def _handshake_error(status: int) -> aiohttp.WSServerHandshakeError:
    return aiohttp.WSServerHandshakeError(
        request_info=MagicMock(), history=(), status=status, message="rejected"
    )


def _client(ws_connect: AsyncMock, *, verify_tls: bool | None = False) -> MagicMock:
    """Return a client double with the transport methods the socket calls."""
    client = MagicMock(name="access_client")
    session = MagicMock(name="session")
    session.ws_connect = ws_connect
    client._ensure_session = AsyncMock(return_value=session)
    client._build_url = MagicMock(
        return_value=URL("https://console.local:12445/api/v1/developer/devices/notifications")
    )
    client._get_headers = MagicMock(return_value={"Authorization": "Bearer token"})
    client._throttle = AsyncMock()
    client._ssl_for_request = MagicMock(return_value=verify_tls)
    return client


def _sleeps(limit: int) -> AsyncMock:
    """Record reconnect delays and stop the loop after ``limit`` waits."""
    recorded: list[float] = []

    async def _sleep(delay: float) -> None:
        recorded.append(delay)
        if len(recorded) >= limit:
            raise _StopLoopError

    sleep = AsyncMock(side_effect=_sleep)
    sleep.recorded = recorded  # type: ignore[attr-defined]
    return sleep


@pytest.mark.parametrize("status", [401, 403, 404])
async def test_permanent_handshake_answer_stops_once_without_retry(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """401, 403 and 404 are reported once to the owner and never retried."""
    ws_connect = AsyncMock(side_effect=_handshake_error(status))
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)
    on_stop = MagicMock()

    await AccessNotificationSocket(_client(ws_connect)).run(MagicMock(), on_stop=on_stop)

    on_stop.assert_called_once_with(status)
    ws_connect.assert_awaited_once()
    sleep.assert_not_awaited()


async def test_permanent_stop_does_not_await_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The owner's callback runs synchronously; run returns without waiting on it."""
    ws_connect = AsyncMock(side_effect=_handshake_error(403))
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    seen: list[int] = []

    await AccessNotificationSocket(_client(ws_connect)).run(MagicMock(), on_stop=seen.append)

    assert seen == [403]


async def test_transient_failures_back_off_then_stop_on_permanent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5xx, 429, connect timeouts and transport errors all retry with backoff."""
    ws_connect = AsyncMock(
        side_effect=[
            _handshake_error(503),
            _handshake_error(429),
            TimeoutError(),
            aiohttp.ClientConnectionError("reset"),
            _handshake_error(403),
        ]
    )
    sleep = _sleeps(limit=100)
    monkeypatch.setattr(asyncio, "sleep", sleep)
    on_stop = MagicMock()

    await AccessNotificationSocket(_client(ws_connect)).run(
        MagicMock(), on_stop=on_stop, reconnect_delay=5.0
    )

    assert sleep.recorded == [5.0, 10.0, 20.0, 40.0]  # type: ignore[attr-defined]
    on_stop.assert_called_once_with(403)


async def test_backoff_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reconnect delay never exceeds the five-minute cap."""
    ws_connect = AsyncMock(side_effect=[_handshake_error(502)] * 4 + [_handshake_error(403)])
    sleep = _sleeps(limit=100)
    monkeypatch.setattr(asyncio, "sleep", sleep)

    await AccessNotificationSocket(_client(ws_connect)).run(
        MagicMock(), on_stop=MagicMock(), reconnect_delay=200.0
    )

    assert sleep.recorded == [200.0, 300.0, 300.0, 300.0]  # type: ignore[attr-defined]


async def test_successful_handshake_resets_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A connection that opens restarts the delay from the configured value."""
    ws_connect = AsyncMock(
        side_effect=[
            _handshake_error(503),
            _FakeWebSocket([]),
            _handshake_error(503),
            _handshake_error(403),
        ]
    )
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    await AccessNotificationSocket(_client(ws_connect)).run(
        MagicMock(), on_stop=MagicMock(), reconnect_delay=5.0
    )

    assert [call.args[0] for call in sleep.await_args_list] == [5.0, 5.0, 10.0]


async def test_connect_timeout_is_transient_not_a_crash(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A connect timeout is logged by type and retried, never raised out of run."""
    ws_connect = AsyncMock(side_effect=[TimeoutError(), _handshake_error(403)])
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    on_stop = MagicMock()

    with caplog.at_level(logging.WARNING):
        await AccessNotificationSocket(_client(ws_connect)).run(MagicMock(), on_stop=on_stop)

    assert "TimeoutError" in caplog.text
    on_stop.assert_called_once_with(403)


async def test_cancellation_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cancelling the socket task raises CancelledError rather than retrying."""
    ws_connect = AsyncMock(side_effect=asyncio.CancelledError)
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    with pytest.raises(asyncio.CancelledError):
        await AccessNotificationSocket(_client(ws_connect)).run(MagicMock(), on_stop=MagicMock())

    sleep.assert_not_awaited()


async def test_text_frames_are_parsed_and_unusable_ones_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only JSON object text frames reach the handler."""
    socket_messages = _FakeWebSocket(
        [
            _text('{"event": "access.remote_view", "data": {"device_id": "reader"}}'),
            _text("not json"),
            _text("[1, 2, 3]"),
            aiohttp.WSMessage(aiohttp.WSMsgType.BINARY, b"\x00", None),
        ]
    )
    ws_connect = AsyncMock(side_effect=[socket_messages, _handshake_error(403)])
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    frames: list[dict[str, Any]] = []

    await AccessNotificationSocket(_client(ws_connect)).run(frames.append, on_stop=MagicMock())

    assert frames == [{"event": "access.remote_view", "data": {"device_id": "reader"}}]
    socket_messages.close.assert_awaited_once()


async def test_error_frame_ends_the_connection_and_reconnects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ERROR frame closes the connection; the socket then reconnects."""
    errored = _FakeWebSocket([aiohttp.WSMessage(aiohttp.WSMsgType.ERROR, None, None)])
    ws_connect = AsyncMock(side_effect=[errored, _handshake_error(403)])
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    await AccessNotificationSocket(_client(ws_connect)).run(
        MagicMock(), on_stop=MagicMock(), reconnect_delay=5.0
    )

    sleep.assert_awaited_once_with(5.0)
    assert ws_connect.await_count == 2


async def test_handler_failure_is_logged_by_type_only(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A handler that fails never leaks the frame or its exception text into logs."""
    socket_messages = _FakeWebSocket(
        [
            _text('{"event": "first", "secret": "frame-secret-value"}'),
            _text('{"event": "second"}'),
        ]
    )
    ws_connect = AsyncMock(side_effect=[socket_messages, _handshake_error(403)])
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    delivered: list[str] = []

    def _handler(frame: dict[str, Any]) -> None:
        delivered.append(str(frame["event"]))
        if frame["event"] == "first":
            message = "contains frame-secret-value"
            raise ValueError(message)

    with caplog.at_level(logging.DEBUG):
        await AccessNotificationSocket(_client(ws_connect)).run(_handler, on_stop=MagicMock())

    assert delivered == ["first", "second"]
    assert "ValueError" in caplog.text
    assert "frame-secret-value" not in caplog.text


async def test_connect_uses_wss_bearer_heartbeat_and_tls_policy() -> None:
    """The handshake uses wss, the bearer header and the client's TLS setting."""
    ws_connect = AsyncMock(return_value=_FakeWebSocket([]))
    client = _client(ws_connect, verify_tls=False)

    await AccessNotificationSocket(client)._connect()

    ws_connect.assert_awaited_once_with(
        "wss://console.local:12445/api/v1/developer/devices/notifications",
        headers={"Authorization": "Bearer token"},
        heartbeat=30,
        ssl=False,
    )
    client._throttle.assert_awaited_once()


async def test_connect_keeps_verification_when_client_has_no_override() -> None:
    """With no per-request override, the socket verifies TLS."""
    ws_connect = AsyncMock(return_value=_FakeWebSocket([]))
    client = _client(ws_connect, verify_tls=None)

    await AccessNotificationSocket(client)._connect()

    assert ws_connect.await_args is not None
    assert ws_connect.await_args.kwargs["ssl"] is True


async def test_hung_close_is_bounded_before_reconnect(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Real aiohttp close must stop even when each frame renews its own timeout."""
    monkeypatch.setattr(
        "unifi_official_api.access.websocket._CLOSE_TIMEOUT_SECONDS",
        0.05,
    )

    async def _continuing_frame() -> aiohttp.WSMessage:
        await asyncio.sleep(0.001)
        return _text('{"event":"notification"}')

    class _FinishedConsumer(aiohttp.ClientWebSocketResponse):
        async def __anext__(self) -> aiohttp.WSMessage:
            raise StopAsyncIteration

    reader = MagicMock()
    reader.read = AsyncMock(side_effect=_continuing_frame)
    writer = MagicMock()
    writer.close = AsyncMock()
    response = MagicMock()
    ws = _FinishedConsumer(
        reader=reader,
        writer=writer,
        protocol=None,
        response=response,
        timeout=evolve(aiohttp.ClientWSTimeout(), ws_close=0.02),
        autoclose=True,
        autoping=True,
        loop=asyncio.get_running_loop(),
    )
    connect = AsyncMock(side_effect=[ws, _handshake_error(403)])
    on_stop = MagicMock()

    with caplog.at_level(logging.DEBUG):
        await asyncio.wait_for(
            AccessNotificationSocket(_client(connect)).run(
                MagicMock(), on_stop=on_stop, reconnect_delay=0.0
            ),
            timeout=0.3,
        )

    assert reader.read.await_count > 1
    writer.close.assert_awaited_once()
    response.close.assert_called_once()
    assert ws.closed
    assert ws.close_code == aiohttp.WSCloseCode.ABNORMAL_CLOSURE
    assert connect.await_count == 2
    on_stop.assert_called_once_with(403)
    assert "Timed out closing the Access notification socket" in caplog.text


async def test_stalled_close_is_bounded_on_the_cancel_path_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelled consumers bound cleanup even if a close implementation stalls."""
    monkeypatch.setattr(
        "unifi_official_api.access.websocket._CLOSE_TIMEOUT_SECONDS",
        0.01,
    )
    receiving = asyncio.Event()
    closed_cancelled = asyncio.Event()

    class _WaitingSocket(_FakeWebSocket):
        async def __anext__(self) -> aiohttp.WSMessage:
            receiving.set()
            await asyncio.Event().wait()
            raise StopAsyncIteration

    async def _hung_close() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            closed_cancelled.set()

    ws = _WaitingSocket([])
    ws.close = AsyncMock(side_effect=_hung_close)
    connect = AsyncMock(return_value=ws)
    task = asyncio.create_task(
        AccessNotificationSocket(_client(connect)).run(MagicMock(), on_stop=MagicMock())
    )
    await asyncio.wait_for(receiving.wait(), timeout=0.3)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=0.3)

    assert closed_cancelled.is_set()
    connect.assert_awaited_once()
