# Shared Agent Constraints

Common constraints, quality bar, exclusion rules, and false-positive guidance for analysis agents. Skill-specific addendums live in each skill's `shared-constraints.md`.

## Agent Constraints

- **Read-only analysis.** Do NOT modify any files, create any files, or run any commands that change state. You are analyzing code, not fixing it.
- **Your findings will be independently validated.** Another step verifies each finding against the actual codebase, so speculation or low-confidence guesses will be caught and discarded. Only report what you are confident about.

## Quality Bar

- Every finding must have real impact, not be a nitpick
- Be specific and actionable (not vague "consider refactoring")
- Be high confidence — assign a confidence level to each finding: **High** (clear evidence), **Medium** (plausible with some evidence), or **Low** (uncertain — prefer to omit)

## All Agents Exclude

- Style/formatting concerns (linters handle these)
- Subjective suggestions ("I would prefer...")
- Performance micro-optimizations without clear impact
- Uncertain findings
- Issues explicitly silenced in code (e.g., `// eslint-disable`, `# noqa`)
- **Generated source files** — skip `*.g.dart`, `*.freezed.dart`, `*.mocks.dart` (Dart/Flutter build_runner output), `*.Designer.cs` (Visual Studio generated), and files inside `Migrations/` directories (database migration files — EF Core, Django, Alembic, etc.). Changes to these files are expected side-effects of model or schema changes and should not be flagged.

## False Positives to Avoid

- Apparently incorrect but actually correct code (intentional deviations)
- Pedantic nitpicks
- Linter-catchable issues
- General code quality concerns not tied to project guidelines
- Findings that contradict another agent's domain — e.g., flagging security-motivated code (blocklists, allowlists, validation rules, sanitization) as a KISS/complexity violation, or flagging deliberate safety measures as over-engineered. When complexity exists to satisfy a security or correctness requirement, it is not a guideline violation — KISS means "simplest design that meets current requirements," and security is a requirement.
