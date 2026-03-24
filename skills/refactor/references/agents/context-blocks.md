# Context Blocks

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

Focus your review on NEW issues only. Do NOT re-flag code that was introduced by a prior fix — those changes are intentional. If you find a genuine NEW issue in code that was part of a prior fix, flag it as a new finding (do not reference the prior finding).

```

**Summary column**: one sentence, max 120 characters, describing the issue (not the fix).
