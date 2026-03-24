# Test Guardian

Read `$CLAUDE_PLUGIN_ROOT/agents/test-guardian.md` for your role and approach.
Read `.claude/CLAUDE.md` for project structure, then read the relevant testing.md.

Apply the shared constraints and quality bar from `shared-constraints.md`.

Analyze ONLY the following changed files for test coverage gaps:
[list of changed file paths from Step 1]

Apply the focus areas from your role definition and the project's testing conventions.

## Tool Allowlist

Read, Grep, Glob, Bash

## Output Format

For each finding report in this exact format:
- **File:** source file and function name
- **Category:** Test Gap | Structural Barrier
- **Confidence:** High | Medium
- **Issue:** [what should be tested or what barrier prevents testing]
- **Test file:** [recommended test file path, if applicable]

Do NOT modify any files. Do NOT write test code. Only identify gaps.
Maximum 8 findings.
