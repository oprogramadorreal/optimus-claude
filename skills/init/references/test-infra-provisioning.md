# Test Infrastructure Provisioning

Complete test infrastructure setup: framework and coverage tooling installation, health check, and Optimus documentation provisioning. Read by init's test infrastructure step.

## Framework and Coverage Tooling Installation

### Framework selection

Recommend the stack's dominant framework — these pins override general knowledge; analyze the actual project to decide:

- Prefer whatever framework the project or its peer projects already use; keep an existing Jest setup unless migration is explicitly requested.
- Node.js/TypeScript with Vite, ESBuild, or SWC → Vitest (built-in v8 coverage); otherwise Jest (`--coverage`). New Angular projects → Vitest; existing Angular tests → keep what's there.
- Go and Rust → built-in test tooling (no third-party framework). Rust coverage: cargo-tarpaulin (`--out Html`) or cargo-llvm-cov (`--html`).
- C#/.NET → xUnit + coverlet; coverlet emits machine-readable output only, so also install `dotnet-reportgenerator-globaltool` for readable reports.
- Flutter → flutter_test (`flutter test --coverage`, LCOV); pure Dart → package:test. Filter generated files (`*.g.dart`, `*.freezed.dart`) from coverage reports; integration tests go in `integration_test/`.
- Python → pytest + pytest-cov; Java → JUnit 5 + JaCoCo; C/C++ → Google Test or Catch2 + gcov/lcov (report via `genhtml`).
- Unknown stack → search the web for the most popular framework and coverage tooling, applying the command validation and approval rules from `$CLAUDE_PLUGIN_ROOT/skills/init/references/unsupported-stack-fallback.md`.

Ask for **explicit user approval** before installing anything. If installation fails (network issues, version conflicts, incompatible environments), report the error and stop — do not proceed without a working framework.

### Coverage tooling gaps

If a framework exists but coverage tooling is missing, recommend installing it (approval required) — coverage measurement is essential for meaningful results and achievable targets. If the coverage tool only produces machine-readable output (XML, JSON), also install a report generator (see the pins above) and include the report command in `testing.md` and CLAUDE.md.

## Test Infrastructure Health Check

After a framework exists (pre-existing or just installed), run the test suite once. Distinguish failure types:

- **Build/bootstrap failure** (runner cannot start, or test files fail to compile — broken imports, missing polyfills, deprecated paths in setup files like `src/test.ts`, `jest.config.*`, `conftest.py`, or compilation errors in `.spec`/`.test` files from renamed/removed APIs): build-level issues, not test logic. Report the specific errors, ask user approval to fix, and re-run. Apply minimal changes only (import paths, type references, mock signatures). If the fix needs more than build-level corrections, stop and report.
- **Test assertion failures** (tests compile and run, some fail): report but continue — these are logic bugs, not infrastructure. Record `{ scope, failing_count }` where `scope` is `project`, `subproject`, or `repo`, and carry it into Step 7's summary (consumed by the broken-baseline modifier).
- **All pass** → proceed normally.

## Optimus Infrastructure Provisioning

This phase runs **regardless** of whether anything was installed above — test infrastructure may have been added manually. Provision what is missing:

### Testing documentation

**Placement:** single project — `.claude/docs/testing.md`. Monorepo — `<subproject>/docs/testing.md` per subproject with test infrastructure, scoped to that subproject's framework and commands; root `.claude/docs/testing.md` only for root-as-project.

If testing.md doesn't exist, create it from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/testing.md`, filling every placeholder with actual project details (framework, commands, directory structure, conventions from existing test files). If it exists, review for accuracy and propose updates — especially after installing a new framework — with user approval (Customizable semantics).

### CLAUDE.md testing references

If `.claude/CLAUDE.md` doesn't reference testing, add test commands and a testing.md reference — extend existing sections, keep the compact ~60-line style. Monorepos without root-as-project: add workspace-wide test commands only (no root testing.md reference); each subproject's CLAUDE.md references its own `docs/testing.md` and commands.

### README testing section

If `README.md` exists at the project root and has no testing heading (scan for headings containing "test", case-insensitive), append a concise 5-10-line section: test command, coverage command (if configured), test directory location. Match the README's heading level and style; source commands from testing.md, don't duplicate its content. Monorepos: same for each subproject README that exists and lacks one.

### Gitignore test artifacts

If `.gitignore` exists and doesn't ignore the test output directory (e.g., `TestResults/`, `htmlcov/`, `coverage/`), append the appropriate entry — one line, matching the file's style.
