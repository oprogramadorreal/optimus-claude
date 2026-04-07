# Harness Mode

## Contents

1. [Skill-Triggered Invocation](#skill-triggered-invocation) — early-exit fast path: resolve environment, build command, present and stop (steps 1–6)
2. [Single-Iteration Execution](#single-iteration-execution) — progress file, analysis cycle, fix application, structured JSON output (steps 1–9)

## Skill-Triggered Invocation

When a user invokes a skill with `deep harness` (e.g., `/optimus:code-review deep harness` or `/optimus:refactor deep harness 8 "focus on backend"`), the skill delegates here for an early-exit fast path. The user already opted in by typing `harness`, so no confirmation is needed. Follow these steps in order and stop at the end — do not return to the calling skill.

### 1. Resolve plugin root

Run `echo $CLAUDE_PLUGIN_ROOT` via Bash. Store the result as `plugin_root`. If the output is empty, stop with: "Cannot resolve plugin root — ensure optimus-claude is installed via the Claude Code plugin system."

### 2. Check Python

Run `python3 --version` via Bash. If it fails, try `python --version`. If neither returns Python 3.8+, stop with: "Harness requires Python 3.8+. Install Python and retry." Remember which command worked (`python3` or `python`) and the version string for step 5.

### 3. Check for existing progress

Run `ls .claude/deep-mode-progress.json 2>/dev/null` via Bash. If the file exists, set `resume` = true. Otherwise `resume` = false.

### 4. Build command

Construct the harness command using these parameters passed by the calling skill:
- `skill_name` — the skill identifier (e.g., `code-review`, `refactor`)
- `scope` — optional scope text from user arguments (omit `--scope` if empty)
- `max_iterations` — optional iteration cap (omit `--max-iterations` if using default 8)
- `focus` — optional focus keyword for finding-cap priority, used by `refactor` (omit `--focus` if empty or if the skill does not define focus modes)
- `resume` — from step 3

```
<python_cmd> "<plugin_root>/scripts/deep-mode-harness/main.py" --skill <skill_name> --progress-file .claude/deep-mode-progress.json [--max-iterations <N>] [--scope "<scope>"] [--focus <focus>] [--timeout <seconds>] [--resume]
```

Where `<python_cmd>` is `python3` or `python` (whichever worked in step 2). Wrap `<plugin_root>` in quotes to handle paths with spaces. The constructed command must be a single line (no backslash continuations) for easy copy-paste on all platforms.

### 5. Present command

Output the following directly — no `AskUserQuestion`:

> **Deep harness mode** — copy and run this command in your terminal:
>
> Python: `[version string from step 2]`
>
> ```bash
> <constructed command from step 4>
> ```
>
> Additional options: `--timeout <seconds>`, `--scope "<text>"`, `--max-iterations <N>`, `--focus <testability|guidelines>`, `--verbose`, `--no-commit`, `--resume`, `--allowed-tools Read,Edit,Write,MultiEdit,Glob,Grep,Bash,Agent`
>
> You can edit the command before running it — for example, add `--scope "focus on src/auth"` to narrow the analysis, or `--max-iterations 12` to increase the cap. When running the script directly from your terminal (without invoking the skill first), use these flags to pass context that would otherwise come from the skill arguments.
>
> **WARNING:** The harness will iterate up to N times, each spawning a fresh `claude -p` session. On each iteration it analyzes code, applies fixes, runs tests, and creates a checkpoint commit. All commits are local — nothing is pushed. To undo everything: `git reset --hard <base-commit>`.
>
> **Why can't I run it for you?** The Bash tool enforces a timeout (default 2 min, max 10 min), but each iteration may take several minutes. Running in your terminal gives real-time progress and avoids timeout issues.

### 6. Stop

Do not proceed to the skill's remaining steps. The harness runs externally.

---

## Single-Iteration Execution

When running under the external deep-mode harness (detected by `HARNESS_MODE_ACTIVE` in the system prompt), execute exactly **one iteration** of the analysis cycle, then exit. The harness handles the iteration loop, test execution, bisection, termination detection, and final reporting.

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

Read the JSON progress file at the path specified in the system prompt. Extract:
- `iteration.current` — which iteration this is
- `findings` — accumulated findings from prior iterations (with status)
- `scope_files.current` — file paths to analyze
- `config.test_command` — the test command (for reference only — do NOT run it)
- `config.max_iterations` — the iteration cap (for reference only — do NOT check it)
- `config.focus` — finding-cap priority mode (empty string = balanced; used by `refactor` for finding-cap allocation)
- `config.pr_description` — optional `{"title", "body", "base_ref"}` dict captured by the harness when an open PR exists for the current branch (null when no PR or `gh` unavailable)

Initialize from the progress file:
- `deep-mode` = true
- `iteration-count` = `iteration.current`
- `accumulated-findings` = `findings` array (restoring cross-session state from disk)
- `focus` = `config.focus` (apply to finding-cap logic if the skill supports focus modes)

If `scope_files.current` is non-empty, use it as the file list for agents — this overrides the skill's Step 3 file discovery (the harness pre-populated the scope). If `scope_files.current` is empty, fall back to the skill's Step 3 file discovery via git.

### Steps 3, 4, 5 execution under harness mode

After reading the progress file, proceed through the skill's Step 3, Step 4, and Step 5 in order. Skip only the Step 2 user confirmation. Under harness mode, Step 3 must use the "no local changes → branch-diff" path automatically: the harness requires a clean working tree, so local changes will always be empty. Skip the interactive scope offers, the scope summary presentation, and the large-diff warning.

If `config.pr_description` is non-null, treat it as equivalent to the `pr-description` that interactive Step 3 captures from `gh pr view`: inject it into agent prompts per Step 5 "PR/MR context injection" and apply the Step 6 "PR/MR description as intent signal" soft-confidence adjustment during validation. Do not re-fetch via `gh pr view` — the harness already captured it, and skipping the extra fetch keeps the Claude session turn budget lean.

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

Apply the same deduplication rules as interactive deep mode, matching against `accumulated-findings` by file + line range + category:
- If existing finding is `"fixed"` → skip new entry (code was intentionally changed)
- If existing finding is `"persistent — fix failed"` → annotate new as `"persistent — fix failed"`
- If existing finding is `"reverted — test failure"` → annotate new as `"reverted — attempt 2"` (the harness will promote to `"persistent — fix failed"` if it fails again)

### 6. Apply fixes

Apply all validated findings using Edit or MultiEdit — same as normal mode. Skip any annotated `"persistent — fix failed"`.

**Critical for harness bisection**: For EACH fix applied, record:
- `pre_edit_content` — the exact original code before editing (the string that was replaced)
- `post_edit_content` — the exact code after editing (the replacement string)

These content pairs enable the harness to mechanically apply/revert individual fixes during test bisection without needing another Claude session. Each pair must be precise enough that `content.replace(pre_edit_content, post_edit_content)` produces the same result as the Edit tool call.

An empty `post_edit_content` is valid — it means the fix deletes the matched code (e.g., removing dead code or a redundant check). The harness supports this.

For fixes that span multiple locations in a single file, output one entry per edit location.

### 7. Do NOT run tests

The harness handles test execution and bisection externally. This keeps test output (stack traces, assertion failures) out of the context window. Do not run the test command.

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
  "no_actionable_fixes": <true if findings exist but none had actionable code edits>
}
```
````

### 9. Exit

Stop immediately after outputting the JSON block. Do NOT:
- Loop back to the analysis step
- Present a cumulative or per-iteration markdown report
- Recommend next steps
- Use `AskUserQuestion`
- Check termination conditions (convergence, cap, all-reverted)

The harness reads the JSON output, runs tests, updates the progress file, and decides whether to launch another iteration.
