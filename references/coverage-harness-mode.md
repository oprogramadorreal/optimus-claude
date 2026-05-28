# Coverage Harness Mode

Single-pass protocol for `/optimus:unit-test` when invoked under the `/optimus:unit-test-deep` orchestrator. The orchestrator alternates unit-test and refactor phases per cycle, but each phase runs in its own fresh subagent context as a single pass.

## Contents

1. [Unit-Test Phase Execution](#unit-test-phase-execution) — single pass under orchestrator control (steps 1–6)
2. [Refactor Phase Execution](#refactor-phase-execution) — single pass under orchestrator control (delegates to `harness-mode.md`)

## Unit-Test Phase Execution

When the `/optimus:unit-test-deep` orchestrator dispatches `/optimus:unit-test` as a subagent for the unit-test phase, the base skill detects `HARNESS_MODE_INLINE` in its invocation prompt and the orchestrator's prompt body includes `Phase: unit-test`. Execute exactly **one pass** of the unit-test workflow, then output structured JSON and exit.

### 1. Read progress file

Read the JSON progress file at the path specified in your invocation prompt. Extract:
- `cycle.current` — which cycle this is
- `coverage` — prior coverage data (baseline, current, history)
- `tests_created` — tests written in prior cycles
- `untestable_code` — items flagged as untestable in prior cycles
- `config.test_command` — the test command (for reference only — do NOT run it)
- `config.scope` — path filter (apply to discovery)

### 2. Run discovery and coverage analysis

Run the same Test Infrastructure Analyzer agent as normal mode (Step 2 of SKILL.md). If prior cycles exist, include a brief context block listing previously created test files and known untestable items so the agent avoids duplicating work.

### 3. Generate and write tests

Run Steps 3–4 of SKILL.md (plan + write) with these harness modifications:
- **Skip `AskUserQuestion`** — auto-approve all planned items
- **Cap at 10 items** per pass (same as normal mode)
- **Do NOT run the full test suite** at the end — the orchestrator handles this externally

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
  "no_coverage_gained": <true if coverage delta is zero or negative>
}
```
````

Convergence signals (`no_new_tests`, `no_untestable_code`, `no_coverage_gained`) drive the orchestrator's termination check.

### 6. Exit

Stop immediately. Do not loop, present reports, or use `AskUserQuestion`.

---

## Refactor Phase Execution

When the `/optimus:unit-test-deep` orchestrator dispatches `/optimus:refactor` as a subagent for the refactor phase, the orchestrator's prompt body includes `Phase: refactor` and `Focus: testability`. The `/optimus:refactor` skill detects `HARNESS_MODE_INLINE` and follows the single-iteration protocol from `references/harness-mode.md` — same protocol used by `/optimus:refactor-deep`.

The orchestrator scopes the refactor session to the `untestable_code` items reported by the preceding unit-test phase (the progress file's `scope_files.current` lists those file paths). The CLI's `refactor-step` handles test-and-bisect after the refactor subagent returns.
