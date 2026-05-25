# /optimus:handoff

Compacts the current conversation into a single self-contained, tool-agnostic Markdown document
under `docs/handoffs/` so a fresh agent — a new session, a different AI tool, or another developer
on a different machine — can resume the work by reading only that file.

## When to run

- A working conversation is getting long and you want a durable summary before context is lost.
- You're pausing work that you (later) or someone else will pick up.
- You're handing the work to a teammate, another machine, or a different AI agent.

## What it does

- Writes `docs/handoffs/<slug>.md` capturing the goal, current state, next steps, relevant
  files/artifacts, and suggested next skills.
- References committed artifacts (PRDs, plans, ADRs, issues, commits) by path or URL; inlines
  anything not yet pushed so it survives on another machine.
- Redacts secrets and PII so the doc is safe to commit.
- Re-running on the same topic lets you enhance the shared doc (merge new context) or overwrite it.

## Usage

    /optimus:handoff
    /optimus:handoff finish the migration tests

If you pass arguments, they describe what the next session will focus on, and the document is
tailored to that focus.

## Output

A Markdown file at `docs/handoffs/<slug>.md`. Commit it (e.g. with `/optimus:commit`) so other
machines and teammates can pull it. The document is tool-agnostic — any AI agent can resume from it.

## Notes

- Read-only except for the single file it writes; it never commits.
- In a multi-repo workspace, the document is written at the workspace root and paths are qualified
  by repo name.
