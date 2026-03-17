# Verification Protocol

Cross-cutting verification discipline for all optimus skills. Every claim of success, completion, or correctness must be backed by fresh evidence from the current execution.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

## Gate Function

Before claiming any status (pass, fixed, complete, working, clean):

1. **IDENTIFY** — which command proves this assertion? (test runner, linter, build, type-checker)
2. **RUN** — execute the command now (not from memory, not from a previous run)
3. **READ** — examine the complete output: exit code, pass/fail counts, error messages
4. **VERIFY** — does the output actually support the claim?
   - YES → state the claim WITH evidence (e.g., "All 34 tests pass — exit code 0")
   - NO → report the actual status with evidence
5. **ONLY THEN** — express the claim

Omitting any step misrepresents progress.

## Evidence Requirements

| Assertion | Required Evidence | NOT Sufficient |
|-----------|-------------------|----------------|
| Tests pass | Test output showing 0 failures + exit code 0 | Earlier runs, assumptions, "should pass" |
| Linter clean | Linter output with 0 errors/warnings | Partial checks, different tool output |
| Build succeeds | Build completion with exit code 0 | Linter passing (linter ≠ compiler) |
| Bug fixed | Test reproducing the bug now passes | Code changes alone without test proof |
| Regression verified | Red-green cycle confirmed (fail → fix → pass) | Single passing test run |
| Agent completed | VCS diff showing actual changes | Agent's self-reported success message |
| All requirements met | Point-by-point verification against spec | Test success alone |

## Rationalization Prevention

When you catch yourself thinking any of these, STOP and run the verification:

| Thought | Reality |
|---------|---------|
| "Should work now" | Run the command and prove it |
| "I'm confident" | Confidence is not evidence |
| "Just this once" | No exceptions to verification |
| "Linter passed so it builds" | Linter ≠ compiler — run the build |
| "The agent reported success" | Verify independently — check the diff |
| "This is a small change" | Small changes cause big failures |
| "I already checked earlier" | Earlier ≠ now — state may have changed |
| "Partial verification is enough" | Partial verification proves nothing |

## Assumption Check

Before committing to an approach (architecture, algorithm, API design, dependency choice), surface and verify assumptions:

1. **LIST** — what does this approach assume about inputs, scale, dependencies, or environment?
2. **CHALLENGE** — for each assumption, ask: what happens if this assumption is wrong?
3. **ALTERNATIVES** — are there simpler or more robust approaches not yet considered?
4. **EVIDENCE** — is the chosen approach supported by project constraints (architecture.md, coding guidelines), or is it preference?

| Thought | Reality |
|---------|---------|
| "This is the obvious approach" | Obvious to whom? List what it assumes |
| "The user asked for X, so X" | The user's goal matters more than their suggested implementation |
| "This library/pattern is standard" | Standard doesn't mean right for this project — check constraints |
| "Everyone does it this way" | Popularity is not evidence of fitness |
| "This worked before" | Different context may invalidate prior success |

## Red Flags

Stop immediately if you notice:

- Modal language before verification: "should", "probably", "appears to"
- Satisfaction before evidence: "Great!", "Perfect!", "Done!"
- Readiness to commit/push without a fresh test run
- Treating agent self-reports as ground truth
- Skipping verification due to fatigue or time pressure
- Agreeing with an approach without considering alternatives
- Implementing the first solution that comes to mind
