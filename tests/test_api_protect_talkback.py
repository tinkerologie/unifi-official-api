# Copyright 2026 UniFi Insights contributors
"""Tests for UniFi Protect talkback audio transport."""

import asyncio
import sys
import threading
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from unifi_official_api.protect.models.files import TalkbackSession
from unifi_official_api.protect.talkback import (
    TalkbackCodecError,
    TalkbackError,
    TalkbackImportError,
    TalkbackSamplingRateError,
    TalkbackSchemeError,
    TalkbackStream,
    TalkbackStreamError,
    _sanitize_url,
    _transcode_and_stream,
    validate_talkback_session,
)


def _make_session(
    url: str = "rtp://192.168.1.10:7004",
    codec: str = "opus",
    sampling_rate: int = 24000,
    bits_per_sample: int = 16,
) -> TalkbackSession:
    """Helper to construct a TalkbackSession."""
    return TalkbackSession(
        url=url,
        codec=codec,
        samplingRate=sampling_rate,
        bitsPerSample=bits_per_sample,
    )


def test_validate_talkback_session_valid() -> None:
    """Test valid talkback session configurations."""
    # RTP + Opus
    validate_talkback_session(_make_session("rtp://10.0.0.1:7004", "opus", 24000, 16))
    # UDP + AAC
    validate_talkback_session(_make_session("udp://10.0.0.1:7004", "aac", 44100, 16))
    # Vorbis
    validate_talkback_session(_make_session("rtp://10.0.0.1:7004", "vorbis", 48000, 16))


def test_validate_talkback_session_invalid_url() -> None:
    """Test invalid or unsupported talkback session URLs."""
    # Missing URL
    with pytest.raises(TalkbackSchemeError, match="Talkback session URL is required"):
        validate_talkback_session(_make_session(url=""))

    # Unsupported scheme (wss://)
    with pytest.raises(TalkbackSchemeError, match="Unsupported talkback URL scheme: 'wss'"):
        validate_talkback_session(_make_session(url="wss://10.0.0.1:7004"))

    # Unsupported scheme (http://)
    with pytest.raises(TalkbackSchemeError, match="Unsupported talkback URL scheme: 'http'"):
        validate_talkback_session(_make_session(url="http://10.0.0.1:7004"))


def test_validate_talkback_session_invalid_codec() -> None:
    """Test invalid or unsupported talkback session codecs."""
    # Missing codec
    with pytest.raises(TalkbackCodecError, match="Talkback session codec is required"):
        validate_talkback_session(_make_session(codec=""))

    # Unsupported codec
    with pytest.raises(TalkbackCodecError, match="Unsupported talkback codec: 'mp3'"):
        validate_talkback_session(_make_session(codec="mp3"))


@pytest.mark.parametrize("rate", [0, -1, None, "24000", True])
def test_validate_talkback_session_invalid_sampling_rate(rate: int) -> None:
    """Test invalid sampling rates."""
    session = _make_session()
    # Bypass Pydantic validation by setting attribute directly
    object.__setattr__(session, "sampling_rate", rate)
    with pytest.raises(TalkbackSamplingRateError, match="Invalid talkback sampling rate"):
        validate_talkback_session(session)


def test_transcode_and_stream_missing_pyav() -> None:
    """Test TalkbackImportError when PyAV is not installed."""
    session = _make_session()
    stop_event = threading.Event()

    with (
        patch.dict(sys.modules, {"av": None, "av.audio.resampler": None}),
        pytest.raises(TalkbackImportError, match="PyAV is required"),
    ):
        _transcode_and_stream(session, "media.mp3", stop_event)


def test_transcode_and_stream_open_input_failure() -> None:
    """Test TalkbackStreamError when opening source media fails."""
    session = _make_session()
    stop_event = threading.Event()

    mock_av = MagicMock()
    mock_av.open.side_effect = RuntimeError("File not found")

    with (
        patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}),
        pytest.raises(TalkbackStreamError, match="Failed to open source media"),
    ):
        _transcode_and_stream(session, "missing.mp3", stop_event)


def test_transcode_and_stream_no_audio_streams() -> None:
    """Test TalkbackStreamError when source media has no audio streams."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = []

    mock_av = MagicMock()
    mock_av.open.return_value = mock_input

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        with pytest.raises(TalkbackStreamError, match="No audio streams found"):
            _transcode_and_stream(session, "silent.mp4", stop_event)
        mock_input.close.assert_called_once()


def test_transcode_and_stream_open_output_failure() -> None:
    """Test TalkbackStreamError when opening destination stream fails."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]

    mock_av = MagicMock()
    # First call succeeds (input), second call raises (output)
    mock_av.open.side_effect = [mock_input, RuntimeError("Cannot bind socket")]

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        with pytest.raises(TalkbackStreamError, match="Failed to open destination stream"):
            _transcode_and_stream(session, "media.mp3", stop_event)
        mock_input.close.assert_called_once()


def test_transcode_and_stream_open_input_failure_redacts_query() -> None:
    """Test TalkbackStreamError redacts query parameters from source URL."""
    session = _make_session()
    stop_event = threading.Event()

    mock_av = MagicMock()
    mock_av.open.side_effect = RuntimeError("File not found")

    with (
        patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}),
        pytest.raises(TalkbackStreamError) as exc_info,
    ):
        _transcode_and_stream(
            session,
            "http://user:password@ha.local/media.mp3?authSig=supersecret123#fragment",
            stop_event,
        )

    err_msg = str(exc_info.value)
    assert "user:password@" not in err_msg
    assert "password" not in err_msg
    assert "supersecret123" not in err_msg
    assert "fragment" not in err_msg
    assert "http://ha.local/media.mp3" in err_msg


def test_transcode_and_stream_open_output_failure_redacts_query() -> None:
    """Test TalkbackStreamError redacts credentials from destination URL."""
    session = _make_session(url="rtp://user:password@192.168.1.10:7004?token=secrettoken#frag")
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, RuntimeError("Cannot bind socket")]

    with (
        patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}),
        pytest.raises(TalkbackStreamError) as exc_info,
    ):
        _transcode_and_stream(session, "media.mp3", stop_event)

    err_msg = str(exc_info.value)
    assert "user:password@" not in err_msg
    assert "password" not in err_msg
    assert "secrettoken" not in err_msg
    assert "frag" not in err_msg
    assert "rtp://192.168.1.10:7004" in err_msg


def test_sanitize_url_helper() -> None:
    """Test _sanitize_url strips userinfo, parameters, fragments, and bad URLs."""
    assert (
        _sanitize_url("http://example.com/audio.mp3?key=val#frag") == "http://example.com/audio.mp3"
    )
    assert (
        _sanitize_url("http://user:pass@example.com/audio.mp3?key=val#frag")
        == "http://example.com/audio.mp3"
    )
    assert _sanitize_url("rtp://admin:secret@192.168.1.10:7004") == "rtp://192.168.1.10:7004"
    assert _sanitize_url("/local/doorbell.wav?authSig=abc") == "/local/doorbell.wav"
    assert _sanitize_url("rtp://192.168.1.10:7004") == "rtp://192.168.1.10:7004"
    with patch("urllib.parse.urlsplit", side_effect=ValueError("bad")):
        assert _sanitize_url("anything") == "<invalid-url>"


@pytest.mark.parametrize(
    ("bit_depth", "expected_fmt"),
    [(8, "u8"), (16, "s16"), (32, "s32"), (24, "s16")],
)
def test_transcode_and_stream_bit_depth_mapping(bit_depth: int, expected_fmt: str) -> None:
    """Test bit-depth mapping and fallback."""
    session = _make_session(bits_per_sample=bit_depth)
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    mock_input.decode.return_value = []

    mock_output = MagicMock()
    mock_stream = MagicMock()
    mock_stream.format = None
    mock_output.add_stream.return_value = mock_stream

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_resampler_cls = MagicMock()
    mock_av.audio.resampler.AudioResampler = mock_resampler_cls

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        _transcode_and_stream(session, "media.mp3", stop_event)

        mock_resampler_cls.assert_called_once_with(
            format=expected_fmt,
            layout="mono",
            rate=session.sampling_rate,
        )


def test_transcode_and_stream_playback_success() -> None:
    """Test full playback loop transcoding, pacing, and flushing."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input_stream = MagicMock()
    mock_input.streams.audio = [mock_input_stream]

    # Two input frames
    frame1 = MagicMock()
    frame2 = MagicMock()
    mock_input.decode.return_value = [frame1, frame2]

    # Resampled frames
    r_frame1 = MagicMock(samples=480)
    r_frame2 = MagicMock(samples=480)
    flush_frame = MagicMock(samples=240)

    mock_resampler = MagicMock()
    mock_resampler.resample.side_effect = [
        [r_frame1],
        [r_frame2],
        [flush_frame],  # flush resample(None)
    ]

    mock_output = MagicMock()
    mock_output_stream = MagicMock()
    mock_output_stream.format = "s16"
    mock_output.add_stream.return_value = mock_output_stream

    packet1 = MagicMock()
    packet2 = MagicMock()
    packet3 = MagicMock()
    packet_final = MagicMock()

    # encode calls
    mock_output_stream.encode.side_effect = [
        [packet1],
        [packet2],
        [packet3],
        [packet_final],
    ]

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        _transcode_and_stream(session, "media.mp3", stop_event)

        assert mock_output.mux.call_count == 4
        mock_input.close.assert_called_once()
        mock_output.close.assert_called_once()


def test_transcode_and_stream_cooperative_stop_between_frames() -> None:
    """Test cooperative stop between input frames skips encoder flush."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]

    frame1 = MagicMock()
    frame2 = MagicMock()
    mock_input.decode.return_value = [frame1, frame2]

    r_frame1 = MagicMock(samples=480)

    def _resample_side_effect(frame: Any) -> list[Any]:
        if frame is frame1:
            return [r_frame1]
        if frame is frame2:
            stop_event.set()
            return []
        return []

    mock_resampler = MagicMock()
    mock_resampler.resample.side_effect = _resample_side_effect

    mock_output = MagicMock()
    mock_output_stream = MagicMock()
    mock_output.add_stream.return_value = mock_output_stream
    mock_output_stream.encode.return_value = [MagicMock()]

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        _transcode_and_stream(session, "media.mp3", stop_event)

        # encode should have been called only for r_frame1, and no flush encode(None)
        mock_output_stream.encode.assert_called_once_with(r_frame1)


def test_transcode_and_stream_cooperative_stop_during_pacing() -> None:
    """Test cooperative stop during Event.wait pacing."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    # Two frames so that on the second frame played_duration > 0 and delay > 0
    frame1 = MagicMock()
    frame2 = MagicMock()
    mock_input.decode.return_value = [frame1, frame2]

    r_frame1 = MagicMock(samples=24000)  # 1 second of audio
    r_frame2 = MagicMock(samples=24000)

    mock_resampler = MagicMock()
    mock_resampler.resample.side_effect = [[r_frame1], [r_frame2]]

    mock_output = MagicMock()
    mock_output_stream = MagicMock()
    mock_output.add_stream.return_value = mock_output_stream
    mock_output_stream.encode.return_value = []

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    # Simulate stop_event being set during pacing wait
    def _fake_wait(timeout: float) -> bool:
        stop_event.set()
        return True

    with patch.object(stop_event, "wait", side_effect=_fake_wait) as mock_wait:
        with patch.dict(
            sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}
        ):
            _transcode_and_stream(session, "media.mp3", stop_event)

        assert mock_wait.called
        assert stop_event.is_set()


def test_transcode_and_stream_close_exceptions_suppressed() -> None:
    """Test exceptions during container close are safely ignored."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    mock_input.decode.return_value = []
    mock_input.close.side_effect = RuntimeError("Input close error")

    mock_output = MagicMock()
    mock_output.add_stream.return_value = MagicMock()
    mock_output.close.side_effect = RuntimeError("Output close error")

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        _transcode_and_stream(session, "media.mp3", stop_event)


@pytest.mark.asyncio
async def test_talkback_stream_lifecycle() -> None:
    """Test TalkbackStream start, running, stop, and complete."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")

    assert not stream.running

    with patch("unifi_official_api.protect.talkback._transcode_and_stream") as mock_worker:
        # Start
        await stream.start()
        # Double start is a no-op
        await stream.start()

        # Wait until finished
        await stream.wait_until_complete()

        mock_worker.assert_called_once_with(session, "media.mp3", stream._stop_event)
        assert not stream.running

        # Idempotent stop
        await stream.stop()
        await stream.stop()


@pytest.mark.asyncio
async def test_talkback_stream_worker_error_propagation() -> None:
    """Test worker error propagation through wait_until_complete."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")

    with patch(
        "unifi_official_api.protect.talkback._transcode_and_stream",
        side_effect=TalkbackStreamError("Worker crash"),
    ):
        await stream.start()

        # Stop should not raise despite worker error
        await stream.stop()

        with pytest.raises(TalkbackStreamError, match="Worker crash"):
            await stream.wait_until_complete()


@pytest.mark.asyncio
async def test_talkback_stream_wait_until_complete_stored_error() -> None:
    """Test wait_until_complete re-raises stored _error if worker task is None."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    stream._error = TalkbackError("Pre-existing error")

    with pytest.raises(TalkbackError, match="Pre-existing error"):
        await stream.wait_until_complete()


def test_transcode_and_stream_stop_before_next_decode_frame() -> None:
    """Test stop_event.is_set() at the start of decode frame loop."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    frame1 = MagicMock()
    frame2 = MagicMock()
    mock_input.decode.return_value = [frame1, frame2]

    r_frame1 = MagicMock(samples=480)

    def _resample(frame: Any) -> list[Any]:
        stop_event.set()
        return [r_frame1]

    mock_resampler = MagicMock()
    mock_resampler.resample.side_effect = _resample

    mock_output = MagicMock()
    mock_output_stream = MagicMock()
    mock_output.add_stream.return_value = mock_output_stream
    mock_output_stream.encode.return_value = []

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        _transcode_and_stream(session, "media.mp3", stop_event)

    assert stop_event.is_set()
    mock_input.close.assert_called_once()
    mock_output.close.assert_called_once()


def test_transcode_and_stream_stop_inside_resampled_frames() -> None:
    """Test stop_event.is_set() inside inner resampled frame loop."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    mock_input.decode.return_value = [MagicMock()]

    r_frame1 = MagicMock(samples=480)
    r_frame2 = MagicMock(samples=480)

    mock_resampler = MagicMock()
    mock_resampler.resample.return_value = [r_frame1, r_frame2]

    mock_output = MagicMock()
    mock_output_stream = MagicMock()
    mock_output.add_stream.return_value = mock_output_stream

    def _encode(rf: Any) -> list[Any]:
        stop_event.set()
        return []

    mock_output_stream.encode.side_effect = _encode

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    with patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}):
        _transcode_and_stream(session, "media.mp3", stop_event)

    assert stop_event.is_set()
    mock_input.close.assert_called_once()
    mock_output.close.assert_called_once()


def test_transcode_and_stream_stop_when_delay_negative() -> None:
    """Test delay <= 0 and stop_event.is_set() branch at line 207."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    mock_input.decode.return_value = [MagicMock()]

    r_frame = MagicMock(samples=480)
    mock_resampler = MagicMock()

    def _resample(frame: Any) -> list[Any]:
        stop_event.set()
        return [r_frame]

    mock_resampler.resample.side_effect = _resample

    mock_output = MagicMock()
    mock_output_stream = MagicMock()
    mock_output.add_stream.return_value = mock_output_stream
    mock_output_stream.encode.return_value = []

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    # Patch time.monotonic to advance so delay <= 0
    with (
        patch("time.monotonic", side_effect=[100.0, 200.0, 300.0]),
        patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}),
    ):
        _transcode_and_stream(session, "media.mp3", stop_event)

    assert stop_event.is_set()
    mock_input.close.assert_called_once()
    mock_output.close.assert_called_once()


def test_transcode_and_stream_generic_runtime_error_during_mux() -> None:
    """Test generic Exception during loop wrapped into TalkbackStreamError."""
    session = _make_session()
    stop_event = threading.Event()

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    mock_input.decode.return_value = [MagicMock()]

    mock_resampler = MagicMock()
    mock_resampler.resample.return_value = [MagicMock(samples=480)]

    mock_output = MagicMock()
    mock_output_stream = MagicMock()
    mock_output.add_stream.return_value = mock_output_stream
    mock_output_stream.encode.return_value = [MagicMock()]
    mock_output.mux.side_effect = RuntimeError("Broken pipe")

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    with (
        patch.dict(sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}),
        pytest.raises(TalkbackStreamError, match="Error during talkback stream: RuntimeError"),
    ):
        _transcode_and_stream(session, "media.mp3", stop_event)


@pytest.mark.asyncio
async def test_talkback_stream_stop_before_start() -> None:
    """Test stop() when stream has not been started."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    await stream.stop()
    assert not stream.running


@pytest.mark.asyncio
async def test_talkback_stream_wait_until_complete_unstarted() -> None:
    """Test wait_until_complete() when stream has not been started and no error."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    await stream.wait_until_complete()


@pytest.mark.parametrize("outcome", ["success", "error"])
@pytest.mark.asyncio
async def test_talkback_stream_worker_skips_cancelled_future(outcome: str) -> None:
    """Test worker does not resolve a future cancelled by its waiter."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    mux_entered = threading.Event()
    release_mux = threading.Event()
    mux_error = RuntimeError("mux failed")

    def _mux(packet: Any) -> None:
        mux_entered.set()
        assert release_mux.wait(timeout=5)
        if outcome == "error":
            raise mux_error

    mock_input = MagicMock()
    mock_input.streams.audio = [MagicMock()]
    mock_input.decode.return_value = [MagicMock()]
    mock_resampler = MagicMock()
    mock_resampler.resample.side_effect = lambda frame: (
        [] if frame is None else [MagicMock(samples=0)]
    )
    mock_output_stream = MagicMock()
    mock_output_stream.encode.side_effect = lambda frame: [] if frame is None else [MagicMock()]
    mock_output = MagicMock()
    mock_output.add_stream.return_value = mock_output_stream
    mock_output.mux.side_effect = _mux

    mock_av = MagicMock()
    mock_av.open.side_effect = [mock_input, mock_output]
    mock_av.audio.resampler.AudioResampler.return_value = mock_resampler

    loop = asyncio.get_running_loop()
    loop_errors: list[dict[str, Any]] = []
    original_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, ctx: loop_errors.append(ctx))

    try:
        with patch.dict(
            sys.modules, {"av": mock_av, "av.audio.resampler": mock_av.audio.resampler}
        ):
            await stream.start()
            assert await asyncio.to_thread(mux_entered.wait, 5)

            waiter = asyncio.create_task(stream.wait_until_complete())
            await asyncio.sleep(0)
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter

            # Cancelling the waiter cancels the worker future, not the thread
            assert not stream.running
            assert stream._thread is not None
            assert stream._thread.is_alive()

            release_mux.set()
            await asyncio.to_thread(stream._thread.join, 5)
            assert not stream._thread.is_alive()
            # Let any call_soon_threadsafe callbacks from the worker run
            await asyncio.sleep(0)
            await asyncio.sleep(0)
    finally:
        release_mux.set()
        loop.set_exception_handler(original_handler)

    assert loop_errors == []
    mock_output.close.assert_called_once()
    mock_input.close.assert_called_once()
    if outcome == "error":
        assert isinstance(stream._error, TalkbackStreamError)
        assert stream._error.__cause__ is mux_error
    else:
        assert stream._error is None


@pytest.mark.asyncio
async def test_talkback_stream_stop_with_cancelled_future() -> None:
    """Test stop() when _worker_future was directly cancelled."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    worker_started = threading.Event()
    release_worker = threading.Event()

    def _worker(
        sess: Any,
        media_url: str,
        stop_event: threading.Event,
    ) -> None:
        """Simulate worker execution until stopped and released."""
        worker_started.set()
        stop_event.wait(timeout=5)
        release_worker.wait(timeout=5)

    with patch(
        "unifi_official_api.protect.talkback._transcode_and_stream",
        side_effect=_worker,
    ):
        try:
            await stream.start()
            assert await asyncio.to_thread(worker_started.wait, 5)
            assert stream._worker_future is not None
            stream._worker_future.cancel()
            assert stream._worker_future.done()
            assert stream._worker_future.cancelled()

            # Calling stop() sets stop_event and returns without awaiting/raising
            await stream.stop()
            assert stream._stop_event.is_set()
            release_worker.set()
            assert stream._thread is not None
            await asyncio.to_thread(stream._thread.join, 5)
            assert not stream._thread.is_alive()
        finally:
            release_worker.set()
            stream._stop_event.set()
            if stream._thread is not None:
                stream._thread.join(timeout=5)


@pytest.mark.asyncio
async def test_talkback_stream_cancelled_waiter_leaves_worker_running() -> None:
    """Test reproducing ticket: cancelled waiter leaves worker alive until stop."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    worker_started = threading.Event()
    release_worker = threading.Event()

    def _worker(
        sess: Any,
        media_url: str,
        stop_event: threading.Event,
    ) -> None:
        """Simulate worker execution until stopped and released."""
        worker_started.set()
        stop_event.wait(timeout=5)
        release_worker.wait(timeout=5)

    with patch(
        "unifi_official_api.protect.talkback._transcode_and_stream",
        side_effect=_worker,
    ):
        try:
            await stream.start()
            assert await asyncio.to_thread(worker_started.wait, 5)

            waiter = asyncio.create_task(stream.wait_until_complete())
            await asyncio.sleep(0)
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter

            # Future was cancelled by waiter, so running is False, but thread is alive
            assert not stream.running
            assert stream._thread is not None
            assert stream._thread.is_alive()

            # Now stop() signals the worker and returns without raising CancelledError
            await stream.stop()
            assert stream._stop_event.is_set()
            release_worker.set()
            await asyncio.to_thread(stream._thread.join, 5)
            assert not stream._thread.is_alive()
        finally:
            release_worker.set()
            stream._stop_event.set()
            if stream._thread is not None:
                stream._thread.join(timeout=5)


@pytest.mark.parametrize("outcome", ["success", "error"])
@pytest.mark.asyncio
async def test_talkback_stream_resolve_callback_race(outcome: str) -> None:
    """Test race where future is cancelled before resolve callback runs on loop."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    worker_finished = threading.Event()
    worker_error = RuntimeError("transcode crashed")

    def _worker(
        sess: Any,
        media_url: str,
        stop_event: threading.Event,
    ) -> None:
        """Simulate worker execution yielding an error or normal exit."""
        try:
            if outcome == "error":
                raise worker_error
        finally:
            worker_finished.set()

    loop = asyncio.get_running_loop()
    original_call_soon_threadsafe = loop.call_soon_threadsafe
    captured_callbacks: list[tuple[Any, tuple[Any, ...]]] = []

    def _intercept_call_soon_threadsafe(callback: Any, *args: Any) -> Any:
        """Intercept threadsafe callbacks targeting the worker resolver."""
        if getattr(callback, "__name__", None) == "_resolve":
            captured_callbacks.append((callback, args))
            return None
        return original_call_soon_threadsafe(callback, *args)

    with (
        patch(
            ("unifi_official_api.protect.talkback._transcode_and_stream"),
            side_effect=_worker,
        ),
        patch.object(loop, "call_soon_threadsafe", side_effect=_intercept_call_soon_threadsafe),
    ):
        try:
            await stream.start()
            assert await asyncio.to_thread(worker_finished.wait, 5)
            assert stream._thread is not None
            await asyncio.to_thread(stream._thread.join, 5)
            assert not stream._thread.is_alive()

            # Worker finished and scheduled call_soon_threadsafe(_resolve, ...)
            assert len(captured_callbacks) == 1
            cb, cb_args = captured_callbacks[0]

            # Simulate race: future is cancelled before callback executes on loop
            assert stream._worker_future is not None
            stream._worker_future.cancel()
            assert stream._worker_future.done()

            # Invoking the callback must return safely without InvalidStateError
            cb(*cb_args)

            if outcome == "error":
                assert stream._error is worker_error
            else:
                assert stream._error is None
        finally:
            if stream._thread is not None:
                stream._thread.join(timeout=5)


@pytest.mark.asyncio
async def test_talkback_stream_stop_after_completed_worker_error() -> None:
    """Test stop() after worker error completes future; wait_until_complete raises."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    worker_error = RuntimeError("transcode crashed")

    def _worker(
        sess: Any,
        media_url: str,
        stop_event: threading.Event,
    ) -> None:
        """Simulate worker failure by raising a runtime error."""
        raise worker_error

    with patch(
        "unifi_official_api.protect.talkback._transcode_and_stream",
        side_effect=_worker,
    ):
        try:
            await stream.start()
            assert stream._thread is not None
            await asyncio.to_thread(stream._thread.join, 5)
            assert not stream._thread.is_alive()

            # Yield to let the resolve callback execute on the loop
            await asyncio.sleep(0)
            assert stream._worker_future is not None
            assert stream._worker_future.done()
            assert not stream._worker_future.cancelled()

            # Calling stop() should retrieve exception without raising
            await stream.stop()

            # wait_until_complete should still raise the stored error
            with pytest.raises(RuntimeError, match="transcode crashed"):
                await stream.wait_until_complete()
        finally:
            if stream._thread is not None:
                stream._thread.join(timeout=5)


@pytest.mark.asyncio
async def test_talkback_stream_pending_stop_caller_cancellation() -> None:
    """Test caller cancellation during stop propagates while shield protects future."""
    session = _make_session()
    stream = TalkbackStream(session, "media.mp3")
    worker_started = threading.Event()
    worker_unblock = threading.Event()

    def _worker(
        sess: Any,
        media_url: str,
        stop_event: threading.Event,
    ) -> None:
        """Simulate worker execution until manually unblocked."""
        worker_started.set()
        worker_unblock.wait(timeout=5)

    with patch(
        "unifi_official_api.protect.talkback._transcode_and_stream",
        side_effect=_worker,
    ):
        try:
            await stream.start()
            assert await asyncio.to_thread(worker_started.wait, 5)
            assert stream.running is True

            stop_task = asyncio.create_task(stream.stop())
            await asyncio.sleep(0)

            # Cancel caller of stop()
            stop_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await stop_task

            # Underlying future is shielded, so still pending and running
            assert stream.running is True
            assert stream._worker_future is not None
            assert not stream._worker_future.done()

            # Unblock worker and let it finish cleanly
            worker_unblock.set()
            assert stream._thread is not None
            await asyncio.to_thread(stream._thread.join, 5)
            await asyncio.sleep(0)
            assert not stream.running
        finally:
            worker_unblock.set()
            stream._stop_event.set()
            if stream._thread is not None:
                stream._thread.join(timeout=5)


@pytest.mark.asyncio
async def test_talkback_stream_custom_executor_success() -> None:
    """Test custom executor running talkback stream successfully."""
    session = _make_session()

    async def fake_executor(func: Any, *args: Any) -> None:
        return None

    stream = TalkbackStream(session, "media.mp3", executor=fake_executor)
    await stream.start()
    await stream.wait_until_complete()
    assert stream.running is False


@pytest.mark.asyncio
async def test_talkback_stream_custom_executor_failure() -> None:
    """Test custom executor error propagation."""
    session = _make_session()

    async def fake_failing_executor(func: Any, *args: Any) -> None:
        raise RuntimeError("executor error")

    stream = TalkbackStream(session, "media.mp3", executor=fake_failing_executor)
    await stream.start()
    with pytest.raises(RuntimeError, match="executor error"):
        await stream.wait_until_complete()
    assert stream.running is False


def test_talkback_stream_rejects_third_positional_argument() -> None:
    """A legacy third positional context argument raises TypeError."""
    with pytest.raises(TypeError, match="positional"):
        TalkbackStream(_make_session(), "media.mp3", MagicMock())  # type: ignore[call-arg]


def test_talkback_stream_rejects_media_url_keyword() -> None:
    """The removed media_url name is neither a keyword nor an attribute."""
    with pytest.raises(TypeError, match="media_url"):
        TalkbackStream(_make_session(), media_url="media.mp3")  # type: ignore[call-arg]
    stream = TalkbackStream(_make_session(), "media.mp3")
    assert stream.media_source == "media.mp3"
    assert not hasattr(stream, "media_url")


@pytest.mark.asyncio
async def test_talkback_stream_explicit_loop_runs_in_daemon_thread() -> None:
    """With loop= and no executor, the worker runs in a daemon thread on that loop."""
    session = _make_session()
    loop = asyncio.get_running_loop()
    stream = TalkbackStream(session, "media.mp3", loop=loop)

    with patch("unifi_official_api.protect.talkback._transcode_and_stream") as mock_worker:
        await stream.start()
        assert stream._worker_future is not None
        assert stream._worker_future.get_loop() is loop
        assert stream._thread is not None
        assert stream._thread.daemon
        await stream.wait_until_complete()

    mock_worker.assert_called_once_with(session, "media.mp3", stream._stop_event)


@pytest.mark.asyncio
async def test_talkback_stream_executor_receives_worker_and_arguments() -> None:
    """The executor is called as executor(func, *args) and no thread is started."""
    session = _make_session()
    calls: list[tuple[Any, ...]] = []

    async def fake_executor(func: Any, *args: Any) -> None:
        calls.append((func, *args))

    stream = TalkbackStream(session, "media.mp3", executor=fake_executor)
    await stream.start()
    await stream.wait_until_complete()
    assert calls == [(_transcode_and_stream, session, "media.mp3", stream._stop_event)]
    assert stream._thread is None
