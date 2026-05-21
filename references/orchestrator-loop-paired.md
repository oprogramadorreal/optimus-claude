# Orchestrator Loop — Paired Cycles (Coverage Variant)

## Contents
1. [Per-cycle body](#per-cycle-body) — steps 1–11 (unit-test phase, refactor phase, history, termination)
2. [After the loop](#after-the-loop)
3. [Per-phase notes](#per-phase-notes)

Shared iteration template for `/optimus:unit-test-deep`. Each **cycle** runs a unit-test phase followed by a conditional refactor-testability phase. The orchestrator skill dispatches `/optimus:unit-test` and `/optimus:refactor` as two distinct subagents per cycle, each in its own fresh context.

The loop control discipline mirrors `references/orchestrator-loop-single.md` (slice-only progress reads, snapshot before dispatch, subagent output is text not state) — see that reference for the rationale. Only the cycle structure differs.

## Per-cycle body

### 1. Snapshot pre-cycle git state

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

Add `--include-stash` if running with `--no-commit` so the working tree can be restored after a failed cycle.

### 2. Dispatch the unit-test subagent

```
Agent tool call:
  subagent_type: general-purpose
  description: "unit-test cycle <N> — unit-test phase"
  prompt: |
    HARNESS_MODE_INLINE
    Progress file: <absolute-progress-path>
    Cycle: <N> of <max>
    Phase: unit-test

    Read the base SKILL.md at `skills/unit-test/SKILL.md` under the
    plugin root and execute its harness-mode protocol from
    `references/coverage-harness-mode.md` ("Unit-Test Phase Execution"
    section) exactly:
    - Read the progress file above for prior coverage and untestable items.
    - Discover gaps, write new tests, measure coverage, flag untestable code.
    - Emit a single ```json:harness-output fenced block and stop.
    - Do not use AskUserQuestion. Do not loop.
```

### 3. Save the subagent return + extract JSON

```bash
TMP_RAW=".claude/.unit-test-deep-raw.txt"
TMP_RESULT=".claude/.unit-test-deep-result.json"
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

Passing `--progress-file` lets the CLI track consecutive parse failures across cycles (and across `--resume`); a single failure is a no-op and the loop moves on, while two consecutive failures cause step 11 (`check-termination`) to return `parse-failure` and terminate the loop. The counter is shared across both phases — a unit-test parse failure followed by a refactor parse failure counts as two consecutive failures.

### 4. Record the unit-test phase

```bash
RESULT=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli unit-test-step \
    --progress-file "<progress-path>" \
    --result-file "$TMP_RESULT")
```

Stdout is one of:

| Output | Meaning |
|---|---|
| `converged` | Skill reported plateau (`no_new_tests` + `no_untestable_code` or `no_coverage_gained`) — cycle ends, loop terminates. |
| `continue` | Unit-test phase complete — proceed to step 5. |

### 5. Commit the unit-test phase checkpoint (skip if `--no-commit`)

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli commit-checkpoint \
    --progress-file "<progress-path>" --phase unit-test
```

### 6. Conditionally dispatch the refactor phase

Check whether there are pending untestable items:

```bash
PENDING=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli pending-refactor-count \
    --progress-file "<progress-path>")
```

If `PENDING == 0`, skip steps 7–9 and jump to step 10.

Otherwise dispatch:

```
Agent tool call:
  subagent_type: general-purpose
  description: "unit-test cycle <N> — refactor phase"
  prompt: |
    HARNESS_MODE_INLINE
    Progress file: <absolute-progress-path>
    Cycle: <N> of <max>
    Phase: refactor

    Read the base SKILL.md at `skills/refactor/SKILL.md` under the
    plugin root and execute its harness-mode protocol from
    `references/harness-mode.md` (with focus = "testability"). The
    progress file lists pending untestable items
    under untestable_code; scope the refactor to those files only.
    Apply fixes; do NOT run tests. Emit a single ```json:harness-output
    fenced block and stop.
```

### 7. Extract the refactor JSON

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

(Same temp file shape as step 3, reused. The `--progress-file` flag continues to update `parse_failure_count` so a refactor-phase parse failure following a unit-test-phase failure triggers `parse-failure` termination.)

### 8. Record the refactor phase

```bash
RESULT=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli refactor-step \
    --progress-file "<progress-path>" \
    --result-file "$TMP_RESULT")
```

Stdout is one of:

| Output | Meaning |
|---|---|
| `converged` | Refactor reported no testability findings or none actionable — cycle ends, loop terminates. |
| `applied fixed=<N> reverted=<N> test_passed=<0\|1>` | Refactor phase complete — proceed to step 9. |

### 9. Commit the refactor phase checkpoint (skip if `--no-commit`)

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli commit-checkpoint \
    --progress-file "<progress-path>" --phase refactor
```

### 10. Record the cycle history + advance

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli record-cycle \
    --progress-file "<progress-path>" \
    --unit-test-summary "<json>" \
    [--refactor-summary "<json>"]
```

`record-cycle` appends a `cycle_history` entry and increments `cycle.current`. The summaries are JSON snippets you can build from the iteration outputs you captured at steps 4 and 8 (counts of tests written, fixes applied, etc.).

### 11. Check termination

```bash
TERMINATION=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli check-termination \
    --progress-file "<progress-path>")
```

Possible values: `continue`, `convergence`, `cap`, `diminishing-returns`, `parse-failure`. If anything other than `continue`, exit the loop. (`parse-failure` is surfaced automatically when the CLI's `parse_failure_count` reaches its threshold — see the parse step above.)

## After the loop

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli final-report \
    --progress-file "<progress-path>" --archive
```

## Per-phase notes

- The unit-test phase runs full project tests after the subagent's writes (the CLI calls `run_tests` internally); the refactor phase bisects on failure (same algorithm as deep-step).
- Tests written by the unit-test phase that fail are recorded with status `fail-fixed` or `fail-abandoned` by the base skill; the CLI does not retest them.
- Coverage delta is computed from `coverage.before` and `coverage.after` reported by the unit-test subagent. The CLI records the history; the orchestrator skill does not need to inspect it directly.
- The orchestrator skill never reads the full `untestable_code` array between cycles — only `pending-refactor-count` decides whether to dispatch the refactor phase.
- **Parse-failure recovery:** identical to the single-loop variant — see `orchestrator-loop-single.md` "Parse-failure recovery". The rule applies to both phase dispatches (unit-test and refactor); a parse failure in either phase counts toward the two-consecutive-failures threshold.
