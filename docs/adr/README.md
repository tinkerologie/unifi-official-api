# Architecture decisions

These records give the design decisions for the library. Records 0001
through 0006 cover decisions before the record date. Their sources are the code, tests, and changelog on 2026-11-07.
Record 0007 gives the rules for a shared request budget.

See the [glossary](../../GLOSSARY.md) for project terms.

| ADR | Decision |
| --- | --- |
| [0001](0001-shared-async-transport-and-session-ownership.md) | Shared async transport and explicit session ownership |
| [0002](0002-application-scoped-routing-and-authentication.md) | Application-scoped routing and authentication |
| [0003](0003-forward-compatible-typed-resource-models.md) | Forward-compatible typed resource models |
| [0004](0004-operation-specific-response-validation.md) | Operation-specific response validation |
| [0005](0005-bounded-per-client-rate-limit-retries.md) | Bounded rate-limit retries (ownership superseded by ADR 0007) |
| [0006](0006-optional-talkback-workers.md) | Optional talkback workers |
| [0007](0007-explicit-shared-request-budgets.md) | Explicit shared request budgets |

Use a new issue to change an existing contract. Add a new record that
supersedes the previous record.
