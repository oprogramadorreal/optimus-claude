# Quality Gate

Runs after all TDD cycles complete. Reviewing here — not per-cycle — catches cross-cycle issues (duplication between behaviors, naming drift, accumulated pattern violations, edge-case coverage gaps) that are invisible within a single cycle.

## Gather changed files

Collect all files changed during the session: `git diff --name-only <original-branch>...HEAD` (the caller provides `<original-branch>`). This is the scope for both agents.

## Launch parallel agents

The code-simplifier agent always runs. The test-guardian agent runs when test infrastructure is detected (`.claude/docs/testing.md` or subproject `docs/testing.md` exists). Launch every applicable agent as a `general-purpose` Agent tool call in a **single** message so they run in parallel — do not skip an applicable agent to save tokens or time.

When composing each prompt below, replace `[changed files]` with the file list and `[plugin root]` with the resolved absolute plugin root — subagents inherit neither `$CLAUDE_PLUGIN_ROOT` nor this directory as cwd, so every path they receive must be absolute or project-relative.

### Constraints (append to both prompts)

```
Constraints:
- Read-only analysis: do NOT modify or create any files.
- Read the "Agent Constraints", "Quality Bar", "All Agents Exclude", and
  "False Positives to Avoid" sections of
  [plugin root]/references/shared-agent-constraints.md and apply them. That
  file's "Finding Cap" and "Structural-Neighbor Scope Expansion" sections do
  NOT apply to this gate — the two limits below replace them.
- Maximum 5 findings. Scope to the listed changed files only; do not suggest
  changes outside them.
- Do NOT flag style/formatting, bugs, or security — out of scope for this gate.
- High or Medium confidence only. Findings are independently validated, so
  omit speculation.
- Report each finding as: File (path:line), Category, Confidence (High|Medium),
  Issue, Suggested fix (max 5 lines).
```

### code-simplifier prompt

```
You are a code simplification specialist reviewing code produced by incremental
TDD cycles. Read .claude/docs/coding-guidelines.md and .claude/CLAUDE.md for
project standards.

Review ALL of these files for cross-cycle simplification opportunities:
[changed files]

The code was written one behavior at a time. Look for what emerges only across
cycles:
- Duplication across behaviors (similar handlers that should share logic)
- Naming inconsistencies between code written in different cycles
- Dead code introduced early then superseded by later cycles
- Pattern violations that accumulated gradually
- Abstractions worth extracting now that the full feature shape is visible

Category for findings: Code Quality. Cite the project guideline each finding
addresses.
```

### test-guardian prompt

```
You are a test coverage specialist reviewing a TDD-built test suite for blind
spots. Read .claude/CLAUDE.md for project structure, then the relevant
testing.md.

Analyze ALL of these files for coverage gaps:
[changed files]

Every behavior here already has a test. Focus on what one-behavior-at-a-time
TDD misses:
- Edge cases and boundary conditions beyond the happy-path-first tests
- Error propagation paths that cross multiple behaviors
- Test-to-source mapping for all new/modified source files
- Structural barriers to unit testing (tight coupling, hidden dependencies)

You MAY run the project's existing test command to confirm the suite passes.
Do NOT write test code — only identify gaps. Categories: Test Gap | Structural
Barrier. Include a recommended test file path where applicable.
```

## Present findings

```
## Quality Gate

### Code Simplifier
[Findings, or "No issues found — code follows project guidelines."]

### Test Guardian
[Findings, or "All code has test coverage. No structural barriers detected."
Omit this section if the agent was not launched.]
```

If neither agent produced findings, report "Quality gate passed — no issues found" and return to the caller.

## Act on findings

Apply fixes for each finding, then run the test suite:

- **All tests pass** — stage and commit with a conventional message (e.g., `refactor(scope): address quality gate findings`).
- **Tests fail** — revert all fixes, then re-apply one at a time with a test run after each: keep fixes that pass, revert those that fail. Summarize which were kept and which reverted ("fix broke tests"), then stage and commit the kept fixes.
