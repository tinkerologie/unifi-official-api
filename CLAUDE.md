# Claude Code Instructions

This repository uses a shared AI instruction system.

Read `AGENTS.md` first. It is the source of truth for:

- architecture and layering expectations
- commands for validation
- endpoint/model patterns
- testing requirements
- documentation and workflow rules

## Quick Reference

- Package: `unifi_official_api`
- Main code: `src/unifi_official_api/`
- Tests: `tests/`
- Validate: `pytest`, `mypy src/ --strict`, `ruff check src/ tests/`

## Path-Specific Instructions

See `.github/instructions/*.instructions.md` for path-based guidance.

## Agent skills

### Issue tracker

Use this repository's GitHub Issues. Before ticket operations, read
`docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels. Before triaging, read
`docs/agents/triage-labels.md`.

### Domain docs

Use a single-context domain layout. Before exploring domain concepts or
architecture, read `docs/agents/domain.md`.
