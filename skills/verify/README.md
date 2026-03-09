# /optimus:verify

Verify that a feature branch works as described — in an isolated sandbox, not just on paper.

## What It Does

1. **Extracts or generates a verification plan** from the PR test plan and branch diff
2. **Creates an isolated sandbox** (git worktree) so verification doesn't touch your working tree
3. **Runs automated checks** — test suite, build, lint, type-check
4. **Launches parallel agents** for functional verification — writes tests, runs integration scenarios, creates mock consumer projects, traces code paths
5. **Handles limitations** — asks for human help when automation can't verify something
6. **Reports results** with a clear verdict and offers to fix issues

All work happens inside the sandbox. The remote repository is never modified.

## When to Use

- **After development, before merging** — prove the feature works before requesting review
- **After creating a PR** — validate the PR's test plan items automatically
- **Mid-development** — check progress against the test plan while still working on the feature
- **After code changes** — re-verify that everything still works after fixes or refactoring

## When Not to Use

- **On the default branch** — this skill is for feature branches only
- **For static code review** — use `/optimus:code-review` instead (it analyzes code quality)
- **For writing tests** — use `/optimus:tdd` (test-driven development) or `/optimus:unit-test` (coverage gaps)
- **For code quality** — use `/optimus:simplify` (cross-file simplification)

## How It Works

### Verification Plan

The skill builds a verification plan from two sources:

- **PR test plan** — if a PR/MR exists, the `## Test plan` section is extracted and each item is classified
- **Branch diff analysis** — changed files, commit messages, and new/modified functions are analyzed to generate additional verification items

Items are classified as:
- **Automated** — run a command and check the exit code (test suite, build, lint, type-check)
- **Functional** — exercise a behavior through tests, integration scenarios, mock projects, or code tracing
- **Manual** — requires human judgment (UI, UX, subjective quality)

### Sandbox

The sandbox is a git worktree at `.worktrees/verify-<branch-slug>`. It shares the repository's object database (instant creation, no network clone) but has its own working tree. Dependencies are installed inside the sandbox.

If git worktrees are unavailable (git < 2.15), the skill falls back to a temporary `.verify-sandbox/` directory.

### Verification Agents

Up to 4 parallel agents handle functional verification:

| Agent | Role | Creates |
|-------|------|---------|
| Test Writer | Writes and runs verification tests | Test files in the sandbox |
| Integration Verifier | Sets up and exercises integration scenarios | Servers, requests, CLI invocations |
| Mock Project Verifier | Creates minimal consumer projects for libraries/APIs | `_mock/` directory in the sandbox |
| Behavior Tracer | Traces code paths and verifies logic | Analysis report, optional verification scripts |

### Report

Results are consolidated into a structured report with:
- Summary and verdict (ALL PASSED / ISSUES FOUND / PARTIAL)
- Per-item status with evidence
- Detailed issue descriptions with file:line references
- Coverage metrics

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `/optimus:code-review` | **Complementary** — code-review is static ("is the code correct?"), verify is dynamic ("does it work?") |
| `/optimus:tdd` | **Different timing** — TDD builds features test-first; verify validates after implementation |
| `/optimus:unit-test` | **Different scope** — unit-test fills project-wide coverage gaps; verify tests branch-specific claims |
| `/optimus:pr` | **Producer-consumer** — pr generates the test plan, verify consumes and validates it |

## Prerequisites

- Git (2.15+ for worktree support, falls back gracefully)
- A feature branch with commits ahead of the target branch
- `gh` CLI (for GitHub PR extraction) or `glab` CLI (for GitLab MR extraction) — optional, the skill works without PR data

**Recommended:** Run `/optimus:init` first for project context (CLAUDE.md, coding guidelines, testing docs).

## Supported Stacks

Node.js/TypeScript, Python, Rust, Go, C#/.NET, Java (Maven/Gradle), C/C++ (CMake). Mock project scaffolds are available for all stacks.

## Skill Structure

```
skills/verify/
├── SKILL.md                          # 9-step verification workflow
├── README.md                         # This file
└── references/
    ├── agent-prompts.md              # Prompt templates for the 4 verification agents
    ├── mock-project-scaffolds.md     # Per-stack minimal consumer project templates
    └── test-plan-extraction.md       # PR parsing and diff-based generation algorithm
```

Shared references consumed from other skills:
- `init/references/multi-repo-detection.md` — workspace detection
- `init/references/verification-protocol.md` — evidence-based verification discipline
- `pr/references/platform-detection.md` — GitHub/GitLab detection and CLI verification
- `pr/references/pr-template.md` — Conventional PR format (test plan section)
- `tdd/references/testing-anti-patterns.md` — mocking discipline for verification tests
