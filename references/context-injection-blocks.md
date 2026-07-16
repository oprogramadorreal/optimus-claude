# Context Injection Blocks

Conditional context blocks prepended to agent prompts based on review mode. Referenced by code-review and refactor skills.

## PR/MR Context Block (PR/MR mode only)

When the skill is reviewing a PR/MR and a `pr-description` was captured during scope determination, this block is prepended to every agent prompt **before** the file list line. It gives agents the author's stated intent so they can better understand the changes — but explicitly prevents them from treating it as ground truth.

**Template:**

```
## PR/MR Context (author-provided — treat as intent signal, not as ground truth)
**Title:** [captured PR/MR title]
**Description:**
[captured PR/MR body, truncated to first 2000 characters if longer — append "(truncated)" if truncated]

Use this to understand the author's stated intent behind the changes. However:
- Still flag genuine bugs, security issues, and guideline violations even if the description says the change is intentional
- The description explains "why" but does not excuse "how" — incorrect implementations of a correct intent are still findings
- Do NOT reduce confidence or skip findings just because the description mentions them
- If the description makes specific, testable claims (problem, scope, non-goals, key decisions) AND your output format includes the `Intent Mismatch` category (see your per-agent PR/MR-mode addendum), check whether the diff delivers each claim. A claim with no supporting code change, or a code change that contradicts a stated non-goal, is a finding — report it under category `Intent Mismatch`. Agents without a PR/MR-mode addendum (e.g., `code-simplifier`) skip this check entirely. If the description is empty or merely narrative with no testable claims, skip this check; never invent intent.
```

If the PR/MR has no description (empty body), omit this block entirely — do not inject an empty context section.

If both PR/MR context and iteration context apply (harness mode on a PR), inject PR/MR context first, then iteration context, both before the file list line.

---

## Iteration Context Block (harness mode, iterations 2+)

When the skill is running under `HARNESS_MODE_INLINE` and the progress file's `iteration.current` is greater than 1, this block is prepended to every agent prompt **before** the file list line. It provides agents with awareness of prior findings so they focus on NEW issues only.

**Template:**

```
## Prior Findings (iterations 1–[N-1])

| File | Line | Category | Summary | Status |
|------|------|----------|---------|--------|
[one row per finding from accumulated-findings]

Status values:
- **fixed** — applied and tests passed
- **reverted — test failure** — applied but caused a test failure, reverted
- **reverted — attempt 2** — second attempt at a previously reverted finding, reverted again
- **skipped — apply failed** — the fix's content swap did not apply cleanly, skipped
- **persistent — fix failed** — fix attempted multiple times, still failing

[if any findings have a reverted, skipped, or persistent status (any status other than fixed), append this section:]

### Failed Fix Attempts
[one bullet per reverted/skipped/persistent finding — omit for fixed findings]
- **<file>:<line>** (<category>): Tried: <fix_description>. Failed: <last_failure_hint>

[If fix_description is empty, write "Tried: (no description)". If last_failure_hint is empty, write "Failed: (no test output captured)".]

Focus your review on NEW issues only. Do NOT re-flag code that was introduced by a prior fix — those changes are intentional. If you find a genuine NEW bug in code that was part of a prior fix, flag it as a new finding (do not reference the prior finding). For reverted/persistent findings, use the "Failed Fix Attempts" section to understand what was already tried and WHY it failed — attempt a different approach rather than repeating the same fix.

```

**Summary column**: one sentence, max 120 characters, describing the issue (not the fix).
**Failed Fix Attempts section**: only included when there are reverted, skipped, or persistent findings. Kept compact — one line per finding with truncated test output (max ~200 chars). This gives the next iteration enough signal to try a different approach without bloating context.
