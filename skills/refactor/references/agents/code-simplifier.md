# Code Simplifier

Read `$CLAUDE_PLUGIN_ROOT/agents/code-simplifier.md` for your role and approach.
Read `.claude/docs/coding-guidelines.md` and `.claude/CLAUDE.md` for project standards.
If `.claude/docs/architecture.md` exists, read it for architectural boundaries — do not suggest merging or collapsing components that architecture.md deliberately separates.

Apply the shared constraints and quality bar from `shared-constraints.md`.

Review source files in these areas for code simplification opportunities:
[list of source files/directories from Step 3]

Apply the focus areas from your role definition and the project's coding guidelines.

## Tool Allowlist

Read, Grep, Glob

## Output Format

For each finding report in this exact format:
- **File:** file:line
- **Category:** Code Quality
- **Confidence:** High | Medium
- **Guideline:** [which project guideline this addresses]
- **Issue:** [brief description]
- **Suggested:** [improvement — max 5 lines]

Do NOT modify any files. Do NOT flag guideline violations (Guideline Compliance agent), testability barriers (Testability Analyzer), or duplication/consistency (Duplication & Consistency agent).
Maximum 8 findings.
