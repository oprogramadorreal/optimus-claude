# Architecture

## Overview

A Claude Code plugin: markdown skills invoked via `/optimus:<name>`, two
plugin-level quality agents, a SessionStart hook, and a Python CLI under
`scripts/harness_common/` that the `/optimus:deep` orchestrator uses for state,
tests, bisection, and checkpoint commits.

## Directory Map

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Plugin manifests (plugin.json, marketplace.json) |
| `agents/` | Plugin-level agent definitions (code-simplifier, test-guardian) |
| `hooks/` | Plugin-level hooks (SessionStart for project state awareness) |
| `references/` | Shared reference docs consumed by multiple skills |
| `skills/<name>/` | One directory per skill (SKILL.md + README.md + optional agents/, references/, templates/) |
| `scripts/harness_common/` | Orchestrator CLI (`cli.py`) + shared modules invoked by `/optimus:deep` |
| `scripts/` | validate.sh, test-hooks.sh, test-skills.sh, generate-fixtures.sh |
| `test/harness-common/` | pytest suite for the CLI and shared modules |

## Skill Architecture

Skills (see the root README for user-facing descriptions): `init`, `spec`,
`tdd`, `unit-test`, `refactor`, `code-review`, `deep`, `reset`. Each directory
contains `SKILL.md` (required) + `README.md` (required), with optional
`agents/`, `references/`, `templates/` subdirectories.

- **Agent boundaries** — plugin-level agents (`agents/`) define reusable quality
  concerns; skill-level agents (`skills/<name>/agents/`) scope them to one
  skill's workflow. See `references/agent-architecture.md` for the two-tier
  design and the prompt-assembly rule.
- **Reference hierarchy** — root `references/` holds cross-skill procedures
  (harness protocols, loop template, shared agent constraints); skill-level
  `references/` hold single-skill detail. Cross-skill references owned by init
  (`multi-repo-detection.md`, `constraint-doc-loading.md`,
  `verification-protocol.md`, `prerequisite-check.md`) keep stable paths.
  Maximum reference depth from a SKILL.md is two levels (validated).
- **Cross-skill data contract** — `/optimus:spec` writes specs to `docs/specs/`
  whose `## Scenarios` / `### Scenario:` headings `/optimus:tdd` consumes
  directly as its behavior list (pinned by `scripts/validate.sh`).

## Orchestrator Data Flow (/optimus:deep)

- The skill runs in the user's conversation and invokes
  `python -m harness_common.cli init` to create a JSON progress file
  (`.claude/<base-skill>-deep-progress.json`), passing `--test-command`
  explicitly (the CLI requires it), then enters the loop defined in
  `references/orchestrator-loop.md`.
- Each iteration (review/refactor modes) or cycle (coverage mode):
  1. `cli snapshot` records the pre-iteration git HEAD (plus a working-tree
     stash in no-commit mode).
  2. The base skill (`code-review`, `refactor`, or `unit-test`) is dispatched
     as a fresh `general-purpose` subagent. The prompt carries
     `HARNESS_MODE_INLINE`, the absolute progress-file path, and an instruction
     to read the base SKILL.md and follow `references/harness-mode.md` (or
     `coverage-harness-mode.md` for the unit-test phase).
  3. The subagent emits a `json:harness-output` fenced block; the orchestrator
     saves it verbatim to a temp file and runs `cli parse`.
  4. `cli deep-step` (or `refactor-step` / `unit-test-step`) applies fixes,
     runs tests, bisects on failure, and updates statuses; the coverage
     variant rolls the whole cycle back if the suite is red. Bisection always
     rebuilds each candidate from the git snapshot (`fixes.py`) — recorded
     edit content is never trusted as revert data, so a corrupt record can
     only fail loudly as `skipped`, never tear the tree.
  5. `cli commit-checkpoint` produces a per-iteration commit (self-skips in
     no-commit mode; a failed commit durably disables commits and switches to
     stash snapshots).
  6. `cli check-termination` returns one of
     `continue | convergence | no-actionable | all-reverted | cap |
     diminishing-returns | parse-failure`; the loop repeats on `continue`.
- `cli final-report --archive` prints the cumulative report and archives the
  progress file to `.done.json` (except after a `diminishing-returns`
  soft-exit, which stays resumable via `--resume`).

## Key Patterns

- **Subagent isolation** — each iteration runs in a fresh subagent context; the
  orchestrator sees only the terse JSON return, never the analysis trace.
- **File-based state** — all cross-iteration state lives in the progress file;
  the orchestrator never holds findings in conversation prose.
- **stdlib only** — no pip dependencies beyond the standard library (dev deps
  are test/formatting tools only).
- **UTF-8 pinned I/O** — every text-mode subprocess call passes
  `encoding="utf-8", errors="replace"` (never the locale codec — on cp1252
  Windows a bare `text=True` silently loses child output on the first
  non-decodable byte), and `cli.main()` reconfigures its own stdout/stderr to
  UTF-8. Enforced by `test/harness-common/test_encoding_policy.py`.

## Module Dependencies

- `harness_common/cli.py` → all sibling modules (`findings`, `convergence`,
  `fixes`, `git`, `parser`, `progress`, `runner`, `reporting`, `constants`).
- `harness_common` is otherwise self-contained with no intra-project
  dependencies.
