# Spec / task context detection

Resolves the task description from the project's spec and JIRA artifacts before implementation begins. Owned by `/optimus:tdd`; a consuming skill applies its own framing — the `AskUserQuestion` option wording, the inline-argument fallback, and what it does with a `## Scenarios` section are the consumer's policy.

## Context detection cascade

Evaluate in order; first match wins. Run this regardless of whether the user also gave an inline task description.

1. **Explicit reference** — if the user's input references a file path ending in `.md` inside `docs/specs/` or `docs/jira/`, read that file and use its Goal section as the task description. (A `docs/specs/<spec>.md` is the active build spec — authored by `/optimus:brainstorm` or brought by a human; see `$CLAUDE_PLUGIN_ROOT/references/sdd-mapping.md`.) Proceed to distillation below if the goal is longer than 2-3 sentences.

2. **Build spec auto-discovery** — if item 1 did not fire and `docs/specs/` exists with `.md` files, select the most recent (by filename date prefix if present, otherwise file modification time). Present it via `AskUserQuestion` — question "Found build spec `<path>` — use it as the basis?", header "Build spec", options "Use it" / "Ignore — describe a different task". If that date — the filename prefix, or the modification time when there is no prefix — is older than 7 days, add a note to the question: "(This spec is [N] days old — if it is a `/optimus:brainstorm`-authored spec, you may want to re-run brainstorm for a fresh design.)" A `docs/specs/` build spec is either a `/optimus:brainstorm`-authored spec (full approach details — use Goal, Components, and Interfaces) or a human-authored spec (use Goal and Acceptance Criteria). A `## Scenarios` section in Given/When/Then form carries stakeholder-approved acceptance criteria — the consuming skill decides how to use it.

3. **JIRA context auto-discovery** — if no build spec resolved (none found, or the user ignored it) but `docs/jira/` exists with `.md` files, read each file's YAML frontmatter and select the one with the most recent `date` field. Present it via `AskUserQuestion` — question "Found JIRA context `<path>` — use it as the basis?", header "JIRA context", options "Use it" / "Ignore — describe a different task". If its date is older than 7 days, add a note to the question: "(This context is [N] days old — you may want to re-run `/optimus:jira` for fresh data.)" JIRA context provides Goal and Acceptance Criteria as the task description.

4. **No context found** — fall back to the consuming skill's own task gathering (inline argument, else `AskUserQuestion`).

Precedence (first match wins): `docs/specs/` build spec → JIRA context → none. The build spec takes priority because it is the most detailed (a `/optimus:brainstorm`-authored spec incorporates JIRA context if brainstorm consumed it).

If context detection resolved a task description (the user accepted a spec or JIRA context), use it — skip the consuming skill's inline/prompt gathering. Otherwise fall back to that gathering.

## Distillation

Apply this to the **final task description, whatever its source** — a spec or JIRA context resolved by the cascade above, *or* a long task the user pasted inline (or supplied via the consuming skill's fallback `AskUserQuestion`). If it is longer than ~2-3 sentences (e.g., a pasted spec, JIRA ticket, or acceptance-criteria list), distill it into a **single-sentence goal** and confirm with `AskUserQuestion` — header "Distilled goal", question "I've distilled your spec to: '[single-sentence summary]'. Is this accurate?":
- **Looks good** — "Proceed with this goal"
- **Adjust** — "Let me refine the focus"
