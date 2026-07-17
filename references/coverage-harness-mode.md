# Coverage Harness Mode

Single-pass protocol for `/optimus:unit-test` when invoked under the `/optimus:deep coverage` orchestrator. The orchestrator alternates unit-test and refactor phases per cycle, but each phase runs in its own fresh subagent context as a single pass.

## Contents

1. [Unit-Test Phase Execution](#unit-test-phase-execution) — single pass under orchestrator control (steps 1–6)
2. [Refactor Phase Execution](#refactor-phase-execution) — single pass under orchestrator control (delegates to `harness-mode.md`)

## Unit-Test Phase Execution

When the `/optimus:deep coverage` orchestrator dispatches `/optimus:unit-test` as a subagent for the unit-test phase, the base skill detects `HARNESS_MODE_INLINE` in its invocation prompt and the orchestrator's prompt body includes `Phase: unit-test`. Execute exactly **one pass** of the unit-test workflow, then output structured JSON and exit.

### 1. Read progress file

Read the JSON progress file at the path specified in your invocation prompt. Extract:
- `cycle.current` — which cycle this is
- `coverage` — prior coverage data (baseline, current, history)
- `tests_created` — tests written in prior cycles
- `untestable_code` — items flagged as untestable in prior cycles
- `config.test_command` — the test command (for reference only — do NOT run it)
- `config.scope` — path filter (apply to discovery); `null` means the full project. The CLI populates it only when the user's scope resolved to a real path, so it is never free text — do not treat `config.scope_text` (recorded intent) as a filter.

### 2. Run discovery and coverage analysis

Run the same Test Infrastructure Analyzer agent as normal mode (Step 2 of SKILL.md).

**Cycle context block (cycles 2+):** when `cycle.current` is greater than 1, prepend a concise context block to the agent prompt before the main instructions. Source the data from the progress file's `tests_created`, `untestable_code`, and `coverage.history`. Include:

- **Tests already added** — `file → target` entries from `tests_created` with status `pass`, so the agent skips those targets.
- **Items previously reverted, abandoned, or bug-found** — entries from `tests_created` with status `fail-abandoned` or similar, so the agent does not re-propose them.
- **Untestable code already flagged** — entries from `untestable_code`, so the agent does not re-flag them.
- **Cumulative coverage delta** — one line derived from `coverage.history`.

The goal is convergence: each cycle proposes **new** testable items, not duplicates. Keep the block under ~30 lines.

**Stop gates under harness mode:** if a SKILL.md Step 2 stop gate fires (no test framework detected, or the baseline suite fails), do not print the conversational handoff messages — skip sections 3–4 and emit the section 5 JSON immediately with `no_new_tests: true`, empty `tests_written` and `untestable_code` arrays (list any failing tests found under `bugs_discovered`), and a non-null `blocked` field naming the gate and why. The orchestrator terminates the loop on a non-null `blocked` and surfaces the reason to the user.

### 3. Generate and write tests

Run Steps 3–4 of SKILL.md (plan + write) with these harness modifications:
- **Skip `AskUserQuestion`** — auto-approve all planned items
- **Cap at 10 items** per pass (same as normal mode)
- **Do NOT run the full test suite as a final verification gate**, nor any `scripts/*.sh` test/lint/build wrapper — the orchestrator owns the full run and bisection. Coverage measurement is fine, including one coverage-instrumented run after tests are written to obtain `coverage.after` — but its pass/fail outcome must not trigger reverts or fixes beyond the per-test workflow

### 4. Collect results

Gather: tests written (file, target, count, status), coverage change, untestable code items, bugs discovered.

### 5. Output structured JSON

Output the results in a `json:harness-output` fenced block:

````
```json:harness-output
{
  "cycle": <cycle number from progress file>,
  "phase": "unit-test",
  "coverage": {
    "tool": "<coverage tool name or null>",
    "before": <percentage or null>,
    "after": <percentage or null>,
    "delta": <percentage or null>
  },
  "tests_written": [
    {
      "file": "<test file path>",
      "target_file": "<source file being tested>",
      "target_description": "<what it tests>",
      "test_count": <number of test cases>,
      "status": "<pass | fail-fixed | fail-abandoned>",
      "failure_reason": "<reason or null>"
    }
  ],
  "untestable_code": [
    {
      "file": "<source file path>",
      "line": <start line>,
      "end_line": <end line>,
      "function": "<function or class name>",
      "barrier": "<hardcoded-dependency | tight-coupling | global-state | ...>",
      "barrier_description": "<brief explanation>",
      "suggested_refactoring": "<what refactoring would help>"
    }
  ],
  "bugs_discovered": [
    {
      "file": "<path>",
      "line": <line>,
      "description": "<bug behavior>",
      "severity": "<High | Medium | Low>"
    }
  ],
  "no_new_tests": <true if zero new tests were written>,
  "no_untestable_code": <true if no untestable code was found>,
  "no_coverage_gained": <true if coverage delta is zero or negative>,
  "blocked": <null, or a one-line string naming the fired Step 2 stop gate and why (e.g. "no test framework detected")>
}
```
````

Convergence signals (`no_new_tests`, `no_untestable_code`, `no_coverage_gained`) drive the orchestrator's termination check.

### 6. Exit

Stop immediately. Do not loop, present reports, or use `AskUserQuestion`.

---

## Refactor Phase Execution

When the `/optimus:deep coverage` orchestrator dispatches `/optimus:refactor` as a subagent for the refactor phase, the orchestrator's prompt body includes `Phase: refactor`; the binding testability focus is carried by the progress file's CLI-pinned `config.focus` (the dispatch prompt mentions it only in prose). The `/optimus:refactor` skill detects `HARNESS_MODE_INLINE` and follows the single-iteration protocol from `references/harness-mode.md` — same protocol used by `/optimus:deep refactor`.

The orchestrator scopes the refactor session to the `untestable_code` items reported by the preceding unit-test phase (the progress file's `scope_files.current` lists those file paths). The CLI's `refactor-step` handles test-and-bisect after the refactor subagent returns.

**Progress-file field mapping.** The coverage-variant progress file differs from the deep-variant schema described in harness-mode.md step 1. When following that protocol here, map: `cycle.current` → `iteration-count` (there is no `iteration` key), `refactor_findings` → `accumulated-findings` (there is no top-level `findings` array), and `config.max_cycles` → the cap. `config.pr_description` does not exist — skip the PR/MR context injection entirely. `config.focus` is present (CLI-pinned to `testability`) and applies as usual.
