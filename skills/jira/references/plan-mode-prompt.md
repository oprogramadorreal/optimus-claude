# Medium path: plan-mode prompt

Read `$CLAUDE_PLUGIN_ROOT/skills/brainstorm/references/plan-mode-handoff.md` — this route ends in `/optimus:tdd`, so the review-only carve-out applies.

Emit that reference's **Prompt skeleton** as a copyable plan-mode prompt, with `<doc-path>` = `docs/jira/<ISSUE-KEY>.md` and `<ISSUE-KEY>` substituted for the real key. Fill it from the structured task:

- **Goal** — from the structured task
- **Context** — acceptance criteria, context fields, key decisions; plus Files Affected and Risks from Step 5 when available
- **Starting Hints** — the task file, plus key files from the impact summary
- **Scope** — the focus area, and anything the JIRA issue excludes

Close it with the carve-out's `## How this conversation should run` block. Then give the user that reference's handoff steps for the current host — the carve-out's three numbered steps in Claude Code, the **Codex handoff** branch under Codex — and emit the execution prompt as a second copyable block from the same skeleton, carrying the acceptance criteria forward into Starting Hints.
