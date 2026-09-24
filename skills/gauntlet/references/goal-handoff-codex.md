# Codex goal handoff

Use this only for a Codex destination. Shared export, completion, and size
rules live in the calling `goal-handoff.md` reference. Preserve a requested
model such as GPT-6 Astra (`gpt-6-astra`); do not choose a substitute.

## Opening instruction

Add a compact instruction to use one native Codex goal for the entire run,
following the runtime instructions in the handoff page, and to mark it
complete only after verifying the shared completion evidence. Do not carry
Claude's small-evaluator assumptions or ultracode recommendation into it.

## Runtime instructions

Include these in the handoff page for the destination lead:

- Inspect the current native goal using available controls (`get_goal` when
  exposed). Reuse the goal created by the pasted message. If none exists,
  this explicit goal request authorizes creating it with `create_goal` when
  available; use the full objective and completion condition. Do not create
  a goal per piece or replace an unrelated unfinished goal.
- Confirm native goal activation before dispatching work. If the destination
  lacks the required controls, explain that no persistent goal was started
  and stop; never silently claim an ordinary run has goal continuation.
- Use `update_goal` only as its current contract permits. Mark `complete`
  only after reading the actual critic verdict files, checking the assembled
  artifact and current test/Git evidence. Native goal status is not a critic.
  Follow the host's blocked-state threshold; do not equate difficult work or
  a plateau with an impasse while actionable work remains.
- Set a token budget only when the user explicitly requested one. Honor
  host pause, usage, budget and permission controls without declaring the
  goal complete or inventing tool operations to bypass them. Preserve the
  unresolved gaps and next action in the checkpoint when suspended.
- Use fresh critic contexts with no inherited lead/builder conversation
  (`fork_turns: "none"` when supported). Supply only the frozen remit and
  resolvable artifact/bar paths. Keep each builder across rounds and sequence
  dispatches to fit available agent slots. On a new-session resume, rebuild
  each builder's context from the checkpoint; do not assume live agents
  transfer. Reopen the bar and verify saved evidence before continuing.

## Checklist above the message

- A NEW Codex session in the run's directory, with the handoff page and all
  bar materials present. Select the requested model in the host; for Astra,
  select GPT-6 Astra. Use Codex's own reasoning controls, not Claude effort
  commands. Check the sandbox and permissions needed by the run.
- Verify that native `/goal` is available. If absent, check the host/version
  and `features.goals` setting; enable it through the host only if desired.
  Do not change the preparing session's settings. Keep this export even if
  the destination needs setup. A plain in-session prompt can be offered as
  a separate fallback, explicitly without native cross-turn continuation.
- Paste the block, then inspect `/goal` or the goal progress row to confirm
  the full objective and final completion condition are active. Correct a
  truncated objective before letting the run continue.
- Use `/goal pause`, `/goal resume`, `/goal edit`, or `/goal clear`, or the
  corresponding progress-row controls. A budget limit or blocked/paused
  state is not success. Resume with the checkpoint available; a different
  session needs the exported instructions and files again.
- After the run, in the run's session: `$optimus:commit` for any leftovers,
  then `$optimus:pr`; then `$optimus:code-review` in a fresh conversation.

Sources: [Codex goals](https://learn.chatgpt.com/use-cases/follow-goals),
[goal controls and size limit](https://learn.chatgpt.com/docs/developer-commands?surface=cli),
and [long-running work and permissions](https://learn.chatgpt.com/docs/long-running-work).
Native tool names above are conditional on the destination's exposed tools;
their current contracts take precedence over assumptions about another host.
