# Orchestrator Loop

## Contents
1. [Shared invariants](#shared-invariants) — plugin root, loop control, parse-failure recovery
2. [Single-skill loop](#single-skill-loop-review--refactor-modes) — `deep review` / `deep refactor`, steps 1–8
3. [Paired-cycle loop](#paired-cycle-loop-coverage-mode) — `deep coverage`, steps 1–11
4. [After the loop](#after-the-loop)

Iteration template for `/optimus:deep`. The orchestrator dispatches a base skill
(`code-review`, `refactor`, or `unit-test`) into a fresh subagent context per
iteration, parses the structured JSON the base skill emits, and uses the harness CLI
to manage state, test/bisect, and decide termination.

The orchestrator never holds findings or fixes in conversation prose. All state lives
in the progress file. Each Bash invocation of the CLI is a discrete operation; the
orchestrator reads the CLI's stdout to make decisions.

## Shared invariants

**Plugin root.** Every command below writes `$CLAUDE_PLUGIN_ROOT` to mean the plugin
root the orchestrator skill resolved in its Plugin-root step. Bash-tool environment
variables do **not** persist across separate Bash calls and may read empty on some
platforms (notably Windows); if `echo $CLAUDE_PLUGIN_ROOT` was empty there, substitute
the resolved absolute path **literally** into every `PYTHONPATH=...` command and into
every dispatch prompt in this file.

**Loop control:**

- **Snapshot before dispatch.** The CLI's step subcommands need a fresh `pre_head` to
  recover from test failures, and verify the snapshot's `iteration_token` matches the
  current iteration — a skipped snapshot makes the step exit non-zero rather than
  restore to a stale commit.
- **Always write progress before dispatching.** Cancellation between dispatches is
  recoverable via `--resume`; cancellation mid-dispatch may leave the working tree
  inconsistent but the progress file remains valid as of the prior iteration.
- **Slice-only progress reads.** Do not read the full progress file's `findings` or
  `untestable_code` arrays between iterations in the orchestrator's own context. The
  CLI's `check-termination` returns a single word; trust it.
- **Subagent output is text, not state.** Treat each subagent's return as a one-time
  payload. Save it to a temp file verbatim, parse it, then forget it. Do not keep the
  raw output in the orchestrator's conversation.
- **Re-entry guard.** If the orchestrator's own invocation prompt body already
  contains `HARNESS_MODE_INLINE`, stop with "Deep mode cannot run inside deep mode".
- **Don't end a turn on a promise.** Mid-loop, if the next step is a tool call, issue
  it — never end a turn with a bare "I'll run X next". End only at termination or when
  blocked on input only the user can provide.
- **Report only what the CLI confirmed.** Per-iteration status comes from the step
  subcommands' / `check-termination`'s stdout — don't assert results the CLI did not
  return, and if a step was skipped or a count is unverified, say so.

**Parse-failure recovery.** If the CLI's `parse` subcommand exits non-zero, the
subagent emitted no `json:harness-output` block (it hit a budget limit, missed the
`HARNESS_MODE_INLINE` router, or hung interactively). On a single failure: warn the
user and continue — the iteration is a no-op. Skip the step/commit subcommands for
this iteration (`parse` only rewrites the result file on success, so it still holds
the previous iteration's JSON and a step subcommand would silently re-process it) and
continue at `check-termination`, then advance. The CLI also rolls the failed
dispatch's partial edits back to the iteration snapshot so nothing half-done is left
for a later checkpoint to commit. Two consecutive failures (across phases and across
`--resume` — the counter lives in the progress file and resets on every successful
parse) make `check-termination` return `parse-failure`; exit the loop and surface the
error for the user to investigate.

## Single-skill loop (review / refactor modes)

Repeat steps 1–8 until step 7 (`check-termination`) returns anything other than
`continue`. `<base-skill>` is `code-review` (review mode) or `refactor` (refactor
mode).

### 1. Snapshot pre-iteration git state

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

Records `HEAD` into `progress["_snapshot"]["pre_head"]` and stamps the current
iteration into `progress["_snapshot"]["iteration_token"]`. In no-commit mode — the
run was started `--no-commit`, or a prior commit failed — `snapshot` also captures a
working-tree stash automatically, so the iteration stays restorable.

### 2. Dispatch the base skill into a fresh subagent

Use the `Agent` tool. The prompt **must** include the inline sentinel, the absolute
progress-file path, the iteration counter, and instructions to read the base SKILL.md
from disk:

```
Agent tool call:
  subagent_type: general-purpose
  description: "<base-skill> iteration <N>"
  prompt: |
    HARNESS_MODE_INLINE
    Plugin root: <absolute-plugin-root>
    Progress file: <absolute-progress-path>
    Iteration: <N> of <max>
    Phase: <base-skill>

    Read the base SKILL.md at
    `<absolute-plugin-root>/skills/<base-skill>/SKILL.md` and execute its
    harness-mode protocol from
    `<absolute-plugin-root>/references/harness-mode.md` exactly. Wherever the
    base SKILL.md, harness-mode.md, or the agent prompt files they load
    reference `$CLAUDE_PLUGIN_ROOT`, substitute the absolute plugin root
    above — your environment may not export it:
    - Read the progress file above for accumulated findings and scope.
    - Run the analysis cycle once.
    - Apply fixes. Do NOT run the test command, any `scripts/*.sh`, or any
      lint/build — the orchestrator owns all test execution and bisection.
    - Emit a single ```json:harness-output fenced block and stop.
    - Do not use AskUserQuestion. Do not loop.
```

The subagent does not inherit `$CLAUDE_PLUGIN_ROOT`, so pass the absolute path — and
the subagent must substitute it onward into the fan-out agent prompts it composes, per
"Prompt assembly at dispatch time" in `$CLAUDE_PLUGIN_ROOT/references/agent-architecture.md`.
The subagent inherits the working tree and applies edits via `Edit`/`MultiEdit`; on
return, the working tree carries the iteration's changes and the subagent's final
message contains the structured JSON.

### 3. Save the subagent return to a temp file

Write the subagent's final message text to a temp file **verbatim** — never
summarize, abbreviate, or re-type any part of it: the `pre_edit_content` /
`post_edit_content` strings inside the JSON are the bisect's apply/revert data, and a
corrupted copy makes its fix unrecoverable (`skipped — apply failed`). Saving to a
file also keeps the raw output out of the orchestrator's parent context:

```bash
TMP_RAW=".claude/.deep-iteration-raw.txt"
TMP_RESULT=".claude/.deep-iteration-result.json"
```

These files must live in `.claude/` and carry these exact filename prefixes
(`.deep-iteration-` and `.unit-test-deep-`) — the checkpoint commit's un-stage step
(`commit_checkpoint` in `scripts/harness_common/git.py`) matches the
`.claude/`-anchored patterns `.claude/.deep-iteration-*` and
`.claude/.unit-test-deep-*` to keep harness state out of the commit, and
`final-report`'s scratch cleanup only sweeps the progress file's own directory.

### 4. Extract the structured JSON

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

Errors on a missing `json:harness-output` block — see "Parse-failure recovery" above.

### 5. Process the iteration

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli deep-step \
    --progress-file "<progress-path>" \
    --result-file "$TMP_RESULT"
```

This single subcommand: promotes actionable fixes, registers findings, runs tests,
bisects on failure, updates per-finding statuses, appends iteration history, widens
scope, and writes the result. Its stdout is one of:

| Output | Meaning |
|---|---|
| `converged` | Skill reported `no_new_findings` — loop terminates. |
| `no-actionable` | Skill reported `no_actionable_fixes` — loop terminates. |
| `all-reverted` | Every fix in this iteration was reverted — loop terminates. |
| `applied fixed=<N> reverted=<N> test_passed=<0\|1\|->` | Iteration completed normally — continue. `test_passed` is `-` when the iteration applied no fixes (so no test ran). |

### 6. Checkpoint commit

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli commit-checkpoint --progress-file "<progress-path>"
```

Returns `committed`, `nothing-to-commit`, `commit-skipped`, or `commit-failed`. Call
it every iteration — the CLI owns the decision: in no-commit mode it self-skips and
prints `commit-skipped`. On `commit-failed`, the CLI durably disables commits for the
rest of the run (persisted, so it survives `--resume`): later snapshots auto-stash and
later checkpoints self-skip, keeping the accumulated uncommitted work restorable.
Warn the user once that checkpoint commits have stopped.

### 7. Check termination

```bash
TERMINATION=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli check-termination \
    --progress-file "<progress-path>")
```

Possible values: `continue`, `convergence`, `no-actionable`, `all-reverted`, `cap`,
`diminishing-returns`, `parse-failure`. If the value is anything other than
`continue`, exit the loop.

### 8. Advance the iteration counter

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli advance --progress-file "<progress-path>"
```

Increments `iteration.current`. Then loop back to step 1.

## Paired-cycle loop (coverage mode)

Each **cycle** runs a unit-test phase followed by a conditional refactor-testability
phase, each in its own fresh subagent context. The shared invariants above apply; the
parse-failure counter is shared across both phases — a refactor parse failure followed
by the next cycle's unit-test parse failure counts as two consecutive failures.

### 1. Snapshot pre-cycle git state

Same command as single-skill step 1. Steps 4 and 8 error out on a stale
`iteration_token`.

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

Write the unit-test subagent's final message text **verbatim** to `$TMP_RAW`, then
extract:

```bash
TMP_RAW=".claude/.unit-test-deep-ut-raw.txt"
TMP_RESULT=".claude/.unit-test-deep-result.json"
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

**Blocked gate:** if the extracted JSON has a non-null `blocked` field, the unit-test
phase hit a stop gate it cannot work past (no test framework, failing baseline — see
coverage-harness-mode.md "Stop gates under harness mode"). Do not run
`unit-test-step` and do not dispatch further cycles: exit the loop, report the
`blocked` reason to the user with the matching base-skill recovery advice
(`/optimus:init` for a missing framework or broken build; triage the failing tests
for a red baseline), and proceed to "After the loop".

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

Same contract as single-skill step 6.

### 6. Conditionally dispatch the refactor phase

Check whether there are pending untestable items:

```bash
PENDING=$(PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli pending-refactor-count \
    --progress-file "<progress-path>")
```

If `PENDING == 0`, skip steps 7–9 and jump to step 10.

Otherwise, **re-snapshot before dispatching the refactor subagent** so a
refactor-phase rollback only undoes refactor edits:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli snapshot --progress-file "<progress-path>"
```

The unit-test phase (steps 2–5) wrote and committed new tests this cycle. The step-1
snapshot predates them, so a refactor-phase combined-regression restore against it
would discard them. Re-running `snapshot` re-stamps the current cycle token and moves
`pre_head` / `pre_stash` forward to the post-unit-test state, so a refactor rollback
preserves the cycle's tests.

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

Write the **refactor** subagent's final message text **verbatim** to a refactor-phase
raw file — distinct from the unit-test phase's file (step 3) so a forgotten write
fails the parse loudly (missing file) instead of silently re-ingesting the stale
unit-test JSON. Then extract:

```bash
TMP_RAW=".claude/.unit-test-deep-rf-raw.txt"
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli parse \
    --input-file "$TMP_RAW" \
    --output-file "$TMP_RESULT" \
    --progress-file "<progress-path>"
```

(`$TMP_RESULT` is reused from step 3 — `refactor-step` reads it immediately after
this parse.)

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

`record-cycle` appends a `cycle_history` entry and increments `cycle.current`. The
summaries are JSON snippets built from the phase outputs captured at steps 4 and 8
(counts of tests written, fixes applied, etc.).

Step 4's `continue` does not distinguish a green merge from a red-suite rollback (see
Per-phase notes), so the unit-test counts are subagent-reported, not CLI-confirmed.
In commit mode, `nothing-to-commit` from step 5 despite reported tests indicates the
cycle was rolled back — record zero tests written for the phase and say so in the
status update; otherwise attribute counts to the subagent (e.g. *"subagent reported 4
tests"*) rather than asserting they were kept.

On a failed parse, never run a `*-step` subcommand against the stale `$TMP_RESULT`: a
unit-test-phase failure skips steps 4–9, a refactor-phase failure skips steps 8–9; in
both cases continue here (record the cycle, noting the parse failure), then step 11.

### 11. Check termination

Same command as single-skill step 7. Possible values in coverage mode: `continue`,
`convergence`, `cap`, `diminishing-returns`, `parse-failure`. If anything other than
`continue`, exit the loop.

### Per-phase notes

- The unit-test phase runs full project tests after the subagent's writes (the CLI
  calls `run_tests` internally) **before** merging the session's results. If the
  suite is red, the CLI rolls the working tree back to the pre-cycle snapshot and
  drops the session output, so a failing cycle is never committed and its
  coverage/untestable/bug data never leaks into later cycles; on green it merges and
  proceeds. The refactor phase bisects on failure (same algorithm as `deep-step`).
- The unit-test base skill is expected to leave the suite green (failing tests it
  writes are marked `fail-fixed` or `fail-abandoned` and not left active); the CLI
  does not retest individual tests. Its full-suite run is the safety net — a red
  result rolls the whole cycle back rather than committing it.
- Coverage delta is taken from the unit-test subagent's `coverage.delta`, or derived
  from `coverage.before`/`coverage.after` when the subagent omits it (so the plateau
  check still fires on a genuine zero-gain cycle).
- The orchestrator never reads the full `untestable_code` array between cycles — only
  `pending-refactor-count` decides whether to dispatch the refactor phase.

## After the loop

Print the final report:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/scripts" python -m harness_common.cli final-report --progress-file "<progress-path>" --archive
```

The `--archive` flag moves the progress file to its `.done.json` sibling (the `.json`
suffix is replaced — e.g. `.claude/code-review-deep-progress.done.json`) and removes
the backup, signaling that this run is complete (a subsequent `--resume` will refuse
the archived path) — **except** when the run ended in `diminishing-returns`, a
resumable soft-exit: the CLI then leaves the active progress file in place (prints
`not-archived`) so `--resume` can continue it. The archived `.done.json` is a
historical artifact the user may delete at any time; a later fresh run (`init`)
checks only the active progress path and won't clean it up.
