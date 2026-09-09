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
- `test/harness-common/test_checkpoint_safety.py` — composed real-Git recovery/validation/checkpoint tests, including failed index operations, unreported edits, stale green results, and preservation of staged/unstaged user work. Keep these composed checks when changing the corresponding mocked unit scaffolds.
- `test/test_init_hook_regressions.py`, `test/test_install_cmd.py`, and `test/test_skill_git_commands.py` — isolated formatter/installer command dispatch and real-Git skill snippets. Recorder stubs establish argv/cwd behavior, not actual formatter quality or model adherence.
- `scripts/test-skills.sh` and `scripts/test-codex-plugin.py` — respectively authenticated Claude execution smoke checks and an isolated Codex installation/discovery probe. Both identify the checkout; loader checks are not semantic execution. Controlled instruction comparisons are described in [the evaluation plan](../../docs/evaluation-plan.md).
- `test/test_format_python_hook.py` — tests for the repo's `.claude/hooks/format-python.sh` PostToolUse hook. This module shells out to `bash`, so it needs Git Bash on Windows; it resolves the interpreter through `harness_common.runner._find_bash` rather than a bare `bash`, because a WSL `bash` earlier on PATH cannot open Windows-style paths. Most cases plant stub formatters and need nothing installed — only the few that exercise real formatting need `black`/`isort` in the repo's `.venv` or on PATH, and they skip when absent.
- `test/test_session_start_launcher.py` — exercises the separate Claude and Codex hook commands against the shared session-start script. Claude's direct Bash path must preserve output and work without Git or with a corrupt Git config. Codex's Windows wrapper is checked under `cmd.exe`, PowerShell 5.1, and PowerShell 7, including native Windows paths, spaces, restricted PATH, and WSL interference. Fixtures also cover preserving the invoking directory outside a repo, at its root, and in a nested directory. The hook configs must select the intended launcher for each host and the manifests must keep matching names and versions. These test command execution, not the host's plugin loader; use a fresh native session with the exact plugin to verify the actual integration and that Codex runs only its explicitly selected hook.
- `test/test_skill_metadata.py` — parses shipped skill metadata and rejects malformed YAML, missing restrictions, string-valued booleans, and a Codex flag under the wrong parent. `scripts/validate.sh` runs the same validator; Python with `requirements-dev.txt` installed is required. PyYAML is a development dependency only; the runtime harness remains stdlib-only.
- `test/test_skill_smoke_runner.py` — local host stubs and real Git fixtures verify checkout selection, failed/empty results, read-only file preservation, actual branch creation, and isolation of consecutive worktree runs. These are runner tests, not model-performance results. The separate `scripts/skill_test_support.py` smoke oracle uses development PyYAML.
- `test/test_install_cmd.py` — invokes the Windows installer with local Python-module stubs to check paths with spaces and failure propagation without creating a real environment or installing packages.
- `scripts/test-codex-plugin.py` — optional local host loader check in a temporary Codex home: marketplace installation, skill discovery, and cached/source prompt comparison. It invokes no model and does not replace the semantic checks in CONTRIBUTING.md.
- The Codex SessionStart regression in `test/test_session_start_launcher.py` ensures plain context does not look like JSON to the host. An exit code of zero alone misses this failure: Codex can reject the stdout and discard every compatibility instruction.
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
