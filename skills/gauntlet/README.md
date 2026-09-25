# optimus:gauntlet

A skill for Claude Code and, experimentally, Codex that runs a **[Gauntlet Loop](https://somethingbig.ai/gauntlet-loop)**: give it an ambitious goal, and it turns that goal into a builder/critic improvement loop judged against a concrete quality bar. It keeps working toward that bar until it passes, you stop, or the host suspends execution.

Instead of producing one decent result and stopping, the agent must keep comparing its work against a much higher standard that it cannot talk its way around.

## How It Works

1. **Choose the bar** — picks the strongest concrete reference an agent can actually inspect and compare its work against: real screenshots, a reference implementation, a test suite, best-in-class examples. If you supplied references, it uses the strongest; otherwise it proposes one. The bar is then resolved into something a fresh agent can actually open — paths, a URL, a command, or saved screenshots — since critics start with no context.
2. **Write the gauntlet prompt** — a short, minimal prompt in the register of the Claude-of-Duty exemplar: the goal and the bar, plus your project's own constraint docs, with the approach, decomposition, and round count left to the lead agent.
3. **Confirm** — shows you the bar and prompt, warns if your working tree has uncommitted changes, and offers **Start the run**, **Adjust first**, **Copy as /goal prompt**, and **Cancel** in both hosts. Copy seeds the progress page and prints a prompt for a fresh session, with the shared gauntlet protocol, completion evidence, and the destination host's goal instructions. It does not create a goal or dispatch builders in the preparing session. The independent critics remain the judges; the host's goal mechanism continues work across turns.
4. **Run** — the lead agent divides the goal into the smallest pieces that can be improved and judged independently. Each piece gets one builder that carries it through every round and, every round, a new critic with fresh context, whose prompt is written once for the piece and never narrowed after a verdict. The critic inspects the real output — running or rendered, not the builder's summary, and never a source read alone for visual or behavioral work — compares it against the bar unlabeled (blind A/B where the artifacts allow it) and writes its verdict to its own file under `.claude/gauntlet/`: either *beats the bar* or the single biggest remaining gap, a way the bar beats ours, which goes back to the builder verbatim for another round. The run stays off your default branch: work happens on a dedicated feature branch, and each piece is committed and pushed when its critic passes it with green tests. When every piece is done, a final fresh critic judges the assembled whole against the bar before the run closes. A live progress page at `.claude/gauntlet-progress.html` (or `.md`) shows the work evolving and doubles as the anchor a later session resumes from.

## Principles

- **Goal over implementation** — you say what you want; the agent chooses how to make it.
- **A real bar** — "make it amazing" is not a bar; a concrete, inspectable reference is.
- **Agent-chosen decomposition** — the lead agent splits the work, not you: the prompt names the destination, not its parts, and a piece counts as independent only if its builder never waits on or overwrites another builder's files.
- **Never let the builder grade itself** — critics get fresh context and the actual artifact, never the builder's history or explanation. They judge the work running, and anything presented as computed must trace to real computation — staged output that merely looks right doesn't pass. The lead agent is held to the same rule: it never narrows a critic's remit after a verdict, passes a builder's findings on only as files a critic can open and measure, and brings a verdict it disputes to you rather than back to the critic as a new rule.
- **No fixed round count** — a plateau is reported, never relabeled as a pass. The agent continues useful work within your authorization and the host's limits; if execution stops before the bar is met, it preserves the unresolved work for resumption.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

Under Codex, invoke `$optimus:gauntlet`. Both in-session execution and **Copy as /goal prompt** are offered; the full builder/critic workflow remains experimental and needs native smoke testing. Claude Code's `/effort` → ultracode setting does not apply. Select GPT-6 Astra (`gpt-6-astra`) in the destination if that is your intended model; see the [Codex support matrix](../../README.md#using-with-openai-codex).

## Usage

- `/optimus:gauntlet <goal>` — proposes a bar, writes the prompt, confirms, runs
- `/optimus:gauntlet <goal> [possible references or quality bars]` — considers your references when choosing the bar
- At the confirmation step, choose **Copy as /goal prompt** for a fresh conversation. The skill seeds `.claude/gauntlet-progress.md`, prints the host-specific handoff, and stops. Choosing **Start the run** instead runs the ordinary in-session lead; it does not implicitly activate a native Codex goal.

Examples:

```
/optimus:gauntlet finish porting all the BUILDING tools; match the desktop app's behavior as closely as possible and compare your work against the desktop app as you go
```

```
/optimus:gauntlet build a landing page for the product — the best landing pages in our category are the quality bar
```

For serious Claude Code runs, enable ultracode first (`/effort` → ultracode). In either host, consider isolating the run in a worktree (`/optimus:worktree`, or `$optimus:worktree` in Codex).

## Fresh-session goals

Copy exports the same loop protocol for both hosts, with different goal setup and controls. Open the new session in the directory containing the progress page, bar materials, and project guidance. The handoff records these paths because the destination has no conversation history. Choose the model and host permissions before pasting; the launch prompt starts work. It uses one goal for the entire gauntlet, not one goal per round or worker.

| Destination | Goal behavior and controls |
|---|---|
| Claude Code | The `/goal` message starts work immediately. A separate evaluator checks evidence surfaced in the transcript; critics still judge the artifacts. Bare `/goal` shows status, `/goal clear` cancels. The checklist includes Claude's trust/hooks prerequisites and `/effort` → ultracode. |
| Codex, including Astra | The handoff uses native `/goal` where available, or explicitly requests the destination's exposed goal tools. Bare `/goal` shows status; `/goal edit`, `/goal pause`, `/goal resume`, and `/goal clear` control the goal where supported. The lead verifies the completion evidence before marking the goal complete. No Claude evaluator, ultracode setting, or Claude hook prerequisite is assumed. |
| Codex without native goals | Copy still exports the native goal prompt for a capable destination. The checklist explains setup and offers a separately labeled plain continuation fallback using the same protocol and resume files; that fallback cannot guarantee automatic continuation across turns. |

The exported objective is checked against the 4,000-character limit shared by both hosts. Longer details remain in the progress document and are referenced by the launch prompt. Copy may write this preparation state, but does not start workers, create a feature branch, or create/update an active goal. It preserves any existing run's progress rather than silently overwriting it.

Passing requires a nonempty piece table with independent passing verdicts, a passing final integration verdict, the applicable green tests, and the required commits on a clean feature branch. Plateau, blockage, interruption, and budget exhaustion are incomplete outcomes. In Codex, the destination follows its exposed goal tools' completion/blockage rules and sets a token budget only if you explicitly requested one.

On resumption, the lead reads progress, verdicts, tests, and Git state before continuing. It recreates workers from these files when necessary; private worker context does not transfer to a new session. Codex critics need a fresh context each round (for example, `fork_turns: "none"` when that option is exposed), with the fixed remit and artifact paths rather than builder history.

Documented host behavior: [Claude goals](https://code.claude.com/docs/en/goal), [Codex goals](https://learn.chatgpt.com/use-cases/follow-goals), [Codex goal commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli#set-or-view-a-task-goal-with-goal), and [Codex long-running work](https://learn.chatgpt.com/docs/long-running-work). Implemented handoff support is separate from a validated execution run; the [manual acceptance checks](../../CONTRIBUTING.md#gauntlet-goal-handoff-manual) track the remaining evidence.

## Cost

Gauntlet is the most expensive skill in the plugin and the only one with no round cap. Every round the piece's work is judged by a freshly spawned critic, so credit and time consumption scale with how long you let it run. Fixes are applied without per-change approval, and finished pieces are committed and pushed to the run's feature branch as they pass, so hours of work survive off your machine. The run never touches your default branch or force-pushes, and a failed push doesn't stop it; opening the PR is left to `/optimus:pr` at the end. Tell it not to push if you'd rather keep the branch local.

The skill confirms before starting, warns if your working tree is dirty, and offers **Cancel**. The progress page holds the goal, resolved bar, prompt, and each piece's round history so a later session can resume. To bound the work up front, narrow the goal at confirmation; any explicit budget or stop condition must remain distinct from passing the bar.

Native goals can continue spending across turns without another prompt. An interrupt can stop the current turn while leaving the goal set; use the destination's goal controls above to pause or clear it. Goals do not change permissions or guarantee uninterrupted execution: approvals, unavailable tools, host errors, usage limits, and genuine blockers can suspend or end a run. Claude can also clear a goal it judges impossible or pause for nonprogress. Preserve the progress files and inspect the reported reason before resuming.

## When to Use

- Long-horizon build, port, or polish goals where "done" means matching a reference
- Work whose output can be inspected and compared: UIs, games, ports, writing, designs, backends with a reference implementation or test-suite bar

## When NOT to Use

- **Fixing existing code toward internal standards** — use `/optimus:deep` (review | refactor | coverage), the deterministic resumable fix loop
- **Lightweight "work until a condition holds"** — use the host's native goal on its own, with no builder/critic protocol (gauntlet's **Copy as /goal prompt** option delivers the full protocol)
- **Small, well-specified tasks** — `/optimus:tdd` or a plain prompt is cheaper

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition |
| `references/goal-handoff.md` | The **Copy as /goal prompt** path — shared seeding, completion evidence, and message-size check; read only when that option is chosen |
| `references/goal-handoff-claude.md` | Claude goal delivery, evaluator behavior, and destination checklist |
| `references/goal-handoff-codex.md` | Codex goal lifecycle, native-tool/plain-prompt fallback, and destination checklist |
| *(shared)* `init/references/constraint-doc-loading.md` | Project constraint docs carried into the gauntlet prompt |

## Acknowledgements

The Gauntlet Loop method — an ambitious goal, a concrete reference bar, and builder/critic pairs with fresh context that loop until the output beats the bar — comes from [The Gauntlet Loop](https://somethingbig.ai/gauntlet-loop) by Matt Shumer, as does the Claude-of-Duty exemplar the generated prompt is modeled on. This skill adds bar resolution to on-disk materials, project constraint docs, a dirty-tree warning with confirmation, a resumable progress page, and host-specific goal handoffs for fresh-session runs.

## Requirements

- Optimus installed in a [supported host](../../README.md#supported-hosts-and-versions)
- For the native Claude goal handoff: Claude Code 2.1.139+ with the trust dialog accepted and hooks enabled
- For the native Codex goal handoff: a destination surface exposing `/goal` or native goal tools; otherwise use the labeled plain-prompt fallback
- Subagent support with independent critic contexts; ultracode recommended for serious Claude runs, not a Codex prerequisite

## License

[MIT](../../LICENSE)
