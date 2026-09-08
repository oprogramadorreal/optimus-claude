---
description: >-
  Runs a Gauntlet Loop: turns an ambitious goal and optional quality references
  into a minimal builder/critic prompt judged against a concrete comparison
  bar, confirms with the user, then executes it as the lead agent until the
  output beats the bar or the user stops the run — or emits it as a
  paste-ready /goal prompt for a fresh session. Use for long-horizon goals
  judged against an inspectable reference. Long-running; spawns many
  subagents, edits project files, and commits finished pieces to a dedicated
  feature branch.
disable-model-invocation: true
argument-hint: "<goal> [possible references or quality bars]"
---

# Gauntlet

Turn an ambitious goal into a builder/critic improvement loop judged against a
concrete quality bar, and run that loop until the output wins or the user
stops it.

The user's arguments are the goal, plus any references or quality bars they
mentioned. If no goal was given, ask for one.

Gauntlet prompts are modeled on Matt Shumer's prompt for the Claude-of-Duty
game:

> I want you to build a first-person shooter at the level of the most recent
> Call of Duty games. It should be utterly perfect, visually beautiful, with
> every single thing done at AAA quality—from textures to physics to anything
> you could think of.
>
> Fan out sub-agents and have sub-agents tackle each one individually so that
> the game is utterly perfect. You should /loop on each item and have a
> separate sub-agent check it visually to ensure it looks triple A. That
> separate sub-agent should be a really harsh critic, and if it doesn't look
> triple A, it should keep going.
>
> Don't stop until each sub-agent is utterly wowed with the quality when
> compared with the actual Call of Duty game. It should literally compare them
> side by side blind and say which one looks better. Do this in ThreeJS. /loop
> until it's utterly perfect. Fan out sub-agents and ultracode.

Copy its register — short, concrete, goal-first, harsh about quality — not its
literal tokens. `/loop` and `ultracode` there are one user's shorthand typed
into a live session; as commands they mean something else entirely. Never
carry slash commands or effort keywords into the prompt you write.

## 1. Choose the bar

Choose the strongest concrete bar that an agent can actually inspect and
compare its work against. If the user has not supplied one, propose a useful
comp or measurement that plays the same role for this task that real Call of
Duty screenshots played for the Claude-of-Duty game.

Then resolve it into something a fresh agent with no prior context can open:
file paths, a URL, a command that renders it, or screenshots saved to disk. A
bar that cannot be resolved that way cannot be judged against — say so and fall
back to the strongest one that can. Explain the chosen bar in one sentence.

## 2. Write the gauntlet prompt

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/constraint-doc-loading.md`
and load the docs it lists. The bar defines what "good" means from outside;
these define what this project requires from inside. The prompt carries
both — the docs as repo paths.

Write a short prompt in that register (minimal is better here — the lead agent
decides the specifics).

Give the lead agent the goal and the bar, but let it choose the approach.
State the goal as a destination and do not enumerate its aspects, even when
the user did: a list of aspects in the goal sentence becomes the
decomposition, and that is the lead agent's call. Tell it to divide the goal
into the smallest pieces that can be improved and judged independently — a
piece is independent only if its builder can work without waiting on or
overwriting another builder's files; anything less is merged or sequenced
before the pieces are set. One builder takes each piece through every round:
it gets the critic's gap verbatim and chooses the fix, which the lead never
writes for it. Every round, a separate critic with fresh context judges the
piece.

Each piece's critic prompt is written once, before its first round, kept on
the progress page, and sent every round with only the artifact paths changed.
It carries the resolved bar materials themselves — the paths, URL, or
command — plus the artifact under judgment, and nothing from the builder: not
its report, its reasoning, or its round history. A critic that cannot open
the bar grades from memory, which is the builder-grades-itself failure this
loop exists to prevent. The lead agent is the other route to that failure,
because it reads every builder report and writes every critic prompt: so the
remit is never narrowed after a verdict, what a builder found reaches a
critic only as a file it can open and measure — never as a conclusion or an
exclusion — and a verdict the lead disputes goes to the user as a
disagreement, not back to the critic as a new rule.

Critics judge the artifact as a user would meet it — run, rendered, executed —
never the builder's summary, and never source review alone when the work is
visual or behavioral. Anything presented as computed — metrics, simulation
output, live data — must trace to real computation: staged output that merely
looks right is a gap, not a pass.

Each critic compares ours against the bar unlabeled — blind A/B when the
artifacts allow it, side by side otherwise; never an older and a newer
version of our own work, which measures the round, not the bar — and writes
its verdict to its own file under `.claude/gauntlet/`, named by piece and
round, ending with one of two final lines: exactly **beats the bar**, or the
single biggest remaining gap, which goes back for another round. A gap is a
way the bar beats ours; checks the bar cannot show — interaction,
robustness, window sizes — belong in the remit from round one or in the test
suite, never added round by round. The progress page copies every verdict
from its file. A piece is done when its critic's file reads *beats the bar*.

Pieces that individually beat the bar can still disagree with each other, so
when every piece is done, a fresh integration critic judges the assembled
whole against the same bar, and any gap it names goes back for another round,
judged again by a fresh integration critic. The run ends when the integration
critic returns *beats the bar* or when the user stops it — and in practice it
is usually the second. Never end it on your own: if a piece's last two rounds
close no gap its critic can still name, report the plateau to the user and
let them decide whether it is worth more compute. Stopping is their call, not
yours.

If the project has a test command, the suite stays green: a piece is not done
while its tests fail.

The run never touches the default branch: before the first edit, the lead
agent creates and switches to a descriptively named feature branch (a
worktree made at confirmation already is one). Each piece is committed, with
its verdict files and the progress page, when its critic returns *beats the
bar* and the suite is green — focused commits at judged milestones, never
one giant commit at the end — and the run never pushes, merges, or opens a
PR unless the user asked for it.

Have the lead agent maintain a simple live progress page that shows the work
evolving over time — a rendered HTML page when the work is visual, markdown
otherwise — at `.claude/gauntlet-progress.html` or `.md`. Keep the goal, the
resolved bar, this prompt, every piece's critic prompt, and every piece's
rounds and verdicts in it, and write it before dispatching each round, so it
doubles as the anchor a later session resumes from.

Do not prescribe the architecture, exact decomposition, or a fixed number of
rounds. Keep the prompt short, but short is a budget for phrasing, not licence
to drop guarantees: one builder per piece, fresh-context critics, the frozen
remit, the bar materials in every critic prompt, ours-against-the-bar
comparison, the verdict file with its two-way final line, judging the
running artifact, the anti-staging rule, the integration critic, and the
branch-and-commit rules all survive to the final draft. Short also has a
number: keep the prompt under 2,500 characters, because the /goal handoff
must fit this exact prompt plus an opening instruction and a completion
condition into /goal's 4,000-character message cap, and those need the rest.

## 3. Confirm and run

Show the user the bar and the prompt. Under Claude Code, recommend ultracode
for serious runs (`/effort` → ultracode): set it before approving "Start the run",
because the run starts immediately after, or in the fresh session for "Copy as /goal prompt".

Run `git status --porcelain`. If it reports anything, say so before asking:
this run rewrites the same files for hours with no per-change approval, and
uncommitted work will not survive it. Offer `/optimus:worktree` or committing
first — on the handoff path, before pasting: the danger window is the future
session, not this one.

Then use `AskUserQuestion` — header "Gauntlet", question confirming the start
of a long-running multi-agent run that spawns many subagents, edits files
without per-change approval, and consumes credits in proportion to how long it
runs — with options "Start the run", "Adjust first", "Copy as /goal prompt",
and "Cancel". Under Codex, omit "Copy as /goal prompt"; that handoff is Claude-only.
Apply requested adjustments and ask again. On "Cancel", stop.
On "Copy as /goal prompt", read
`$CLAUDE_PLUGIN_ROOT/skills/gauntlet/references/goal-handoff.md` and follow
it: the run is handed to a fresh session instead of executed here.

On "Start the run", execute the prompt yourself as the lead agent. There is no
arbitrary final round: the run ends when the output beats the bar or when the
user stops it.

Close on the outcome — uncommitted work → `/optimus:commit`; already committed
→ `/optimus:pr`, then `/optimus:code-review` in a fresh conversation — and say
plainly whether the run beat the bar, plateaued, or was interrupted, and
whether the suite is green.
