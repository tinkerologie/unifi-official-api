# Shared async transport and explicit session ownership

**Status:** Accepted. The record date is 2026-11-07.

All application clients use `BaseUniFiClient` for HTTP requests. It also
controls timeouts, processes responses, and manages the HTTP session. The
caller can supply an `aiohttp.ClientSession`. A client closes the sessions
that it creates. The caller closes a session that it supplies.

A framework can use its existing connection pool. A client can also run on
its own. A session in each endpoint divides session ownership among endpoints.
A client that always creates a session cannot use the caller's connection pool.

## Consequences

- Close clients that create their own sessions. You can use the asynchronous
  context manager to close a client.
- If the caller's session is closed when a request starts, the client creates
  a replacement. The client owns the replacement.
- The client must use Transport Layer Security (TLS) settings that agree with
  the session connector. Some application clients can set TLS options for
  each request.

## Evidence

- [Transport and lifecycle](../../src/unifi_official_api/base.py):
  `_ensure_session`, `_owns_session`, `close`, and context-manager methods.
- [Client plumbing tests](../../tests/test_api_client_plumbing.py) and
  [base-client tests](../../tests/test_base_client.py).
