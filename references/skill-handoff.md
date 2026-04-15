# Skill handoff convention

Every skill's closing "next step" text must tell the user three things, in this order:

1. **Conversation** — whether to stay in the current conversation or start a fresh one.
2. **Mode** — normal mode, or plan mode. When plan mode is recommended, say explicitly whether to approve the plan (see "Plan mode" below).
3. **Next skill** — the exact slash command to invoke, or "none" if the chain ends here.

Closing tip (append verbatim whenever recommending a next skill):

> **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch.

## Plan mode

Claude Code's plan mode has built-in semantics the plugin cannot change: **approving a plan executes it immediately in the same conversation.** That conflicts with skills that route to `/optimus:tdd` afterwards, because plan-mode execution bypasses TDD's Red-Green-Refactor discipline (the Iron Law, verification protocol, circuit breaker).

Plan mode is also **read-only**: Claude cannot write files while the conversation is in plan mode. Any persistence ("append the refined plan to the doc") happens *after* the user toggles plan mode off, in normal mode, in the same conversation — and only because the pasted plan-mode prompt told Claude to do it. There is no automatic persistence; it is prompt-driven.

Plan mode is a **client UI toggle** — no phrase exits it. The user must press the client's plan-mode control (CLI: `Shift+Tab`; VSCode extension and other clients: the equivalent toggle). Alternate entry points: launch with `claude --permission-mode plan`, or prefix the first message with `/plan`. Skill closing copy should describe the action client-agnostically and mention `Shift+Tab` only as an example. Note: some approval dialogs offer an "Ultraplan" option — it executes the plan, so treat it like approval and ignore it.

When a skill recommends plan mode as a handoff step:

- Treat plan mode as **review-only**. Tell the user not to approve the plan — use it to iterate on the design with Claude grounded against the real codebase.
- The generated plan-mode prompt must include a closing instruction telling Claude to **append a "Refined plan" section** to the underlying design/task doc (`docs/design/…` or `docs/jira/…`) once the user signals they're done iterating. Append (not overwrite) preserves the original design/task context for audit. The write happens in normal mode after the user toggles plan mode off, in the same conversation — it is prompt-driven, not automatic.
- After Claude writes the refined plan, the user starts a **fresh conversation** and invokes the next skill (typically `/optimus:tdd` for code deliverables, or pastes an execution prompt for prose deliverables), which gathers context from scratch against the updated doc.

## Why fresh conversations

Each skill gathers its own context (doc loads, pre-flight checks, suitability analysis). Reusing a conversation mixes unrelated context and can bias the new skill's decisions. A fresh conversation keeps every skill's Step 1 honest.
