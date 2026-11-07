# Explicit shared request budgets

**Status:** Accepted on 2026-11-07.

A server quota can apply to more than one client. Protect and Mobility
clients can use a request budget that the caller supplies. The budget controls
when these clients can start requests. It also shares short delays after
HTTP 429 responses. By default, each client uses its own budget. This option
supersedes the ownership rule in
[ADR 0005](0005-bounded-per-client-rate-limit-retries.md).

Each budget applies to one application, connection mode, origin, and route
prefix. For remote Protect, it also applies to one console ID. The caller
groups clients with the same credential scope. One budget operates in one
event loop in one process. The transport uses the same rules for
session ownership and retries.
