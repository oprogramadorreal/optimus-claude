# Agent Prompt Templates

Prompt templates for the quality gate agents in Step 8. Both agents run in parallel after all TDD cycles complete.

## Agent A — Code Simplifier (only if `.claude/agents/code-simplifier.md` exists)

```
Read `.claude/agents/code-simplifier.md` for your role and approach.
Read `.claude/docs/coding-guidelines.md` and `.claude/CLAUDE.md` for project standards.

Review ALL of the following files for cross-cycle simplification opportunities:
[list of changed file paths]

This code was written incrementally across multiple TDD cycles. Look for issues
that emerge from incremental development:
- Duplication across behaviors (e.g., similar handlers that should share logic)
- Naming inconsistencies between code written in different cycles
- Dead code introduced early then superseded by later cycles
- Pattern violations that accumulated gradually
- Abstractions that should be extracted now that the full feature shape is visible

Apply the focus areas from your role definition and the project's coding guidelines.
For each finding: file:line, guideline violated, brief description, suggested improvement.
Do NOT suggest changes outside the changed files. Do NOT flag style/formatting, bugs, or security.
Maximum 5 findings. Report as a structured list.
```

## Agent B — Test Guardian (only if `.claude/agents/test-guardian.md` exists)

```
Read `.claude/agents/test-guardian.md` for your role and approach.
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
