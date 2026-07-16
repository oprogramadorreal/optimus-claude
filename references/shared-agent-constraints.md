# Shared Agent Constraints

Common constraints, quality bar, exclusion rules, and false-positive guidance for
analysis agents. Skill-specific addendums live in each skill's `shared-constraints.md`.

## Agent Constraints

- **Read-only analysis.** Do NOT modify any files, create any files, or run any
  commands that change state. You are analyzing code, not fixing it. One carve-out:
  you MAY run the project's existing test and coverage commands when your agent
  prompt's role explicitly requires it (e.g., a test-guardian verifying the suite
  passes); agents whose role doesn't require test runs remain fully read-only.
- **Your findings will be independently validated.** Another step verifies each
  finding against the actual codebase, so speculation or low-confidence guesses will
  be caught and discarded. Only report what you are confident about.

## Quality Bar

- Every finding must have real impact, not be a nitpick.
- Be specific and actionable (not vague "consider refactoring").
- Assign a confidence level to each finding: **High** (clear evidence), **Medium**
  (plausible with some evidence), or **Low** (uncertain — prefer to omit).

## All Agents Exclude

- Style/formatting concerns (linters handle these)
- Subjective suggestions ("I would prefer...")
- Performance micro-optimizations without clear impact
- Uncertain findings
- Issues explicitly silenced in code (e.g., `// eslint-disable`, `# noqa`)
- **Generated source files** — skip `*.g.dart`, `*.freezed.dart`, `*.mocks.dart`
  (Dart/Flutter build_runner output), `*.Designer.cs` (Visual Studio generated), and
  files inside `Migrations/` directories (EF Core, Django, Alembic, etc.). Changes to
  these files are expected side-effects of model or schema changes.

## Finding Cap

Up to **15** findings — only when each is a distinct root cause with supporting
evidence. Do NOT pad to reach the cap: 3 strong findings are preferred over 15 weak
ones. One exception: **Intent Mismatch** findings (code-review, PR/MR mode only,
defined in `skills/code-review/agents/shared-constraints.md`) have a separate budget
of up to **5** additional findings per agent per pass, on top of the 15.

## Related-File Consistency Check

When you flag an issue in file `X`, also check structurally related files for the
same pattern (or the same pattern missing where it should mirror `X`): siblings with
the same name in a parallel directory, files sharing `X`'s filename stem, and files
that import a symbol named in the finding. Open at most 3 extra files per finding,
only when the link is structural and explicit — no fuzzy "semantically related"
expansion, no browsing for unrelated issues. Report only the related-file occurrence
as a new consistency finding; if nothing matches, do nothing.

## False Positives to Avoid

- Apparently incorrect or unusual-looking but actually correct code (intentional
  deviations) — when evidence of intent is ambiguous, prefer to omit the finding.
  This does not override flagging of genuine bugs, security issues, or guideline
  violations.
- Pedantic nitpicks and linter-catchable issues
- General code quality concerns not tied to project guidelines
- Findings that contradict another agent's domain — e.g., flagging security-motivated
  code (validation rules, sanitization, allowlists) as a KISS/complexity violation.
  When complexity exists to satisfy a security or correctness requirement, it is not
  a guideline violation — KISS means "simplest design that meets current
  requirements," and security is a requirement.
