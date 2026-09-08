# optimus:gauntlet

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that runs a **[Gauntlet Loop](https://somethingbig.ai/gauntlet-loop)**: give it an ambitious goal, and it turns that goal into a builder/critic improvement loop judged against a concrete quality bar — then keeps looping until the output beats the bar or you stop the run.

Instead of producing one decent result and stopping, the agent must keep comparing its work against a much higher standard that it cannot talk its way around.

## How It Works

1. **Choose the bar** — picks the strongest concrete reference an agent can actually inspect and compare its work against: real screenshots, a reference implementation, a test suite, best-in-class examples. If you supplied references, it uses the strongest; otherwise it proposes one. The bar is then resolved into something a fresh agent can actually open — paths, a URL, a command, or saved screenshots — since critics start with no context.
2. **Write the gauntlet prompt** — a short, minimal prompt in the register of the Claude-of-Duty exemplar: the goal and the bar, plus your project's own constraint docs, with the approach, decomposition, and round count left to the lead agent.
3. **Confirm** — shows you the bar and the prompt, warns if your working tree has uncommitted changes, and asks for confirmation (with **Cancel**) before starting, since gauntlet runs are long and spawn many subagents. A fourth option, **Copy as /goal prompt**, skips execution: the skill seeds the progress page, then prints the same prompt as one paste-ready [`/goal`](https://code.claude.com/docs/en/goal) message for a fresh session — the prompt plus a transcript-verifiable completion condition, with a checklist of the manual steps the new session needs. The critics remain the judges; `/goal`'s per-turn evaluator only keeps that session alive until their verdicts and green tests have been shown in the conversation.
4. **Run** — the lead agent divides the goal into the smallest pieces that can be improved and judged independently. Each piece gets one builder that carries it through every round and, every round, a new critic with fresh context, whose prompt is written once for the piece and never narrowed after a verdict. The critic inspects the real output — running or rendered, not the builder's summary, and never a source read alone for visual or behavioral work — compares it against the bar unlabeled (blind A/B where the artifacts allow it) and writes its verdict to its own file under `.claude/gauntlet/`: either *beats the bar* or the single biggest remaining gap, a way the bar beats ours, which goes back to the builder verbatim for another round. The run stays off your default branch: work happens on a dedicated feature branch, and each piece is committed when its critic passes it with green tests. When every piece is done, a final fresh critic judges the assembled whole against the bar before the run closes. A live progress page at `.claude/gauntlet-progress.html` (or `.md`) shows the work evolving and doubles as the anchor a later session resumes from.

## Principles

- **Goal over implementation** — you say what you want; the agent chooses how to make it.
- **A real bar** — "make it amazing" is not a bar; a concrete, inspectable reference is.
- **Agent-chosen decomposition** — the lead agent splits the work, not you: the prompt names the destination, not its parts, and a piece counts as independent only if its builder never waits on or overwrites another builder's files.
- **Never let the builder grade itself** — critics get fresh context and the actual artifact, never the builder's history or explanation. They judge the work running, and anything presented as computed must trace to real computation — staged output that merely looks right doesn't pass. The lead agent is held to the same rule: it never narrows a critic's remit after a verdict, passes a builder's findings on only as files a critic can open and measure, and brings a verdict it disputes to you rather than back to the critic as a new rule.
- **No fixed round count** — the loop ends when the output wins or when you stop it; in practice, usually the second. If a piece plateaus, the agent reports it and you decide whether it is worth more compute.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

Under Codex, the in-session lead-agent path is experimental; agent execution still needs native smoke testing. Claude Code's `/effort` → ultracode setting and **Copy as /goal prompt** handoff do not apply; see the [Codex support matrix](../../README.md#using-with-openai-codex).

## Usage

- `/optimus:gauntlet <goal>` — proposes a bar, writes the prompt, confirms, runs
- `/optimus:gauntlet <goal> [possible references or quality bars]` — considers your references when choosing the bar
- At the confirmation step, choose **Copy as /goal prompt** to run the gauntlet in a fresh conversation instead: the skill seeds `.claude/gauntlet-progress.md`, prints one message starting with `/goal`, and stops. In the new session — opened in the directory that holds the progress page and bar materials — set `/effort` → ultracode and pick a permission mode **before** pasting; pasting starts the run immediately. Stop it with `/goal clear` (Esc only interrupts the current turn); bare `/goal` shows turn and token spend.

Examples:

```
/optimus:gauntlet finish porting all the BUILDING tools; match the desktop app's behavior as closely as possible and compare your work against the desktop app as you go
```

```
/optimus:gauntlet build a landing page for the product — the best landing pages in our category are the quality bar
```

For serious runs, enable ultracode first (`/effort` → ultracode) and consider isolating the run in a worktree (`/optimus:worktree`).

## Cost

Gauntlet is the most expensive skill in the plugin and the only one with no round cap. Every round the piece's work is judged by a freshly spawned critic, so credit and time consumption scale with how long you let it run. Fixes are applied without per-change approval, and finished pieces are committed to the run's feature branch as they pass — the run never pushes, merges, or opens a PR on its own.

The skill confirms before starting, warns if your working tree is dirty, and offers **Cancel**. Once running, press Esc to stop — the progress page holds the goal, the resolved bar, the prompt, and every piece's round history, so a later session can pick the run back up. To bound a run up front, narrow the goal at the confirmation step.

The **Copy as /goal prompt** path is unattended-leaning: `/goal` re-prompts the agent after every turn until the completion condition holds, and a plateaued run never auto-stops — you stop it with `/goal clear`. A goal does not change permissions, so choose a permission mode in the fresh session deliberately: without auto-accept the run stalls at its first prompt; with it, nothing interrupts spending. The per-turn evaluator's own cost is negligible; the run itself is the same open-ended builder/critic loop as the in-session path.

## When to Use

- Long-horizon build, port, or polish goals where "done" means matching a reference
- Work whose output can be inspected and compared: UIs, games, ports, writing, designs, backends with a reference implementation or test-suite bar

## When NOT to Use

- **Fixing existing code toward internal standards** — use `/optimus:deep` (review | refactor | coverage), the deterministic resumable fix loop
- **Lightweight "work until a condition holds"** — Claude Code's native `/goal` on its own, with no builder/critic protocol (gauntlet's **Copy as /goal prompt** option is the reverse: the full protocol delivered through `/goal`)
- **Small, well-specified tasks** — `/optimus:tdd` or a plain prompt is cheaper

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition |
| `references/goal-handoff.md` | The **Copy as /goal prompt** path — seeding, message build, completion condition, user checklist; read only when that option is chosen |

## Acknowledgements

The Gauntlet Loop method — an ambitious goal, a concrete reference bar, and builder/critic pairs with fresh context that loop until the output beats the bar — comes from [The Gauntlet Loop](https://somethingbig.ai/gauntlet-loop) by Matt Shumer, as does the Claude-of-Duty exemplar the generated prompt is modeled on. This skill adapts his meta-prompt workflow into a Claude Code command, adding bar resolution to on-disk materials, project constraint docs, a dirty-tree warning with a confirmation step, a resumable progress page, and an optional `/goal` handoff for fresh-session runs.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Claude Code 2.1.139+ with the trust dialog accepted and hooks enabled — only for the **Copy as /goal prompt** option
- Subagent support; ultracode recommended for serious runs

## License

[MIT](../../LICENSE)
