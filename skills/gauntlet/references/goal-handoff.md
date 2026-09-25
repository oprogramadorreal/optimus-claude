# /goal handoff

The user chose "Copy as /goal prompt": prepare the export, then stop, even
when the destination lacks native goals. Do not start a goal, dispatch
builders or critics, edit the product, commit, or change host settings in
this session. The progress document below is the handoff artifact, not an
execution milestone.

Use the current host unless the user requested another destination. Read
only that destination's sibling reference: [Claude Code](goal-handoff-claude.md)
or [Codex](goal-handoff-codex.md). Keep one shared gauntlet
prompt; the host reference adds only delivery and lifecycle instructions.

## Seed the progress page

Write `.claude/gauntlet-progress.md` with the goal, resolved bar, prompt,
concrete constraint-doc paths, test command when one exists, destination
host/model, and an empty piece/round/verdict table. Include the destination
reference's runtime instructions here. Use markdown even for visual work;
the lead can keep a rendered page beside it. Preserve an existing run's
history when resuming; for a different goal, use a distinct named markdown
handoff under `.claude/` instead of overwriting it, and use that path throughout.

Anything too bulky for the message lives here. The page and bar materials
must exist in the directory the new session opens — committed or copied
into the worktree by the user before pasting, if necessary. Resolve all
references now; the fresh session cannot rely on this conversation or the
preparing session's plugin-root variable.

## Build the message

Emit one paste-ready message starting with `/goal `. That prefix is the
delivery envelope; SKILL.md's ban on slash commands and effort keywords
still governs the body. Use the same gauntlet prompt just shown, not a
second implementation template. Add concrete repo paths and the test
command, an opening instruction to read the handoff page and verify that
the bar opens before dispatching work, the destination reference's message addition,
and the shared completion condition below as the final paragraph. If the
bar is inaccessible, report the blocker and follow the host's suspension
rules without claiming success.

The completion condition, in a few lines: every turn ends by showing the
progress page's piece/round/verdict table, the tail of test output with its
exit status, and the current branch with `git status --porcelain` output.
The goal is met ONLY when every piece in the nonempty table has a verdict
copied from its critic's own file whose final line reads exactly "beats the
bar", the integration critic's file says the same of the assembled whole,
the suite exits 0 on a feature branch whose porcelain status is clean, and
all of it is shown in the most recent turn. Verify those files and results;
the lead's own quality assessment never counts. No piece may be removed,
renamed, or merged to satisfy the condition; splitting is fine, with each
new piece starting without a verdict. An empty table never passes.

A plateau is not completion: report it and keep working on other actionable
pieces while the user decides. A host pause, blocker, usage or budget limit,
or user stop leaves an incomplete checkpoint, not a passing result. In a
testless project omit test clauses from both condition and evidence.

## Gate on a real count

Both hosts cap the objective — everything after `/goal ` — at 4,000
characters. Count the exact final body before printing: under 4,000 is the
gate, about 3,500 the target. A UTF-8 byte count is a conservative check:
use `wc -c` on a UTF-8 temp file under Bash, or
`[System.Text.Encoding]::UTF8.GetByteCount($goalBody)` under PowerShell.
Never count a retyped approximation or include the checklist in the body.

Over budget, remove repetitions, move supporting detail into the handoff
page, and tighten the host additions first. Condense the shared prompt only
as a last resort, retaining every guarantee. Keep the completion condition
in the message. Recount after every cut and print only a passing body.

## Print and stop

Above the message, identify the destination host/model and the handoff file,
then print that host's checklist. Use host-correct skill mentions in the
checklist. Make clear that pasting starts work in the destination session.
Then stop; the fresh session owns the run.
