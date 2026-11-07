# Explicit shared request budgets

**Status:** Accepted on 2026-11-07.

A server quota can cover several clients using the same credential scope.
Protect and Mobility accept a caller-owned request budget so those clients
coordinate request starts and short cooldowns. The client still creates an
independent budget by default. The shared option supersedes the ownership rule
in [ADR 0005](0005-bounded-per-client-rate-limit-retries.md).

The budget binds to one application and origin, with connection mode and
remote Protect console identity where applicable. The caller groups clients
that use the same credential scope. Explicit injection keeps ownership local
to the application and avoids a process-wide credential registry. Requests
share pacing and cooldowns on one event loop. Session ownership and bounded
retry behavior follow the existing transport policy.
