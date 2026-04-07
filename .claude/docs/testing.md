# Testing

This is a markdown-based plugin project — most "source code" is SKILL.md files validated via `bash scripts/validate.sh` and `bash scripts/test-hooks.sh`. The sections below cover the Python code under `scripts/` (`harness_common/`, `deep-mode-harness/`, `test-coverage-harness/`) and its pytest suites under `test/`.

For general testing principles (workflow, when to add tests, bug-fix-first-test discipline), follow the [testing.md template](../../skills/init/templates/docs/testing.md). For skill-file changes, see [skill-writing-guidelines.md](skill-writing-guidelines.md) instead.

## Test Runner

pytest via `python -m pytest`, plus `bash scripts/validate.sh` and `bash scripts/test-hooks.sh` for plugin manifest and hook validation.

## Running Tests

```bash
bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/harness-common/ test/deep-mode-harness/ test/test-coverage-harness/   # Full suite
python -m pytest test/test-coverage-harness/                                                                                                          # Single harness
python -m pytest test/test-coverage-harness/test_runner.py::test_name                                                                                 # Single test
test.cmd                                                                                                                                              # Windows convenience wrapper
```

## Test Structure

- `test/harness-common/` — tests for shared modules in `scripts/harness_common/`
- `test/deep-mode-harness/` — tests for `scripts/deep-mode-harness/impl/`
- `test/test-coverage-harness/` — tests for `scripts/test-coverage-harness/`
- Test files mirror the module they cover (`test_<module>.py`).

## Writing Tests

- Use plain pytest (no classes unless fixtures demand it); name tests `test_<behavior>`.
- Prefer `tmp_path` and real file I/O over mocking the filesystem — these harnesses are I/O-heavy and mocked paths have masked real bugs before.
- Keep fixtures local to the test module unless they are reused across harnesses.

## Coverage

```bash
test-coverage.cmd   # pytest --cov for all three harnesses, HTML report in htmlcov/
```

Equivalent direct invocation is documented in [.claude/CLAUDE.md](../CLAUDE.md) under "Commands".
