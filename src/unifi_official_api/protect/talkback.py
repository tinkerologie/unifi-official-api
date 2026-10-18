"""Talkback audio transport for UniFi Protect cameras.

This module provides the audio streaming transport needed to stream audio to
UniFi Protect camera speakers using negotiated talkback sessions.

PyAV is used to decode the source media, resample audio to mono at the
session sampling rate and bit depth, encode it using the session codec, and mux
it into the destination stream (e.g. RTP over UDP).

Stop is cooperative:
    Between frames, the stream checks a threading.Event and uses Event.wait()
    for real-time pacing. A blocked input open or read call ends only when its
    I/O timeout expires.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
import urllib.parse
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Final

from ..exceptions import UniFiError

if TYPE_CHECKING:
    from .models.files import TalkbackSession

_LOGGER = logging.getLogger(__name__)

# URL schemes supported by the talkback transport
SUPPORTED_SCHEMES: Final[set[str]] = {"rtp", "udp"}

# Codec to (container_format, codec_name) mapping
CODEC_MAP: Final[dict[str, tuple[str, str]]] = {
    "aac": ("adts", "aac"),
    "opus": ("rtp", "libopus"),
    "vorbis": ("ogg", "vorbis"),
}

# Bit depth to sample format mapping
BIT_DEPTH_MAP: Final[dict[int, str]] = {
    8: "u8",
    16: "s16",
    32: "s32",
}

DEFAULT_SAMPLE_FORMAT: Final[str] = "s16"
DEFAULT_INPUT_TIMEOUT: Final[float] = 10.0


class TalkbackError(UniFiError):
    """Base exception for talkback errors."""


class TalkbackSchemeError(TalkbackError):
    """Raised when the talkback destination URL scheme is unsupported."""


class TalkbackCodecError(TalkbackError):
    """Raised when the talkback codec is unsupported."""


class TalkbackSamplingRateError(TalkbackError):
    """Raised when the talkback sampling rate is missing or non-positive."""


class TalkbackImportError(TalkbackError, ImportError):
    """Raised when PyAV cannot be imported."""


class TalkbackStreamError(TalkbackError):
    """Raised when streaming or transcoding fails."""


def validate_talkback_session(session: TalkbackSession) -> None:
    """Validate talkback session parameters prior to streaming."""
    if not session.url:
        raise TalkbackSchemeError("Talkback session URL is required")

    parsed = urllib.parse.urlsplit(session.url)
    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES:
        raise TalkbackSchemeError(f"Unsupported talkback URL scheme: '{parsed.scheme}'")

    if not session.codec:
        raise TalkbackCodecError("Talkback session codec is required")

    codec_key = session.codec.lower()
    if codec_key not in CODEC_MAP:
        raise TalkbackCodecError(f"Unsupported talkback codec: '{session.codec}'")

    if (
        isinstance(session.sampling_rate, bool)
        or not isinstance(session.sampling_rate, int)
        or session.sampling_rate <= 0
    ):
        raise TalkbackSamplingRateError(f"Invalid talkback sampling rate: {session.sampling_rate}")


def _sanitize_url(url: str) -> str:
    """Remove userinfo, query parameters, and fragments to prevent credential leakage."""
    try:
        parts = urllib.parse.urlsplit(url)
        netloc = parts.netloc.rsplit("@", 1)[-1]
        return parts._replace(netloc=netloc, query="", fragment="").geturl()
    except Exception:
        return "<invalid-url>"


def _close_quietly(container: Any) -> None:
    """Close a PyAV container if it was opened, ignoring close errors."""
    if container is None:
        return
    with contextlib.suppress(Exception):
        container.close()


def _transcode_and_stream(
    session: TalkbackSession,
    media_url: str,
    stop_event: threading.Event,
) -> None:
    """Worker function to transcode and stream audio in the executor."""
    try:
        import av  # type: ignore[import-not-found]  # noqa: PLC0415
        import av.audio.resampler  # type: ignore[import-not-found]  # noqa: PLC0415

    except ImportError as err:
        msg = (
            "PyAV is required for talkback audio streaming; "
            "install it with 'pip install unifi-official-api[talkback]'"
        )
        raise TalkbackImportError(msg) from err

    codec_key = session.codec.lower()
    out_format, codec_name = CODEC_MAP[codec_key]
    sample_fmt = BIT_DEPTH_MAP.get(session.bits_per_sample, DEFAULT_SAMPLE_FORMAT)

    input_container: Any = None
    output_container: Any = None

    try:
        try:
            input_container = av.open(
                media_url,
                mode="r",
                timeout=DEFAULT_INPUT_TIMEOUT,
            )
        except Exception as err:
            safe_source = _sanitize_url(media_url)
            raise TalkbackStreamError(f"Failed to open source media '{safe_source}'") from err

        if not input_container.streams.audio:
            raise TalkbackStreamError("No audio streams found in source media")

        input_audio = input_container.streams.audio[0]

        try:
            output_container = av.open(
                session.url,
                mode="w",
                format=out_format,
            )
        except Exception as err:
            safe_dest = _sanitize_url(session.url)
            raise TalkbackStreamError(f"Failed to open destination stream '{safe_dest}'") from err

        output_stream = output_container.add_stream(
            codec_name,
            rate=session.sampling_rate,
        )
        output_stream.layout = "mono"

        # PyAV AudioResampler
        resampler = av.audio.resampler.AudioResampler(
            format=output_stream.format or sample_fmt,
            layout="mono",
            rate=session.sampling_rate,
        )

        start_time = time.monotonic()
        played_duration = 0.0

        for frame in input_container.decode(input_audio):
            if stop_event.is_set():
                break

            for resampled_frame in resampler.resample(frame):
                if stop_event.is_set():
                    break

                frame_duration = resampled_frame.samples / session.sampling_rate
                target_time = start_time + played_duration
                delay = target_time - time.monotonic()

                if delay > 0 and stop_event.wait(delay):
                    break

                played_duration += frame_duration

                for packet in output_stream.encode(resampled_frame):
                    output_container.mux(packet)

        # Flush encoder only when not stopped early
        if not stop_event.is_set():
            for resampled_frame in resampler.resample(None):
                for packet in output_stream.encode(resampled_frame):
                    output_container.mux(packet)

            for packet in output_stream.encode(None):
                output_container.mux(packet)

    except TalkbackError:
        raise
    except Exception as err:
        msg = f"Error during talkback stream: {type(err).__name__}"
        raise TalkbackStreamError(msg) from err
    finally:
        _close_quietly(output_container)
        _close_quietly(input_container)


class TalkbackStream:
    """Talkback audio stream runner."""

    def __init__(
        self,
        session: TalkbackSession,
        media_source: str,
        _context: Any = None,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        executor: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        """Initialize the talkback stream."""
        self.session = session
        self.media_source = media_source
        self.media_url = media_source  # Compatibility alias
        self._context = _context
        self._loop = loop
        self._executor = executor
        self._stop_event = threading.Event()
        self._worker_future: asyncio.Future[None] | None = None
        self._thread: threading.Thread | None = None
        self._error: Exception | None = None
        self._started = False

    @property
    def running(self) -> bool:
        """Return True if the stream worker is currently running."""
        return self._worker_future is not None and not self._worker_future.done()

    async def start(self) -> None:
        """Validate session and start worker."""
        if self._started:
            return
        self._started = True

        validate_talkback_session(self.session)

        running_loop = self._loop or asyncio.get_running_loop()
        future: asyncio.Future[None] = running_loop.create_future()
        self._worker_future = future

        def _resolve(error: Exception | None = None) -> None:
            """Resolve the worker future on the event loop."""
            if future.done():
                return
            if error is not None:
                future.set_exception(error)
            else:
                future.set_result(None)

        if self._executor is not None:
            # Delegate execution to caller-provided executor
            async def _run_executor() -> None:
                try:
                    assert self._executor is not None
                    await self._executor(
                        _transcode_and_stream,
                        self.session,
                        self.media_source,
                        self._stop_event,
                    )
                except Exception as err:
                    self._error = err
                    _resolve(err)
                else:
                    _resolve()

            self._executor_task = asyncio.create_task(_run_executor())
        else:

            def _run() -> None:
                """Execute the transcoding and streaming loop in a background thread."""
                try:
                    _transcode_and_stream(
                        self.session,
                        self.media_source,
                        self._stop_event,
                    )
                except Exception as err:
                    self._error = err
                    _LOGGER.debug("Talkback stream worker encountered error: %s", err)
                    running_loop.call_soon_threadsafe(_resolve, err)
                else:
                    running_loop.call_soon_threadsafe(_resolve)

            self._thread = threading.Thread(
                target=_run,
                name=f"unifi_talkback_{self.session.codec}",
                daemon=True,
            )
            self._thread.start()

    async def stop(self) -> None:
        """Cooperatively stop the stream."""
        self._stop_event.set()
        future = self._worker_future
        if future is None or future.done():
            if future is not None and not future.cancelled():
                future.exception()
            return

        with contextlib.suppress(Exception):
            await asyncio.shield(future)

    async def wait_until_complete(self) -> None:
        """Wait until stream finishes and re-raise any worker error."""
        if self._worker_future is not None:
            try:
                await self._worker_future
            except Exception as err:
                raise (self._error or err) from err
        elif self._error is not None:
            raise self._error


__all__ = [
    "BIT_DEPTH_MAP",
    "CODEC_MAP",
    "DEFAULT_INPUT_TIMEOUT",
    "DEFAULT_SAMPLE_FORMAT",
    "SUPPORTED_SCHEMES",
    "TalkbackCodecError",
    "TalkbackError",
    "TalkbackImportError",
    "TalkbackSamplingRateError",
    "TalkbackSchemeError",
    "TalkbackStream",
    "TalkbackStreamError",
    "validate_talkback_session",
]
