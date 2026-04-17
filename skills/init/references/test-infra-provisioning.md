# Test Infrastructure Provisioning

This reference covers the complete test infrastructure setup: framework and coverage tooling installation, health check, and Optimus documentation provisioning. Read by init's test infrastructure step.

## Framework and Coverage Tooling Installation

### Subprojects without a test framework

Analyze the tech stack and recommend the most popular framework with appropriate coverage tooling. Consult `$CLAUDE_PLUGIN_ROOT/skills/init/references/test-framework-recommendations.md` for stack-specific recommendations. For unsupported stacks, read `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md` and apply its command validation and approval rules. These are starting points — analyze the actual project to decide. Ask for **explicit user approval** before installing anything.

If installation fails (network issues, version conflicts, incompatible environments), report the error to the user and stop — do not proceed without a working framework.

### Subprojects with framework but without coverage tooling

Detect this gap separately and recommend installing coverage tooling. Coverage measurement is essential for reporting meaningful results and setting achievable targets. Ask for explicit user approval.

### Coverage report tooling

If the installed coverage tool only generates machine-readable output (XML, JSON) without a built-in human-readable report, install a report generator alongside it. Consult the "Report Tool" column in `$CLAUDE_PLUGIN_ROOT/skills/init/references/test-framework-recommendations.md`. Ask for explicit user approval. Include the report command in `testing.md` and `CLAUDE.md` coverage sections.

## Test Infrastructure Health Check

After framework exists (pre-existing or just installed), run the test suite once to verify it works. Distinguish between failure types:

- **Build/bootstrap failure** (test runner cannot start, or test files fail to compile — broken imports, missing polyfills, deprecated paths in setup files like `src/test.ts`, `jest.config.*`, `conftest.py`, or compilation errors in `.spec`/`.test` files due to renamed/removed APIs) — these are build-level issues, not test logic. Report the specific errors, ask the user for approval to fix them, and re-run. Apply minimal changes: update import paths, fix type references, adjust mocks to match current signatures. If the fix requires more than build-level corrections, stop and report.
- **Test assertion failures** (tests compile and run, but some fail) — report but continue. These are logic bugs, not infrastructure issues. Record the outcome as `{ subproject, framework, failing_count, failing_names[]? }` (one record per subproject) and carry it into Step 7's summary so the broken baseline is visible there, not only mentioned during provisioning.
- **All pass** — proceed normally.

## Optimus Infrastructure Provisioning

This phase runs **regardless** of whether the steps above installed anything — test infrastructure may have been added manually. Provision what is missing:

### Testing documentation

If `.claude/docs/testing.md` doesn't exist, create it using `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/testing.md` as the skeleton. Fill in all placeholders with actual project details (framework name, test commands, directory structure, conventions from existing test files). Don't leave any `[placeholder]` text.

If `.claude/docs/testing.md` already exists, review it for accuracy. Propose updates if outdated — especially if a new framework was just installed. Ask user approval before modifying.

### CLAUDE.md testing references

If `.claude/CLAUDE.md` doesn't reference testing, add test commands and a testing.md reference. Keep within init's compact ~60-line style — add to existing sections rather than creating new ones.

### Monorepo subprojects

For monorepos, update subproject-level `CLAUDE.md` files too. Each subproject should reference its own `docs/testing.md` and test commands.

### README testing section

If `README.md` exists at the project root and doesn't already have a testing section (scan for headings containing "test", case-insensitive), append a concise section with: test command, coverage command (if configured), and test project/directory location. Match the README's existing heading level, language, and formatting style. Use `.claude/docs/testing.md` as the source of truth for commands and paths — do not duplicate its full content. Keep the section to 5-10 lines.

For monorepos, update each subproject's `README.md` too if it exists and lacks a testing section.

### Gitignore test artifacts

If `.gitignore` exists and doesn't already ignore the test output directory (e.g., `TestResults/` for .NET, `htmlcov/` for Python, `coverage/` for Node.js), append the appropriate entry. One line, matching the file's existing style.
