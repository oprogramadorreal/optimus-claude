# Harness Mode (single-iteration protocol)

## Contents

1. [Single-Iteration Execution](#single-iteration-execution) — progress file, analysis cycle, fix application, structured JSON output (steps 1–9)
2. [Skill-step execution under harness mode](#skill-step-execution-under-harness-mode) — which base-skill steps run, per-skill scope rules, `pr_description` handling
3. [Termination reasons](#termination-reasons) — enum of exit reasons the orchestrator may record

## Single-Iteration Execution

When running under the `/optimus:deep` orchestrator (a `review` or `refactor` run, or the refactor phase of `deep coverage`), the base skill detects `HARNESS_MODE_INLINE` in its invocation prompt and executes exactly **one iteration** of the analysis cycle, then exits. The orchestrator handles the iteration loop, test execution, bisection, termination detection, and final reporting via `python -m harness_common.cli`.

### 1. Read progress file

Read the JSON progress file at the path specified in your invocation prompt. Extract:
- `iteration.current` — which iteration this is
- `findings` — accumulated findings from prior iterations (with status)
- `scope_files.current` — file paths to analyze
- `config.test_command` — the test command (for reference only — do NOT run it)
- `config.max_iterations` — the iteration cap (for reference only — do NOT check it)
- `config.focus` — finding-cap priority mode (empty string = balanced; used by `refactor` for finding-cap allocation)
- `config.pr_description` — optional `{"title", "body", "base_ref"}` dict captured by the orchestrator when an open PR exists for the current branch (null when no PR or `gh` unavailable)

Initialize from the progress file:
- `iteration-count` = `iteration.current`
- `accumulated-findings` = `findings` array (restoring cross-session state from disk)
- `focus` = `config.focus` (apply to finding-cap logic if the skill supports focus modes)

If `scope_files.current` is non-empty, use it as the file list for agents — this overrides the skill's Step 3 file discovery (the orchestrator pre-populated the scope). If `scope_files.current` is empty, fall back to the skill's Step 3 file discovery (per-skill rules below).

### Skill-step execution under harness mode

After reading the progress file, proceed through all of the skill's remaining numbered steps in order — skip only the user confirmation step (the orchestrator handles approval upfront), the interactive scope offers, and the scope summary presentation. Scope handling is skill-specific:

- **code-review**: Step 3 must take the **No local changes → auto-route** branch and always land on its branch-diff outcome — never PR mode, even when an open PR/MR exists and HEAD is fully pushed (the orchestrator pre-captured the PR description into `config.pr_description`; do not re-fetch via `gh pr view`) — regardless of the working tree's actual state (in `--no-commit` mode the `snapshot` step takes a non-destructive stash via `git stash create`/`store`, so uncommitted changes may still be present), and skip the large-diff warning.
- **refactor**: when `scope_files.current` is non-empty, derive analysis areas from it per Step 2's harness note; when empty, run Step 3's normal directory scan with full-project scope.

If `config.pr_description` is non-null **and the base skill defines a PR/MR context block** (code-review does; refactor ignores `config.pr_description` — its Step 2 harness note states the PR/MR block does not apply), treat it as equivalent to the `pr-description` that interactive Step 3 captures from `gh pr view`: inject it into agent prompts per Step 5 "PR/MR context injection" and apply the Step 6 "PR/MR description as intent signal" soft-confidence adjustment during validation. Do not re-fetch via `gh pr view` — the orchestrator already captured it.

### 2. Build iteration context (iterations 2+)

If `iteration-count` > 1, construct the Iteration Context Block from the accumulated findings using the "Iteration Context Block" template in `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md` — that file is the single source for the block, including the status-values legend, the empty-field fallbacks, and the closing "Focus your review on NEW issues only" instruction.

Harness-specific deltas:

- Do NOT include code content (`pre_edit_content` / `post_edit_content`) in the block — the table uses only the compact fields (file, line, category, summary, status); code content would recreate context bloat.
- Source the "Failed Fix Attempts" bullets from `accumulated-findings`: `fix_description` (what was tried) and `last_failure_hint` (truncated test failure output, max ~200 chars) give the next iteration enough signal to try a different approach instead of repeating the same fix.

### 3. Run one analysis cycle

Launch all agents in parallel — same agents, same prompts, same parallelism as the skill's normal agent step. Inject the Iteration Context Block (from step 2) into agent prompts before the file list, following the same injection order as interactive mode.

### 4. Validate findings

Apply the same validation protocol as the skill's normal validation step. Independently verify each finding, check for false positives, apply change-intent awareness from git history. One clause of that protocol does not carry over: **do not drop what you could not confirm** — see the gate below.

**Auto-apply gate.** Nothing here gets user review before it lands, so only findings your own validation *confirms* earn a fix in step 6. An unconfirmed finding is still recorded in `new_findings` with its confidence. That is a deliberate override of the base protocol's "a finding you cannot confirm is dropped" rule (`references/finding-validation.md`, and the equivalent line in each skill's validation step): dropping keeps an interactive report tight, but here it also erases the loop's only evidence that the iteration found anything — an iteration whose findings were all unconfirmed would emit `no_new_findings: true` and terminate the entire run as `convergence`, reporting clean. Record it instead, and let the empty edit pair mark it un-fixed.

Emit `pre_edit_content` and `post_edit_content` as **empty strings** for such a finding — not omitted. The schema requires both under `additionalProperties: false`, but the runtime validator checks only the envelope — the required arrays and flags — not per-finding keys; the schema validator lives in the test suite. So an omitted key fails *silently*, not loudly — step 6's promotion guard reads it as `None` and skips the finding exactly as it skips an empty string, and the run carries on with output that no longer matches its own contract. An empty `pre_edit_content` is the affirmative "no fix was applied" the rest of this protocol is built on. Agents are told to report rather than pre-filter; this gate, not their silence, is what keeps auto-applied edits honest.

### 5. Consolidate and deduplicate findings

Apply the same deduplication rules as the skill's normal mode, matching against `accumulated-findings` by file + line range + category:
- If existing finding is `"fixed"` → skip new entry (code was intentionally changed)
- If existing finding is `"persistent — fix failed"` → annotate new as `"persistent — fix failed"`
- If existing finding is `"reverted — test failure"` → annotate new as `"reverted — attempt 2"` (the orchestrator will promote to `"persistent — fix failed"` if it fails again)

### 6. Apply fixes

Apply all validated findings using Edit or MultiEdit — same as normal mode. Skip any annotated `"persistent — fix failed"`.

**Critical for orchestrator bisection**: For EACH fix applied, record:
- `pre_edit_content` — the exact original code before editing (the string that was replaced)
- `post_edit_content` — the exact code after editing (the replacement string)

These content pairs enable the orchestrator to mechanically apply/revert individual fixes during test bisection without needing another subagent dispatch. Each pair must be precise enough that `content.replace(pre_edit_content, post_edit_content)` produces the same result as the Edit tool call.

An empty `post_edit_content` is valid — it means the fix deletes the matched code (e.g., removing dead code or a redundant check). The orchestrator supports this.

For fixes that span multiple locations in a single file, output one entry per edit location.

### 7. Do NOT run tests

The orchestrator owns all test execution and bisection — running them here would pull stack traces and assertion failures into the subagent's context window. Do **not** run the project's test command, any `scripts/*.sh`, or any lint / build / coverage invocation — not even to "verify" your own fixes — and skip any such verification step the base skill's normal (interactive) flow would perform; finding validation (step 4) still applies. Apply your edits and emit the JSON.

### 8. Output structured JSON

At the end of the response, emit the iteration results in one `json:harness-output` fenced block.

Read `$CLAUDE_PLUGIN_ROOT/references/schemas/harness-output.schema.json` — it is the contract, and it carries field names, types, which fields are required, the enums, and what `no_actionable_fixes` means. `$CLAUDE_PLUGIN_ROOT/test/harness-common/fixtures/harness-output.golden.json` is a complete worked instance to copy the shape from.

The one thing the schema cannot state: `category` values are skill-specific — use the category the agent that raised the finding assigned it.

### 9. Exit

Stop immediately after outputting the JSON block. Do NOT loop back to the analysis step, present a cumulative or per-iteration report, recommend next steps, use `AskUserQuestion`, or check termination conditions. The orchestrator parses the JSON output, runs tests via the harness CLI, updates the progress file, and decides whether to dispatch another iteration.

### Termination reasons

The orchestrator may record one of these reasons on exit:

- **`convergence`** — zero new findings
- **`no-actionable`** — findings exist but have no code edits
- **`all-reverted`** — every fix this iteration failed tests
- **`diminishing-returns`** — yield plateaued at ≤1 new finding for two consecutive iterations ending at iter 4 or later, with no reverted fixes in either window iteration; remaining issues may exist and can be resumed via `--resume`
- **`cap`** — max iterations hit
- **`parse-failure`** — subagent error (after two consecutive iterations produced no parseable JSON)
- **`blocked`** — coverage target only: the unit-test phase hit a stop gate it cannot work past (no test framework, red baseline). Like `diminishing-returns` it is a resumable soft exit — the orchestrator records it before leaving the loop, and the progress file is left un-archived so `--resume` works once the user clears the prerequisite
