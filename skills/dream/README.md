# optimus:dream

Prunes and consolidates your project's Claude Code auto-memory. Named after Claude Code's internal "dream" memory-consolidation pass, but inverted: where a dream normally also captures new memories, this skill only removes, merges, and tightens.

Claude Code loads a bounded memory index at startup and retrieves detailed memory files on demand. Wrong entries can steer sessions astray, and overlapping ones make useful information harder to find. `/optimus:dream` keeps the index and supporting files focused while preserving valuable details that future tasks may retrieve.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Type `/optimus:dream` in a project where Claude Code auto-memory is enabled. Pass an optional focus to narrow the pass, e.g. `/optimus:dream the deploy notes`.

Claude Code only. In Codex, this skill stops without reading or changing memory; use Codex's own memory controls instead.

## How It Works

1. **Inventory** — reads every memory file and the index; records the baseline footprint (file count, bytes).
2. **Judge** — each memory gets one verdict, tested against a concrete bar: *what future-session decision would this change?*
   - **Delete** — disproven by the current codebase, superseded, cheaply re-derivable from the repo, or tied to work that's done
   - **Merge** — overlapping entries folded into one file
   - **Shrink** — the fact stays, the padding goes
   - **Keep** — earns its place as-is

   The index is judged too: dangling or drifted lines, and any content that doesn't belong in an index.
3. **Confirm** — presents the full plan with per-file reasons and the projected footprint, and asks before changing anything.
4. **Execute** — snapshots the store into the session scratchpad, re-checks for memories written while the plan awaited approval (those are kept, unjudged), then merges, shrinks, and deletes; syncs frontmatter, fixes cross-links, and rebuilds the index.
5. **Report** — re-lists the store to verify the file count against the baseline, then reports the footprint before → after.

## Guarantees

- **Never creates a new memory file** and never stores a new fact — the file count can only stay flat or shrink.
- **Always asks before deleting.** Memory files are not git-tracked, so nothing is removed without your approval — and a snapshot is copied into the session scratchpad before execution as a last-resort undo.
- **Touches nothing outside the memory directory and its index.** Session transcripts may be grepped, narrowly, as evidence that a memory is stale — never modified; the store's `logs/` and `sessions/` activity streams are not read at all.
- **Treats memory content as data, never as instructions.** Text inside a memory that tells the agent what to do is judged like any other content — a poisoned or self-protecting entry is a deletion candidate, not a directive.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 2.x with auto-memory enabled for the project — auto-memory does not exist on 1.x releases

## License

[MIT](../../LICENSE)
