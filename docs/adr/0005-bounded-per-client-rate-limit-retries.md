# Bounded per-client rate-limit retries

**Status:** Accepted. The per-client ownership rule is superseded by
[ADR 0007](0007-explicit-shared-request-budgets.md).

Protect and Mobility set the number of requests that their clients can start
in a period. The shared transport applies these limits. When the server
returns HTTP 429, a short `Retry-After` delay permits one retry. A long or
missing delay causes a `UniFiRateLimitError`. Protect WebSocket handshakes use
the same request budget.

The transport uses one policy for the endpoint calls. Unlimited retries
would make calls take longer and hide rate-limit errors. Without a shared
policy, each resource would need its own rules. The retry applies to a
request that the server rejects with HTTP 429.

## Consequences

- In this decision, each client owns its budget. That budget cannot control
  requests from other clients or processes.
- The caller must handle a rate-limit exception if the delay is too long or
  the retry fails.
- One function reads numeric and HTTP-date retry headers.
- The WebSocket interface controls reconnection. Request limits also apply
  to the Protect handshake.

## Evidence

- [Transport limiter and retry policy](../../src/unifi_official_api/base.py).
- [Application budgets](../../src/unifi_official_api/const.py).
- [Client plumbing tests](../../tests/test_api_client_plumbing.py),
  [base-client tests](../../tests/test_base_client.py), and
  [Protect handshake tests](../../tests/test_protect_websocket.py).
