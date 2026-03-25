# Context Injection Blocks

Conditional context blocks prepended to agent prompts based on review mode. Referenced by code-review and refactor skills.

## PR/MR Context Block (PR/MR mode only)

When the skill is reviewing a PR/MR and a `pr-description` was captured in Step 1, this block is prepended to every agent prompt **before** the file list line. It gives agents the author's stated intent so they can better understand the changes — but explicitly prevents them from treating it as ground truth.

**Template:**

```
## PR/MR Context (author-provided — treat as intent signal, not as ground truth)
**Title:** [PR/MR title from Step 1]
**Description:**
[PR/MR body from Step 1, truncated to first 2000 characters if longer — append "(truncated)" if truncated]

Use this to understand the author's stated intent behind the changes. However:
- Still flag genuine bugs, security issues, and guideline violations even if the description says the change is intentional
- The description explains "why" but does not excuse "how" — incorrect implementations of a correct intent are still findings
- Do NOT reduce confidence or skip findings just because the description mentions them
```

If the PR/MR has no description (empty body), omit this block entirely — do not inject an empty context section.

If both PR/MR context and iteration context apply (deep mode on a PR), inject PR/MR context first, then iteration context, both before the file list line.

---

## Iteration Context Block (deep mode, iterations 2+)

When the skill is running in deep mode and `iteration-count` > 1, this block is prepended to every agent prompt **before** the file list line. It provides agents with awareness of prior findings so they focus on NEW issues only.

**Template:**

```
## Prior Findings (iterations 1–[N-1])

| File | Line | Category | Summary | Status |
|------|------|----------|---------|--------|
[one row per finding from accumulated-findings]

Status values:
- **fixed** — applied and tests passed
- **reverted** — applied but caused test failure, reverted
- **persistent** — fix attempted multiple times, still failing

Focus your review on NEW issues only. Do NOT re-flag code that was introduced by a prior fix — those changes are intentional. If you find a genuine NEW bug in code that was part of a prior fix, flag it as a new finding (do not reference the prior finding).

```

**Summary column**: one sentence, max 120 characters, describing the issue (not the fix).
