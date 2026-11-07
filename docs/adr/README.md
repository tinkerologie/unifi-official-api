# Architecture decisions

These records describe material decisions already embodied in the library.
They were recorded retrospectively on 2026-11-07 from source, tests, and the
changelog. Their trade-offs describe observable consequences rather than
claiming to recover an undocumented historical discussion.

See the [domain glossary](../../GLOSSARY.md) for resource terminology.

| ADR | Decision |
| --- | --- |
| [0001](0001-shared-async-transport-and-session-ownership.md) | Shared async transport and explicit session ownership |
| [0002](0002-application-scoped-routing-and-authentication.md) | Application-scoped routing and authentication |
| [0003](0003-forward-compatible-typed-resource-models.md) | Forward-compatible typed resource models |
| [0004](0004-operation-specific-response-validation.md) | Operation-specific response validation |
| [0005](0005-bounded-per-client-rate-limit-retries.md) | Bounded rate-limit retries (ownership superseded by ADR 0007) |
| [0006](0006-optional-talkback-workers.md) | Optional talkback workers |
| [0007](0007-explicit-shared-request-budgets.md) | Explicit shared request budgets |

Each record documents the current choice and its limitations. Change an
established contract through a separate issue and a superseding record, rather
than turning these retrospective records into proposals for new behavior.
