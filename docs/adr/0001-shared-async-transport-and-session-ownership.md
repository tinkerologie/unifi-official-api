# Shared async transport and explicit session ownership

**Status:** Accepted; recorded retrospectively on 2026-11-07.

Application clients share `BaseUniFiClient` for asynchronous HTTP requests,
timeouts, response handling, and connection lifecycle. Callers can inject an
`aiohttp.ClientSession`; the client closes sessions it creates and leaves
caller-owned sessions open when it closes.

This gives standalone consumers a usable client while allowing frameworks to
share their existing connection pools. Creating a session in each endpoint
would scatter resource ownership; always creating one in the client would
prevent a caller from controlling that resource. The ownership distinction is
therefore part of the client interface, rather than endpoint-specific cleanup.

## Consequences

- Consumers must close clients that create their own sessions, normally through
  the asynchronous context manager.
- Reusing a caller session does not transfer ownership. If the supplied session
  is already closed when a request starts, the client creates and owns its
  replacement.
- Request-specific TLS behavior must account for an injected session's existing
  connector; application clients provide overrides where needed.

## Evidence

- [Transport and lifecycle](../../src/unifi_official_api/base.py):
  `_ensure_session`, `_owns_session`, `close`, and context-manager methods.
- [Client plumbing tests](../../tests/test_api_client_plumbing.py) and
  [base-client tests](../../tests/test_base_client.py).
