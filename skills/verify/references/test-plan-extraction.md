# Test Plan Extraction & Generation

How to extract a test plan from a PR/MR description and generate verification items from the branch diff. Used in Step 2 of the verify workflow.

## Extracting from PR/MR Description

Parse the PR/MR body for the `## Test plan` section (matching the Conventional PR format from `$CLAUDE_PLUGIN_ROOT/skills/pr/references/pr-template.md`). Each `- [ ]` item becomes a Verification Plan item.

### Classification Rules

Classify each extracted item by its language:

- **Automated** — mentions running a command, CLI invocation, or test runner (e.g., "Run `npm test`", "Execute the build", "Lint passes")
- **Functional** — describes checking a behavior, exercising a feature, or verifying an outcome (e.g., "POST /endpoint returns 200", "Verify the export includes X", "New component renders correctly")
- **Manual** — requires subjective judgment, visual inspection, or human evaluation (e.g., "Check the UI looks correct", "Confirm the UX flow is intuitive", "Review the error message wording")

If classification is ambiguous, default to **Functional** (the skill can attempt it and escalate to Manual if it fails).

## Generating from Branch Diff

When no PR exists, or the PR has no `## Test plan` section, generate verification items from the diff.

### Source Data

1. `git diff --stat <target-branch>...HEAD` — changed file overview
2. `git diff <target-branch>...HEAD` — full diff
3. `git log --oneline <target-branch>..HEAD` — commit history

### Generation Algorithm

1. **Parse changed files** — categorize as: source code, tests, configuration, documentation, other
2. **Parse commit messages** — extract claimed behaviors (e.g., "feat: add password reset" → "password reset functionality should work")
3. **For each source file changed:**
   - Identify new/modified exports, functions, endpoints, CLI commands, public APIs
   - Generate a Functional item for each: "Verify [function/endpoint/feature] behaves as [commit message / code intent]"
4. **For test files changed:**
   - Generate an Automated item: "Run test suite — verify new/modified tests pass"
5. **Always include standard Automated checks** (if commands are available from CLAUDE.md, testing.md, or manifests):
   - Test suite
   - Build
   - Lint
   - Type-check

### Deduplication

Items that cover the same file and behavior are merged — keep the more specific version.

## Merging PR Plan with Diff-Derived Plan

When both exist:

1. PR test plan items are preserved verbatim — they represent developer intent
2. Diff-derived items are added with a **"Generated"** label
3. If a PR item and a diff-derived item cover the same file/function, keep the PR item and drop the generated one
4. Standard Automated checks (test, build, lint, type-check) are always included regardless of source
