# Shared Agent Constraints

Common constraints, quality bar, exclusion rules, and false-positive guidance for analysis agents. Skill-specific addendums live in each skill's `shared-constraints.md`.

## Agent Constraints

- **Read-only analysis.** Do NOT modify any files, create any files, or run any commands that change state. You are analyzing code, not fixing it. One carve-out: you MAY run the project's existing test or coverage commands when your agent prompt's role explicitly requires it — never under `HARNESS_MODE_INLINE`, where the orchestrator owns every test run.
- **Report what you find; do not pre-filter for the reader.** A later pass validates every finding against the actual codebase and drops what it cannot confirm. Label confidence honestly and let that pass do its job — a real issue you withheld is the more expensive error, and it is the one nobody downstream can recover.

## Dual Lens

When `.claude/docs/skill-writing-guidelines.md` exists, the project authors markdown instructions for an AI agent, and those files follow different quality rules than code. Judge `.md` files under `skills/`, `agents/`, `prompts/`, `commands/`, or `instructions/` (including nested `references/`) by `skill-writing-guidelines.md`; judge everything else — including shell hooks, scripts, and JSON manifests — by `coding-guidelines.md`. Never cross the two. When the file does not exist, this does not apply.

## Quality Bar

- Every finding must have real impact, not be a nitpick
- Be specific and actionable (not vague "consider refactoring")
- Label each finding **High** (clear evidence), **Medium** (plausible, some evidence), or **Low** (uncertain, or evidence you could not confirm)

## All Agents Exclude

- Style/formatting concerns (linters handle these)
- Subjective suggestions ("I would prefer...")
- Performance micro-optimizations without clear impact
- Issues explicitly silenced in code (e.g., `// eslint-disable`, `# noqa`)
- **Generated source files** — skip mechanical output such as `*.g.dart`, `*.freezed.dart`, `*.mocks.dart` (Dart/Flutter build_runner output) and `*.Designer.cs` when generation provenance confirms it. A migration directory is not proof of generation: review authored schema operations and data transformations; skip only confirmed mechanical snapshots or generated sections.

## Finding Cap

Up to **15** findings, each a distinct root cause with supporting evidence. The cap is a ceiling, not a target — do not pad to reach it. A skill may define a finding category that composes on top of this cap; when yours does, its own shared-constraints file states that budget.

## Structural-Neighbor Scope Expansion

When you flag an issue in file `X`, check the files structurally tied to it — same-name siblings, files that import or re-export a symbol you named — for the same pattern, or for its absence where it should mirror `X`. Report each as a new consistency finding referencing the original as its trigger.

Limits: at most **3** extra files per original finding, reached through a structural link you can point at rather than a hunch; never duplicate the original finding. Expansion is opportunistic — if nothing is structurally tied, do nothing.

## False Positives to Avoid

- Apparently incorrect or unusual-looking but actually correct code (intentional deviations). Where the evidence of intent is ambiguous, report it at **Low** confidence and name the evidence you could not confirm.
- Pedantic nitpicks
- Linter-catchable issues
- Code-quality opinions you cannot tie to the guidelines you were given — the project's own, or the baseline set handed to you when the project has none
- Complexity that exists to satisfy a security or correctness requirement is not a guideline violation — KISS means "simplest design that meets current requirements," and security is a requirement. Blocklists, allowlists, validation rules, sanitization, and deliberate safety measures are not over-engineering. (You do not need to predict what other agents will say: contradictions between agents are resolved during consolidation, which sees every agent's output.)
