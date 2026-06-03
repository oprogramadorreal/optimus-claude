# Testing

This is a markdown-based plugin project — most "source code" is SKILL.md files validated via `bash scripts/validate.sh` and `bash scripts/test-hooks.sh`. The sections below cover the Python code under `scripts/harness_common/` (the orchestrator CLI plus its shared modules) and its pytest suite under `test/harness-common/`.

For general testing principles, see [skills/tdd/SKILL.md](../../skills/tdd/SKILL.md) for test-first / bug-reproduce-first discipline, and [skills/tdd/references/testing-anti-patterns.md](../../skills/tdd/references/testing-anti-patterns.md) for mocking discipline (especially relevant here — the CLI is I/O-heavy and over-mocking has masked real bugs before). For skill-file changes, see [skill-writing-guidelines.md](skill-writing-guidelines.md) instead.

## Test Runner

pytest via `python -m pytest`, plus `bash scripts/validate.sh` and `bash scripts/test-hooks.sh` for plugin manifest and hook validation.

## Running Tests

```bash
bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/harness-common/   # Full suite
python -m pytest test/harness-common/test_cli.py                                                   # Single module
python -m pytest test/harness-common/test_cli.py::TestInit::test_deep_code_review                  # Single test
test.cmd                                                                                            # Windows convenience wrapper
```

## Test Structure

- `test/harness-common/` — tests for the orchestrator CLI (`scripts/harness_common/cli.py`) and its shared modules.
- Test files mirror the module they cover (`test_<module>.py`).

## Writing Tests

- Use plain pytest. Grouping related tests under `Test*` classes for navigation is fine when a module has many tests — a class-scoped fixture is not required to justify it (the harness suites, e.g. `test_cli.py`, group this way; `test_skill_contract.py` uses plain functions — both are acceptable). Name tests `test_<behavior>`.
- Prefer `tmp_path` and real file I/O over mocking the filesystem — the CLI is I/O-heavy and mocked paths have masked real bugs before.
- Keep fixtures local to the test module unless they are reused across modules; shared fixtures live in `test/harness-common/conftest.py`.

## Coverage

```bash
test-coverage.cmd   # pytest --cov for harness_common, HTML report in htmlcov/
```

Equivalent direct invocation is documented in [.claude/CLAUDE.md](../CLAUDE.md) under "Commands".
