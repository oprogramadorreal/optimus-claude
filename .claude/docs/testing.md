# Testing

This is a markdown-based plugin project — most "source code" is SKILL.md files validated via `bash scripts/validate.sh` and `bash scripts/test-hooks.sh`. The sections below cover the Python code under `scripts/harness_common/` (the orchestrator CLI plus its shared modules) and its pytest suite under `test/harness-common/`.

For general testing principles, see [skills/tdd/SKILL.md](../../skills/tdd/SKILL.md) for test-first / bug-reproduce-first discipline, and [skills/tdd/references/testing-anti-patterns.md](../../skills/tdd/references/testing-anti-patterns.md) for mocking discipline (especially relevant here — the CLI is I/O-heavy and over-mocking has masked real bugs before). For skill-file changes, see [skill-writing-guidelines.md](skill-writing-guidelines.md) instead.

## Test Runner

pytest via `python -m pytest`, plus `bash scripts/validate.sh` and `bash scripts/test-hooks.sh` for plugin manifest and hook validation.

## Running Tests

```bash
bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/   # Full suite
python -m pytest test/harness-common/test_cli.py                                                   # Single module
python -m pytest test/harness-common/test_cli.py::TestInit::test_deep_code_review                  # Single test
test.cmd                                                                                            # Windows convenience wrapper
```

## Test Structure

- `test/harness-common/` — tests for the orchestrator CLI (`scripts/harness_common/cli.py`) and its shared modules.
- `test/test_format_python_hook.py` — tests for the repo's `.claude/hooks/format-python.sh` PostToolUse hook. This module shells out to `bash`, so it needs Git Bash on Windows; it resolves the interpreter through `harness_common.runner._find_bash` rather than a bare `bash`, because a WSL `bash` earlier on PATH cannot open Windows-style paths. Most cases plant stub formatters and need nothing installed — only the few that exercise real formatting need `black`/`isort` in the repo's `.venv` or on PATH, and they skip when absent.
- `test/test_session_start_launcher.py` — compares the Windows `cmd.exe` fallback's complete hook output with a direct Bash launch outside a repo, at its root, and in a nested directory containing spaces. Tests both the restricted system PATH (`Git\cmd` and `System32`) and a stub Bash that fails with UTF-16 stdout diagnostics like WSL; startup diagnostics are separate from hook output. Also checks the Claude Bash command's exact stdout on both platforms with an inherited `GIT_PREFIX`. These test command execution, not the host's plugin loader; use `claude --plugin-dir <plugin> --debug-file <log> -p ...` to verify the actual Claude integration.
- `test/test_skill_metadata.py` — parses shipped skill metadata and rejects malformed YAML, missing restrictions, string-valued booleans, and a Codex flag under the wrong parent. `scripts/validate.sh` runs the same validator; Python with `requirements-dev.txt` installed is required. PyYAML is a development dependency only; the runtime harness remains stdlib-only.
- Test files mirror the module they cover (`test_<module>.py`).

## Writing Tests

- Use plain pytest. Grouping related tests under `Test*` classes for navigation is fine when a module has many tests — a class-scoped fixture is not required to justify it (the harness suites, e.g. `test_cli.py`, group this way; `test_skill_contract.py` uses plain functions — both are acceptable). Name tests `test_<behavior>`.
- Prefer `tmp_path` and real file I/O over mocking the filesystem — the CLI is I/O-heavy and mocked paths have masked real bugs before.
- Keep fixtures local to the test module unless they are reused across modules; shared fixtures live in `test/harness-common/conftest.py`.

## Coverage

```bash
test-coverage.cmd                                                                  # HTML report in htmlcov/
python -m pytest test/harness-common/ --cov scripts/harness_common --cov-report=term-missing   # direct
```

First-time setup: on Windows, `install.cmd` creates `.venv` and installs the dev dependencies. There is no `install.sh` — on macOS/Linux run `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`. Either way `bash` must be on PATH for the hook tests (already there on macOS/Linux; Git Bash on Windows).
