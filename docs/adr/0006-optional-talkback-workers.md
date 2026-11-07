# Optional talkback workers

**Status:** Accepted. The record date is 2026-11-07.

Protect talkback gets an audio destination from the camera. A worker runs
the PyAV decode, resample, encode, and output operations. The event loop can
continue to process other requests. The `talkback` extra installs PyAV.
Talkback imports PyAV when it starts to send audio.

The caller can supply an executor. By default, talkback uses a dedicated
daemon thread. With an optional dependency, applications that use other
APIs can run without PyAV.

## Consequences

- The library makes sure that the talkback session is valid before it sends
  audio. If PyAV is missing, it raises an import error for talkback.
- The worker can stop between frames. If the worker waits for input, it can
  wait until the configured input or output timeout expires.
- The talkback interface specifies the codecs, destination schemes, and
  audio parameters.

## Evidence

- [Optional dependencies](../../pyproject.toml).
- [Talkback implementation](../../src/unifi_official_api/protect/talkback.py).
- [Talkback tests](../../tests/test_api_protect_talkback.py).
