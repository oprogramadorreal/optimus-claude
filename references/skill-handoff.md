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

When a skill recommends plan mode as a handoff step:

- Treat plan mode as **review-only**. Tell the user not to approve the plan — use it to iterate on the design with Claude grounded against the real codebase.
- The generated plan-mode prompt must include a closing instruction telling Claude to **append a "Refined plan" section** to the underlying design/task doc (`docs/design/…` or `docs/jira/…`) once the user toggles plan mode off. Append (not overwrite) preserves the original design/task context for audit. The write happens in normal mode, same conversation, immediately after the mode transition — but only because the pasted prompt instructs it.
- After the user toggles plan mode off and Claude writes the refined plan, the user starts a **fresh conversation** and invokes the next skill (typically `/optimus:tdd` for code deliverables, or pastes an execution prompt for prose deliverables), which gathers context from scratch against the updated doc.

### Client-specific plan-mode controls

Plan-mode entry and exit use a UI toggle that **differs per Claude Code client**. Skills must describe the action client-agnostically and name specific keybindings only as examples, never as the primary instruction. The reliable signal is the mode indicator in the client's UI.

- **Claude Code CLI:** `Shift+Tab` cycles permission modes. Press until the mode indicator reads "plan mode" to enter; press again to toggle plan mode off without approving.
- **VSCode extension and other clients:** use the equivalent plan-mode toggle in the client's UI.
- **Portable entry points** (work across clients): launch with `claude --permission-mode plan`, or prefix the message with `/plan`.
- **No universal exit slash command** exists for user-initiated exit; rely on the client's toggle.

## Canonical plan-mode handoff (quote verbatim into skill closing copy)

Skills that end in a plan-mode handoff must emit **three things in this order**:

1. **A plan-mode prompt block** (pre-filled, copyable). Its closing paragraph must tell Claude:

   > Treat this conversation as a review loop — validate the plan against the actual codebase and iterate with me. When I'm ready, I will toggle plan mode off in my client without approving. As soon as you observe the mode transition, append a "Refined plan" section to `<doc-path>` to capture the refined plan, then stop — I will start a fresh conversation to execute it.

2. **A three-step user instruction**, phrased as follows (substitute `<doc-path>` and the next-skill slug):

   > 1. Start a fresh Claude Code conversation and switch it into **plan mode** using your client's plan-mode toggle (on the Claude Code CLI, press `Shift+Tab` until the mode indicator reads "plan mode"; in the VSCode extension or other clients, use the equivalent control). Alternatively, launch with `claude --permission-mode plan` or prefix your first message with `/plan`. Paste the prompt above as the first message.
   > 2. Iterate with Claude. **Do not approve the plan** (and ignore the "Ultraplan" option if offered — both execute immediately and skip the follow-up step). When you're satisfied, **toggle plan mode off without approving** (CLI: press `Shift+Tab` again; other clients: use the equivalent toggle — the mode indicator confirms you've left plan mode). The pasted prompt has already told Claude to append a "Refined plan" section to `<doc-path>` — it will do so now, in the same conversation, in normal mode.
   > 3. Start a **second fresh conversation** and paste the execution prompt below. (Each skill's Step 1 gathers context from scratch — a clean conversation keeps that honest.)

3. **An execution prompt block** (pre-filled, copyable) for the second conversation. Reference `<doc-path>` and name the deliverable. For **code deliverables**, the prompt should invoke `/optimus:tdd` and point it at the updated doc. For **prose deliverables** (research notes, audit reports, investigation write-ups — no code produced), the prompt should instruct Claude directly, with scope carried forward from the design doc, and explicitly note that `/optimus:tdd` does not apply.

### Ultraplan

Claude Code's plan-approval dialog may offer an "Ultraplan" option. **Ignore it for this handoff** — Ultraplan executes the plan, which skips the `/optimus:tdd` discipline or the prose-execution prompt.

## Why fresh conversations

Each skill gathers its own context (doc loads, pre-flight checks, suitability analysis). Reusing a conversation mixes unrelated context and can bias the new skill's decisions. A fresh conversation keeps every skill's Step 1 honest.
