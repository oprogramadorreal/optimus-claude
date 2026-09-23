# Finding Validation

Shared protocol for checking analysis-agent findings before they reach a report or become a fix. Consumers: `/optimus:code-review` Step 6 and `/optimus:refactor` Step 5, each of which layers its own corroboration and confidence policy on top.

Treat agent findings as claims needing independent evidence, not ground truth. Verify against the actual code and report what you observed, never what "should" be true. Agents are instructed to report rather than pre-filter, so this pass — not their silence — is what makes the output trustworthy.

For each finding:

- **Context** — read the code around the flagged location, enough of it to tell whether the issue holds in context rather than in isolation.
- **Intent** — comments, test assertions, or an established pattern may show the code is deliberate. What looks like a bug is sometimes a decision.
- **Pre-existing** — for diff-scoped reviews, the issue must be introduced by the changes under review rather than inherited from untouched code. Skills that analyze existing code rather than a diff skip this check.
- **Runtime assumptions** — unvalidated, undocumented assumptions about inputs, dependencies, or the environment strengthen a finding.

**Change-intent awareness.** For files carrying findings, check recent history — `git log --no-merges --format="%h %s" -5 -- <file>`, reading `git show <sha> -- <file>` when the messages are uninformative. If a recent commit deliberately introduced what a finding wants to remove or revert ("fix null check", "harden auth flow", "add dependency injection"), lower that finding's confidence: someone already made this call, and the finding is arguing with them without their context. Skip gracefully when history is unavailable — a shallow clone or a new file is not evidence either way.

A finding you cannot confirm is dropped, but count the drops: report how many, so what the filter removed stays visible rather than silent. An agent's Low label describes its evidence, not yours: promote a Low finding your own check confirms rather than dropping it.
