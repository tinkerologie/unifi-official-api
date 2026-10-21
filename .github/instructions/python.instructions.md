---
applyTo: "src/**/*.py, tests/**/*.py"
---

# Python Instructions

**Applies to:** all Python source and test files.

## Language and Style

- Target Python 3.14+ (`requires-python` in `pyproject.toml`).
- Do not add `from __future__ import annotations`: Python 3.14 evaluates annotations lazily, and the pyupgrade pre-commit hook (`--py314-plus`) removes the import.
- Keep full type hints on public and internal functions unless intentionally private/simple.
- Follow Ruff and MyPy strictness expectations in `pyproject.toml`.

## Imports

- Group imports as stdlib, third-party, local.
- Prefer absolute imports from `unifi_official_api` root for package modules.
- Use `TYPE_CHECKING` imports where needed to avoid cycles.

## Async Rules

- All network I/O must stay async (`aiohttp`).
- Never use blocking network calls or `time.sleep()` in async paths.
- Use timeout-aware patterns for external calls.

## Error Handling

- Catch narrow exception types.
- Re-raise with context (`raise ... from err`) when translating.
- Do not use bare `except Exception` unless re-raising and explicitly justified.

## Model Usage

- Keep API response normalization close to endpoint/model boundaries.
- Prefer typed models over loose dictionaries for returned entities.
- Avoid silently discarding fields needed for forward compatibility.

## Validation Before Completion

Run:

```bash
mypy src/ --strict
ruff check src/ tests/
```

Use `ruff format src/ tests/` when formatting changes are required.
