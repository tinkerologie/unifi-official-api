# Optional talkback workers

**Status:** Accepted; recorded retrospectively on 2026-11-07.

Protect talkback negotiates an audio destination separately from streaming
media. PyAV decoding, resampling, encoding, and output run in a worker rather
than on the asynchronous event loop. The `talkback` extra supplies PyAV, which
is imported when streaming is needed; consumers using other APIs do not need
to install it. Callers can supply an executor instead of the default dedicated
daemon thread.

This isolates a native media dependency and blocking work from ordinary API
requests while supporting hosts with their own worker facilities. Making PyAV
mandatory would impose media dependencies on every consumer; doing decoding
in the event loop would couple unrelated requests to media I/O.

## Consequences

- A negotiated session is validated before streaming, and missing PyAV produces
  a talkback-specific import error.
- Stop is cooperative between frames. A blocked input open or read finishes
  only when its configured I/O timeout expires; stop is not immediate worker
  termination.
- The accepted codecs, destination schemes, and audio parameters remain part
  of the talkback interface rather than a generic HTTP transport capability.

## Evidence

- [Optional dependencies](../../pyproject.toml).
- [Talkback implementation](../../src/unifi_official_api/protect/talkback.py).
- [Talkback tests](../../tests/test_api_protect_talkback.py).
