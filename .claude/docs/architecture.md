# Architecture

A Claude Code plugin whose skills are markdown, plus one orchestrator skill (`deep`) that dispatches base skills into fresh subagent contexts and drives them with a stdlib-only Python CLI under `scripts/harness_common/`.

The directory layout is discoverable; what follows is what reading it does not tell you.

## The deep loop

`references/orchestrator-loop-single.md` and `-paired.md` are the executable spec for the per-iteration body, and `references/schemas/*.schema.json` is the JSON contract. Those files are the definition — this doc does not restate the step sequence. The invariants they depend on but do not explain:

- **The bisect rebuilds each candidate state from the pre-iteration git snapshot**, never from the reported `pre_edit_content`/`post_edit_content`. A corrupt record can then only fail loudly as `skipped`; it can never tear the working tree.
- **`record-cycle` runs before `check-termination`** on the coverage target, because it pre-increments `cycle.current` and the cap check reads it. Swapping them silently runs one cycle too many.
- **The two soft exits are not archived.** `diminishing-returns` and `blocked` (the coverage target's stop gate) stay resumable on purpose; every other termination reason moves the progress file to `.done.json` so a stray `--resume` cannot reopen a finished run. The set is `RESUMABLE_TERMINATIONS` in `scripts/harness_common/constants.py` — one name, consumed by `cmd_final_report`, so narrowing this back to a single reason breaks the `--resume` each skill's SKILL.md promises.
- **All cross-iteration state lives in the progress file.** The orchestrator sees the subagent's terse JSON return, never its analysis trace — that is what keeps the loop from being bounded by one conversation's context.

## Contracts that fail loudly

- `references/schemas/` holds the harness JSON contracts. `test/harness-common/test_harness_schema.py` validates the golden fixtures under `test/harness-common/fixtures/` against them, round-trips them through `cli parse`, and checks that the harness-mode docs still point at both — change a schema and it fails until the fixtures follow.
- Every text-mode subprocess call passes `encoding="utf-8", errors="replace"`. A bare `text=True` uses the locale codec, which on a cp1252 Windows box silently truncates child output at the first non-decodable byte. `cli.main()` reconfigures its own stdout/stderr for the same reason. Enforced by `test/harness-common/test_encoding_policy.py`.
- `scripts/validate.sh` section 17 pins only strings a program parses or that cross a conversation boundary. Adding a pin for a heading one file reads from another is the anti-pattern that section exists to have removed.

## Agents and references

Two tiers, no inheritance: `agents/` holds standalone user-invocable agents, and `skills/<name>/agents/` holds prompt files scoped to one skill, each carrying its criteria inline. `deep` owns none — it dispatches base skills, which own the analysis agents. The dispatch-time path-substitution rule is in `references/agent-architecture.md`; the rest of the authoring rules are in `.claude/docs/skill-writing-guidelines.md`, which `validate.sh` enforces the two-level reference depth cap for.

## Two hosts, one plugin

OpenAI Codex loads this plugin through the Claude Code files: it accepts `.claude-plugin/plugin.json` as a legacy manifest, reads `.agents/plugins/marketplace.json` (installing from `./`), and runs `hooks/hooks.json` with `CLAUDE_PLUGIN_ROOT` set. What the layout does not tell you:

- **`hooks/session-start` is the only host-aware code.** It detects Codex by `PLUGIN_ROOT` being set and equal to `CLAUDE_PLUGIN_ROOT` (Codex sets both, Claude Code only the latter), switches its skill mentions to `$optimus:`, supplies the plugin root and question mapping, and states the unsupported Claude features. This extra context is emitted only under Codex. Absolute paths let shared agent prompts be used with either host's subagent tools; execution compatibility still needs the contributor smoke test.
- **`skills/*/agents/openai.yaml` is metadata, not an agent.** It carries Codex's `allow_implicit_invocation: false`, the twin of `disable-model-invocation: true`; the prompt files beside it are unrelated to it.
- **The hook command in `hooks/hooks.json` is bash-first with a git fallback.** Claude Code keeps its direct Bash launch. Codex runs Windows hooks through `cmd.exe`, where Git for Windows may expose only `Git\cmd`, so the fallback uses Git's bundled shell. Claude Code's schema rejects unknown keys, ruling out `commandWindows`; the alias body carries no POSIX path lists or `$` expansions that MSYS might rewrite. Git starts shell aliases at the repository root: `--git-alias` tells the hook to restore the caller's directory using `GIT_PREFIX` before inspecting project state. Normal launches ignore that variable.
- **Claude Code-only by design:** `permissions`, `dream`, init's formatter hooks, Claude `/goal` and `/workflows` handoffs, and the two plugin-level agents. Claude-specific plan-mode handoffs need manual adaptation. The README's support matrix is the user-facing list — extend it before extending the code.
