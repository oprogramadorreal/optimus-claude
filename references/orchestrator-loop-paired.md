# Orchestrator Loop — Paired Cycles (Coverage Variant)

## Contents
1. [Per-cycle body](#per-cycle-body) — steps 1–11 (unit-test phase, refactor phase, history, termination)
2. [After the loop](#after-the-loop)
3. [Per-phase notes](#per-phase-notes)

Shared iteration template for `/optimus:unit-test-deep`. Each **cycle** runs a unit-test phase followed by a conditional refactor-testability phase. The orchestrator skill dispatches `/optimus:unit-test` and `/optimus:refactor` as two distinct subagents per cycle, each in its own fresh context.

The loop control discipline mirrors `references/orchestrator-loop-single.md` (slice-only progress reads, snapshot before dispatch, subagent output is text not state, plus the long-run conduct invariants — don't end a turn on a promise, and report only what the CLI confirmed) — see that reference for the rationale. Only the cycle structure differs.

**Plugin root.** Every command below writes `$CLAUDE_PLUGIN_ROOT` to mean the plugin root the orchestrator skill resolved in its Step 2. Bash-tool environment variables do **not** persist across separate Bash calls and may read empty on some platforms (notably Windows); if `echo $CLAUDE_PLUGIN_ROOT` was empty there, substitute the resolved absolute path **literally** into every `PYTHONPATH=...` command and into both dispatch prompts in this file.

## Per-cycle body

### 1. Snapshot pre-cycle git state

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

Records `pre_head` and stamps the current cycle into `_snapshot.iteration_token` (steps 4 and 8 error out on a stale token). In no-commit mode `snapshot` also captures a working-tree stash automatically, so you do **not** need `--include-stash` (it remains an explicit override).

### 2. Dispatch the unit-test subagent

```
Agent tool call:
  subagent_type: general-purpose
  description: "unit-test cycle <N> — unit-test phase"
  prompt: |
    HARNESS_MODE_INLINE
    Plugin root: <absolute-plugin-root>
    Progress file: <absolute-progress-path>
    Cycle: <N> of <max>
    Phase: unit-test

    Read the base SKILL.md at
    `<absolute-plugin-root>/skills/unit-test/SKILL.md` and execute its
    harness-mode protocol from
    `<absolute-plugin-root>/references/coverage-harness-mode.md` ("Unit-Test
    Phase Execution" section) exactly. Wherever the base SKILL.md or that
    reference mentions `$CLAUDE_PLUGIN_ROOT`, substitute the absolute plugin
    root above — your environment may not export it:
    - Read the progress file above for prior coverage and untestable items.
    - Discover gaps, write new tests, measure coverage, flag untestable code.
    - Emit a single ```json:harness-output fenced block and stop.
    - Do not use AskUserQuestion. Do not loop.
```

### 3. Save the subagent return + extract JSON

Write the unit-test subagent's final message text to `$TMP_RAW`, then extract the JSON:

```bash
TMP_RAW=".claude/.unit-test-deep-ut-raw.txt"
TMP_RESULT=".claude/.unit-test-deep-result.json"
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

Passing `--progress-file` lets the CLI track consecutive parse failures across cycles (and across `--resume`); a single failure is a no-op and the loop moves on, while two consecutive failures cause step 11 (`check-termination`) to return `parse-failure` and terminate the loop. The counter is shared across both phases — a unit-test parse failure followed by a refactor parse failure counts as two consecutive failures.

**Blocked gate:** if the extracted JSON has a non-null `blocked` field, the unit-test phase hit a stop gate it cannot work past (no test framework, failing baseline — see coverage-harness-mode.md "Stop gates under harness mode"). Do not run `unit-test-step` and do not dispatch further cycles: exit the loop, report the `blocked` reason to the user with the matching base-skill recovery advice (`/optimus:init` for a missing framework or broken build; triage the failing tests for a red baseline), and proceed to "After the loop".

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
| `continue` | Unit-test phase complete — proceed to step 5. Also printed after a red-suite rollback (the CLI reverts the cycle's tests and drops the phase JSON without a distinct token — see Per-phase notes). |

### 5. Commit the unit-test phase checkpoint

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli commit-checkpoint \
    --progress-file "<progress-path>" --phase unit-test
```

Call this every cycle — in no-commit mode it self-skips (`commit-skipped`); on `commit-failed` the CLI durably disables commits for the rest of the run (later snapshots auto-stash). Same contract as `orchestrator-loop-single.md` step 6.

### 6. Conditionally dispatch the refactor phase

Check whether there are pending untestable items:

```bash
PENDING=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli pending-refactor-count \
    --progress-file "<progress-path>")
```

If `PENDING == 0`, skip steps 7–9 and jump to step 10.

Otherwise, **re-snapshot before dispatching the refactor subagent** so a refactor-phase rollback only undoes refactor edits:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

The unit-test phase (steps 2–5) wrote and committed new tests this cycle. The step-1 snapshot predates them, so a refactor-phase combined-regression restore against it would discard them. Re-running `snapshot` re-stamps the current cycle token (so step 8's freshness check still passes) and moves `pre_head` / `pre_stash` forward to the post-unit-test state, so a refactor rollback preserves the cycle's tests.

Then dispatch:

```
Agent tool call:
  subagent_type: general-purpose
  description: "unit-test cycle <N> — refactor phase"
  prompt: |
    HARNESS_MODE_INLINE
    Plugin root: <absolute-plugin-root>
    Progress file: <absolute-progress-path>
    Cycle: <N> of <max>
    Phase: refactor

    Read the base SKILL.md at
    `<absolute-plugin-root>/skills/refactor/SKILL.md` and execute its
    harness-mode protocol from
    `<absolute-plugin-root>/references/harness-mode.md` (with focus =
    "testability"). Wherever the base SKILL.md or harness-mode.md reference
    `$CLAUDE_PLUGIN_ROOT`, substitute the absolute plugin root above — your
    environment may not export it. The progress file lists pending untestable
    items under untestable_code; scope the refactor to those files only.
    Apply fixes. Do NOT run the test command, any `scripts/*.sh`, or any
    lint/build — the orchestrator owns all test execution. Emit a single
    ```json:harness-output fenced block and stop.
```

### 7. Save the refactor return + extract the refactor JSON

Write the **refactor** subagent's final message text to a refactor-phase raw file — distinct from the unit-test phase's file (step 3) so a forgotten write fails the parse loudly (missing file) instead of silently re-ingesting the stale unit-test JSON. Then extract:

```bash
TMP_RAW=".claude/.unit-test-deep-rf-raw.txt"
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

(`$TMP_RESULT` is reused from step 3 — refactor-step reads it immediately after this parse. The `--progress-file` flag continues to update `parse_failure_count` so a refactor-phase parse failure following a unit-test-phase failure triggers `parse-failure` termination.)

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
| `applied fixed=<N> reverted=<N> test_passed=<0\|1\|->` | Refactor phase complete — proceed to step 9. `test_passed` is `-` when no fixes were applied. |

### 9. Commit the refactor phase checkpoint

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli commit-checkpoint \
    --progress-file "<progress-path>" --phase refactor
```

Self-skips in no-commit mode (same contract as step 5).

### 10. Record the cycle history + advance

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli record-cycle \
    --progress-file "<progress-path>" \
    --unit-test-summary "<json>" \
    [--refactor-summary "<json>"]
```

`record-cycle` appends a `cycle_history` entry and increments `cycle.current`. The summaries are JSON snippets you can build from the phase outputs you captured at steps 4 and 8 (counts of tests written, fixes applied, etc.).

Step 4's `continue` does not distinguish a green merge from a red-suite rollback (see Per-phase notes), so the unit-test counts are subagent-reported, not CLI-confirmed. In commit mode, `nothing-to-commit` from step 5 despite reported tests indicates the cycle was rolled back — record zero tests written for the phase and say so in the status update; otherwise attribute counts to the subagent (e.g. *"subagent reported 4 tests"*) rather than asserting they were kept.

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

`--archive` moves the progress file to `<path>.done.json` once the run is complete — except on a `diminishing-returns` soft-exit, which the CLI leaves un-archived (prints `not-archived`) so the run stays resumable via `--resume`.

## Per-phase notes

- The unit-test phase runs full project tests after the subagent's writes (the CLI calls `run_tests` internally) **before** merging the session's results. If the suite is red, the CLI rolls the working tree back to the pre-cycle snapshot and drops the session output, so a failing cycle is never committed and its coverage/untestable/bug data never leaks into later cycles; on green it merges and proceeds. The refactor phase bisects on failure (same algorithm as deep-step).
- The unit-test base skill is expected to leave the suite green (failing tests it writes are marked `fail-fixed` or `fail-abandoned` and not left active); the CLI does not retest individual tests. Its full-suite run is the safety net — a red result rolls the whole cycle back rather than committing it.
- Coverage delta is taken from the unit-test subagent's `coverage.delta`, or derived from `coverage.before`/`coverage.after` when the subagent omits it (so the plateau check still fires on a genuine zero-gain cycle). The CLI records the history; the orchestrator skill does not need to inspect it directly.
- The orchestrator skill never reads the full `untestable_code` array between cycles — only `pending-refactor-count` decides whether to dispatch the refactor phase.
- **Parse-failure recovery:** identical to the single-loop variant — see `orchestrator-loop-single.md` "Parse-failure recovery". The rule applies to both phase dispatches (unit-test and refactor); a parse failure in either phase counts toward the two-consecutive-failures threshold.
