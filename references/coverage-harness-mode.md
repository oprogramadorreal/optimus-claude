# Coverage Harness Mode

Protocol for the test-coverage harness — an automated loop that alternates `/optimus:unit-test` and `/optimus:refactor testability` to maximize test coverage.

## Contents

1. [Skill-Triggered Invocation](#skill-triggered-invocation) — early-exit fast path: resolve environment, build command, present and stop (steps 1–6)
2. [Unit-Test Phase Execution](#unit-test-phase-execution) — single pass under harness control (steps 1–6)
3. [Refactor Phase Execution](#refactor-phase-execution) — single pass under harness control (steps 1–6)

## Skill-Triggered Invocation

When a user invokes `/optimus:unit-test deep harness [N] ["scope"]`, the skill delegates here for an early-exit fast path. The user already opted in by typing `harness`, so no confirmation is needed. Follow these steps in order and stop at the end — do not return to the calling skill.

### 1. Resolve plugin root

Run `echo $CLAUDE_PLUGIN_ROOT` via Bash. Store the result as `plugin_root`. If the output is empty, stop with: "Cannot resolve plugin root — ensure optimus-claude is installed via the Claude Code plugin system."

### 2. Check Python

Run `python3 --version` via Bash. If it fails, try `python --version`. If neither returns Python 3.8+, stop with: "Harness requires Python 3.8+. Install Python and retry." Remember which command worked (`python3` or `python`) and the version string for step 5.

### 3. Check for existing progress

Run `ls .claude/test-coverage-progress.json 2>/dev/null` via Bash. If the file exists, set `resume` = true. Otherwise `resume` = false.

### 4. Build command

Construct the harness command using these parameters passed by the calling skill:
- `max_cycles` — optional cycle cap (omit `--max-cycles` if using default 5)
- `scope` — optional scope text from user arguments (omit `--scope` if empty)
- `resume` — from step 3

```
<python_cmd> "<plugin_root>/scripts/test-coverage-harness/main.py" --progress-file .claude/test-coverage-progress.json [--max-cycles <N>] [--scope "<scope>"] [--resume]
```

Where `<python_cmd>` is `python3` or `python` (whichever worked in step 2). Wrap `<plugin_root>` in quotes to handle paths with spaces. The constructed command must be a single line (no backslash continuations) for easy copy-paste on all platforms.

### 5. Present command

Output the following directly — no `AskUserQuestion`:

> **Test-coverage harness mode** — copy and run this command in your terminal:
>
> Python: `[version string from step 2]`
>
> ```bash
> <constructed command from step 4>
> ```
>
> Additional options: `--timeout <seconds>`, `--scope "<text>"`, `--max-cycles <N>`, `--verbose`, `--no-commit`, `--resume`, `--allowed-tools Read,Edit,Write,MultiEdit,Glob,Grep,Bash,Agent`
>
> You can edit the command before running it — for example, add `--scope "focus on src/auth"` to narrow the analysis, or `--max-cycles 8` to increase the cap.
>
> **How it works:** The harness alternates between `/optimus:unit-test` (to write tests for testable code) and `/optimus:refactor testability` (to refactor untestable code), looping until coverage plateaus or the cycle cap is reached. Each phase spawns a fresh `claude -p` session. All commits are local — nothing is pushed. To undo everything: `git reset --hard <base-commit>`.
>
> **Why can't I run it for you?** The Bash tool enforces a timeout (default 2 min, max 10 min), but each phase may take several minutes. Running in your terminal gives real-time progress and avoids timeout issues.

### 6. Stop

Do not proceed to the skill's remaining steps. The harness runs externally.

---

## Unit-Test Phase Execution

When running under the external test-coverage harness (detected by `HARNESS_MODE_ACTIVE` in the system prompt with `phase: unit-test`), execute exactly **one pass** of the unit-test workflow, then output structured JSON and exit.

### 1. Read progress file

Read the JSON progress file at the path specified in the system prompt. Extract:
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
- **Do NOT run the full test suite** at the end — the harness handles this externally

### 4. Collect results

Gather: tests written (file, target, count, status), coverage change, untestable code items, bugs discovered.

### 5. Output structured JSON

Output the results in a `json:harness-output` fenced block (see Step 6 of SKILL.md for the exact schema). Key fields:
- `tests_written` — what was generated
- `coverage` — before/after/delta
- `untestable_code` — items that need refactoring
- `no_new_tests`, `no_untestable_code`, `no_coverage_gained` — convergence signals

### 6. Exit

Stop immediately. Do not loop, present reports, or use `AskUserQuestion`.

---

## Refactor Phase Execution

When running under the test-coverage harness with `phase: refactor`, the `/optimus:refactor` skill executes using the existing harness-mode protocol from `references/harness-mode.md` (Single-Iteration Execution, steps 1–9). The key difference is that the harness invokes the skill as `/optimus:refactor deep N testability` — the `testability` positional focus keyword scopes the refactor to the `untestable_code` items reported by the preceding unit-test phase. The refactor skill detects `HARNESS_MODE_ACTIVE` from the system prompt and follows `references/harness-mode.md` as usual.

The refactor skill already supports `HARNESS_MODE_ACTIVE` and outputs `json:harness-output` — no changes needed to its behavior. The test-coverage harness handles:
- Feeding untestable code items as the scope for the refactor session
- Running tests after refactoring
- Bisecting fixes on test failure
- Creating checkpoint commits
