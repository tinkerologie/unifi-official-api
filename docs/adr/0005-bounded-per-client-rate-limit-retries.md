# Bounded per-client rate-limit retries

**Status:** Accepted; recorded retrospectively on 2026-11-07.

Rate-limited application clients pace their requests through a limiter in the
shared transport. Protect and Mobility declare their budgets; a short server
`Retry-After` permits one retry after HTTP 429, while a long or missing delay
raises `UniFiRateLimitError` instead of blocking a call for a minute. Protect
WebSocket handshakes consume the client's request budget as well.

Keeping this policy in transport covers endpoint calls consistently. Unlimited
retries would hide sustained quota contention and extend operation latency;
leaving all pacing to consumers would duplicate policy across every resource.
The retry is specifically for server-rejected rate-limited requests, not a
general retry of writes after uncertain connection failures.

## Consequences

- The current limiter is owned by one client instance. It does not coordinate
  multiple clients or processes using the same server-side quota.
- Only a bounded short delay is retried; callers still handle a rate-limit
  exception when the delay is unsuitable or the retry is rejected.
- HTTP-date and numeric retry headers are interpreted by one helper.
- Stream reconnection remains the stream interface's responsibility; sharing
  pacing does not make every WebSocket failure an HTTP retry.

## Evidence

- [Transport limiter and retry policy](../../src/unifi_official_api/base.py).
- [Application budgets](../../src/unifi_official_api/const.py).
- [Client plumbing tests](../../tests/test_api_client_plumbing.py),
  [base-client tests](../../tests/test_base_client.py), and
  [Protect handshake tests](../../tests/test_protect_websocket.py).
