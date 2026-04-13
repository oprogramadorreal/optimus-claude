# Architecture

## Overview

A Claude Code plugin that combines markdown-based skill authoring (16 skills invoked via `/optimus:<name>`) with Python harness orchestrators that drive iterative Claude sessions for deep code review, refactoring, and test coverage.

## Directory Map

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Plugin manifests (plugin.json, marketplace.json) |
| `agents/` | Plugin-level agent definitions (code-simplifier, test-guardian) |
| `hooks/` | Plugin-level hooks (SessionStart for project state awareness) |
| `references/` | Shared reference docs consumed by multiple skills |
| `skills/<name>/` | One directory per skill (SKILL.md + README.md + optional agents/, references/, templates/) |
| `scripts/harness_common/` | Shared Python library used by both harnesses |
| `scripts/deep-mode-harness/` | Deep-mode harness: iterative code-review/refactor orchestrator |
| `scripts/test-coverage-harness/` | Test-coverage harness: iterative unit-test + refactor orchestrator |
| `scripts/test-skills.sh` | Skill execution test runner |
| `test/` | pytest suites mirroring each harness module |

## Code Architecture

### Data Flow

- Entry: `main.py` (argparse CLI) → `impl/runner.py` (launches `claude -p` subprocess per iteration)
- State: `impl/progress.py` reads/writes `.claude/*-progress.json` for cross-iteration persistence and `--resume` support
- Output: Each Claude session emits a `json:harness-output` block parsed by `harness_common.parser.parse_harness_output`
- Reporting: `impl/reporting.py` generates iteration summaries

### Key Patterns

- **Subprocess isolation** — each Claude iteration is a fresh `claude -p` process with no shared in-process state
- **Facade/re-export** — each `impl/` module imports from `harness_common` and re-exports, so callers use the harness-specific namespace
- **JSON progress protocol** — state persists across subprocess boundaries via a JSON file
- **stdlib only** — no pip dependencies beyond the standard library (dev deps are test/formatting tools only)

### Dependencies Between Modules

- `deep-mode-harness/impl/` → `harness_common` (constants, fixes, git, progress, reporting, runner)
- `test-coverage-harness/impl/` → `harness_common` (constants, git, progress, reporting, runner)
- `harness_common` is self-contained with no intra-project dependencies
- Harness-internal modules with no cross-module imports: `findings.py` (deep-mode), `convergence.py` (test-coverage)

## Skill Architecture

### Skill Organization

- 16 skills: brainstorm, branch, code-review, commit, commit-message, how-to-run, init, jira, permissions, pr, prompt, refactor, reset, tdd, unit-test, worktree
- Each directory contains `SKILL.md` (required) + `README.md` (required), with optional `agents/`, `references/`, `templates/` subdirectories

### Agent Boundaries

- **Plugin-level** (`agents/`): code-simplifier, test-guardian — available across all skills
- **Skill-level** (`skills/<name>/agents/`): scoped to the owning skill (e.g., code-review has 7 specialized agents, refactor has 4)
- Agents receive context via explicit prompt construction in SKILL.md, not implicit sharing

### Reference Hierarchy

- **Root** `references/`: agent-architecture, shared-agent-constraints, context-injection-blocks, harness-mode, coverage-harness-mode, scope-expansion-rule — cross-skill shared procedures
- **Skill-level** `references/`: supplemental docs scoped to one skill (e.g., `init/references/`, `pr/references/`)
- Maximum depth: SKILL.md → reference → sub-reference (two levels)

### Orchestration Patterns

- **Harness delegation** — skill detects deep-harness argument, reads `references/harness-mode.md`, builds CLI args, and hands off to the Python subprocess
- **Agent spawning** — SKILL.md instructs Claude to invoke named sub-agents for specialized review passes
- **JSON output protocol** — each Claude session emits structured `json:harness-output` blocks the orchestrator parses to decide continue/stop
- **User checkpoints** — skills use `AskUserQuestion` at decision points for confirmation before proceeding
