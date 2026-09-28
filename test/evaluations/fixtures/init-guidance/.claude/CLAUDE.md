# Invoice ledger

Standard-library Python library for invoice lookup and partner imports.

## Commands

From the repository root: `python -m unittest discover -s tests`.

## Project constraints

- Never recycle an archived invoice ID. Our reconciliation partner retains it for seven years; this agreement is not encoded in the in-memory lookup implementation.
- Catalog IDs are exact, case-sensitive keys, including whitespace. Importer-specific feed padding rules belong in `importer/CLAUDE.md`.

## Documentation

| Changing | Read |
|---|---|
| Data ownership or module boundaries | `.claude/docs/architecture.md` |
| Tests | `.claude/docs/testing.md` |
