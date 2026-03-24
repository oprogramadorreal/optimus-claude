# Code Simplifier

Read `$CLAUDE_PLUGIN_ROOT/agents/code-simplifier.md` for your role and approach.
Read `.claude/docs/coding-guidelines.md` and `.claude/CLAUDE.md` for project standards.

Apply the shared constraints and quality bar from `shared-constraints.md`.

Review ONLY the following changed files for code simplification opportunities:
[list of changed file paths from Step 1]

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

Do NOT modify any files. Do NOT suggest changes outside the changed files. Do NOT flag style/formatting, bugs, security, or guidelines.
Maximum 8 findings.
