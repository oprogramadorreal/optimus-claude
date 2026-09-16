# Claude Code goal handoff

Use this only for a Claude Code destination. Shared export, completion, and
size rules live in the calling `goal-handoff.md` reference.

## Runtime instructions

Keep these in the handoff page and add a compact sentence to the message:
the small per-turn goal evaluator reads only conversation evidence and uses
no tools. Its reason is a continuation nudge, never a critic gap or a new
rule. Fresh-context critics remain the only quality judges. Show the shared
completion evidence each turn so the evaluator can assess it.

## Checklist above the message

- Claude Code 2.1.139 or later (`claude --version`), workspace trusted and
  hooks permitted; `/goal` is unavailable when hook policy disables it.
- A NEW conversation in the run's directory, with the handoff page and all
  bar materials present. Select `/effort` → ultracode for serious runs and
  choose the permission mode deliberately: a goal grants no extra access.
- Paste as one block, then inspect bare `/goal`; the registered condition
  must include the final "met ONLY when" paragraph. If truncated, clear it
  with `/goal clear` and paste the complete message again.
- Stop with `/goal clear`; interrupting a turn alone does not clear the goal.
  Bare `/goal` shows status/spend; an active goal survives session resume,
  while `/clear` removes it.
- The evaluator can clear a goal as impossible, and errors or nonprogress
  can clear or pause it. Inspect the stated reason and fix a real blocker
  before restarting; if the evaluator mistook a hard bar for an impossible
  one, re-paste the same condition. Clearing is not proof of success.
- After the run, commit any leftovers with `/optimus:commit`, then review
  the branch with `/optimus:code-review` in a fresh conversation.

Behavior source: [Claude Code goals](https://code.claude.com/docs/en/goal).
