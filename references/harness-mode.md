# Harness Mode (single-iteration protocol)

## Contents

1. [Single-Iteration Execution](#single-iteration-execution) — progress file, analysis cycle, fix application, structured JSON output (steps 1–9)
2. [Termination reasons](#termination-reasons) — enum of exit reasons the orchestrator may record

## Single-Iteration Execution

When running under an orchestrator skill (`/optimus:code-review-deep` or `/optimus:refactor-deep`), the base skill detects `HARNESS_MODE_INLINE` in its invocation prompt and executes exactly **one iteration** of the analysis cycle, then exits. The orchestrator handles the iteration loop, test execution, bisection, termination detection, and final reporting via `python -m harness_common.cli`.

### Contents

1. [Read progress file](#1-read-progress-file)
2. [Build iteration context](#2-build-iteration-context-iterations-2)
3. [Run one analysis cycle](#3-run-one-analysis-cycle)
4. [Validate findings](#4-validate-findings)
5. [Consolidate and deduplicate findings](#5-consolidate-and-deduplicate-findings)
6. [Apply fixes](#6-apply-fixes)
7. [Do NOT run tests](#7-do-not-run-tests)
8. [Output structured JSON](#8-output-structured-json)
9. [Exit](#9-exit)

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

If `scope_files.current` is non-empty, use it as the file list for agents — this overrides the skill's Step 3 file discovery (the orchestrator pre-populated the scope). If `scope_files.current` is empty, fall back to the skill's Step 3 file discovery via git.

### Skill-step execution under harness mode

After reading the progress file, proceed through all of the skill's remaining numbered steps in order — skip only the user confirmation step (the orchestrator handles approval upfront). Under harness mode, Step 3 (or its skill-equivalent) must use the "no local changes → branch-diff" path automatically: the orchestrator requires a clean working tree, so local changes will always be empty. Skip the interactive scope offers, the scope summary presentation, and the large-diff warning.

If `config.pr_description` is non-null, treat it as equivalent to the `pr-description` that interactive Step 3 captures from `gh pr view`: inject it into agent prompts per Step 5 "PR/MR context injection" and apply the Step 6 "PR/MR description as intent signal" soft-confidence adjustment during validation. Do not re-fetch via `gh pr view` — the orchestrator already captured it, and skipping the extra fetch keeps the subagent's turn budget lean.

### 2. Build iteration context (iterations 2+)

If `iteration-count` > 1, construct the Iteration Context Block from the accumulated findings using the same template as `$CLAUDE_PLUGIN_ROOT/references/context-injection-blocks.md`:

```
## Prior Findings (iterations 1–[N-1])

| File | Line | Category | Summary | Status |
|------|------|----------|---------|--------|
[one row per finding from accumulated-findings]

### Failed Fix Attempts
[one bullet per reverted/persistent finding only — omit fixed findings]
- **<file>:<line>** (<category>): Tried: <fix_description>. Failed: <last_failure_hint>
```

The main table uses only compact fields (file, line, category, summary, status). Do NOT include code content (`pre_edit_content` / `post_edit_content`) in the context block, as that would recreate context bloat.

The "Failed Fix Attempts" section is appended **only when reverted or persistent findings exist**. It surfaces `fix_description` (what was tried) and `last_failure_hint` (truncated test failure output, max ~200 chars) so the next iteration can try a different approach instead of repeating the same fix. Omit the section entirely if all findings are fixed.

### 3. Run one analysis cycle

Launch all agents in parallel — same agents, same prompts, same parallelism as the skill's normal agent step. Inject the Iteration Context Block (from step 2) into agent prompts before the file list, following the same injection order as interactive mode.

### 4. Validate findings

Apply the same validation protocol as the skill's normal validation step. Independently verify each finding, check for false positives, apply change-intent awareness from git history.

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

The orchestrator handles test execution and bisection externally. This keeps test output (stack traces, assertion failures) out of the subagent's context window. Do not run the test command.

### 8. Output structured JSON

At the end of the response, output the iteration results in this exact format:

````
```json:harness-output
{
  "iteration": <number>,
  "new_findings": [
    {
      "file": "<path>",
      "line": <number>,
      "end_line": <number>,
      "category": "<category from the agent finding — skill-specific>",
      "guideline": "<specific rule or 'General: ...'>",
      "summary": "<one-sentence, max 120 chars>",
      "fix_description": "<brief description of the fix applied>",
      "severity": "<Critical | Warning | Suggestion>",
      "confidence": "<High | Medium>",
      "agent": "<agent-name>",
      "pre_edit_content": "<exact original code>",
      "post_edit_content": "<exact replacement code>"
    }
  ],
  "fixes_applied": [
    <same structure as new_findings — the subset that were actually applied via Edit/MultiEdit>
  ],
  "fixes_skipped_persistent": ["<id of findings skipped due to persistent status>"],
  "no_new_findings": <true if zero new findings discovered>,
  "no_actionable_fixes": <true ONLY if every finding has empty pre_edit_content (i.e., no swap pair was captured); any finding with a non-empty pre_edit_content + a different post_edit_content counts as actionable, regardless of file type — markdown, JSON, config, and code edits all qualify>
}
```
````

### 9. Exit

Stop immediately after outputting the JSON block. Do NOT:
- Loop back to the analysis step
- Present a cumulative or per-iteration markdown report
- Recommend next steps
- Use `AskUserQuestion`
- Check termination conditions (convergence, cap, all-reverted, diminishing-returns)

The orchestrator parses the JSON output, runs tests via the harness CLI, updates the progress file, and decides whether to dispatch another iteration.

### Termination reasons

The orchestrator may record one of these reasons on exit:

- **`convergence`** — zero new findings
- **`no-actionable`** — findings exist but have no code edits
- **`all-reverted`** — every fix this iteration failed tests
- **`diminishing-returns`** — yield plateaued at ≤1 new finding for two consecutive iterations after iter 4, with no reverted fixes in either window iteration; remaining issues may exist and can be resumed via `--resume`
- **`cap`** — max iterations hit
- **`parse-failure`** — subagent error (after two consecutive iterations produced no parseable JSON)
