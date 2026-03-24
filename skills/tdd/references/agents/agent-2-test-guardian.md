# Agent 2 — Test Guardian (only if test infrastructure detected)

```
Read `$CLAUDE_PLUGIN_ROOT/agents/test-guardian.md` for your role and approach.
Read `.claude/CLAUDE.md` for project structure, then read the relevant testing.md.

Analyze ALL of the following files for test coverage gaps:
[list of changed file paths]

This code was built using TDD — every behavior has a test. Focus on what TDD's
one-behavior-at-a-time approach may have missed:
- Edge cases and boundary conditions not covered by the happy-path-first tests
- Error propagation paths across multiple behaviors
- Test-to-source mapping for all new/modified source files
- Structural barriers that prevent unit testing (tight coupling, hidden dependencies)

Run the full test suite to confirm everything passes.
Apply the focus areas from your role definition and the project's testing conventions.
For each finding: source file and function name, finding type (Test Gap | Structural Barrier),
what should be tested or what barrier prevents testing, recommended test file path (if applicable).
Do NOT write test code. Only identify gaps.
Maximum 5 findings. Report as a structured list.
```
