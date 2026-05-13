# Skill handoff convention

Every skill's closing "next step" text must tell the user three things, in this order:

1. **Conversation** — whether to stay in the current conversation or start a fresh one.
2. **Mode** — normal mode, or plan mode. When plan mode is recommended, say explicitly whether to approve the plan (see "Plan mode" below).
3. **Next skill** — the exact slash command to invoke, or "none" if the chain ends here.

Closing tip (append verbatim whenever recommending a next skill):

> **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch.

## Continuation skills — exception to fresh-conversation

The default tip above applies when the next skill **gathers its own context**. Some skills instead **capture** the current conversation's context (design decisions, non-goals, trade-offs discussed during implementation) into a durable artifact. For those skills, a fresh conversation strips the very context they need. Override the default tip when the next skill is one of these.

The continuation skills are:

- **`/optimus:commit`** — captures the conversation's understanding of *why* the changes were made into the commit message body. A commit message generated from the diff alone records *what* changed; a commit message generated in the implementation conversation also records *why*.
- **`/optimus:commit-message`** — same intent capture as `/optimus:commit`, but read-only (suggests a message without committing). Same continuation rationale.
- **`/optimus:pr`** — captures the conversation's intent (problem, scope, non-goals, key decisions) into the PR description. `/optimus:code-review` later consumes that description as author intent context.

The canonical implementation chain is **implement → `/optimus:commit` → `/optimus:pr` → `/optimus:code-review`**. The first three should run in the same conversation as the implementation (or, after `/optimus:code-review` applies fixes, in the code-review conversation). `/optimus:code-review` itself, and other downstream skills like `/optimus:unit-test`, run in fresh conversations because they gather their own context.

### Closing tip wording

Skills that emit a closing tip must use one of the variants below **verbatim** (substituting only the explicit placeholders). Drift is the failure mode this section exists to prevent — never paraphrase to skill-specific wording like "refactor's rationale", "deliverable's rationale", or "fix context". The umbrella term **"implementation context"** is intentional and covers design decisions, refactor rationale, fix context, and deliverable rationale.

#### Variant A — Single continuation skill

When the closing block recommends **one** continuation skill, emit:

> **Tip:** stay in this conversation when running `<continuation-skill>` so it can capture the implementation context. Other downstream skills (`<non-continuation-examples>`) should still run in fresh conversations.

Substitute `<continuation-skill>` with the actual skill (e.g., `/optimus:pr`). Substitute `<non-continuation-examples>` with the relevant examples (e.g., `/optimus:code-review`, `/optimus:unit-test`, etc.).

#### Variant B — Mixed (continuation + non-continuation)

When the closing block recommends **two or more** skills with a mix of continuation and non-continuation paths, emit:

> **Tip:** for `<continuation-skills>`, stay in this conversation so they can capture the implementation context. For other downstream skills (`<non-continuation-examples>`), start a fresh conversation — each gathers its own context from scratch.

Use commas + "and" for multiple continuation skills (e.g., `` `/optimus:commit` and `/optimus:pr` ``).

#### Variant C — Default (no continuation skill recommended)

When the closing block recommends only non-continuation skills, emit the plain default:

> **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch.

### Adding a future continuation skill

The criterion: the skill's primary value comes from reading the current conversation, not from independent context gathering. Skills that load docs, run pre-flight checks, or analyze code from scratch are **not** continuation skills.

## Plan mode

Claude Code's plan mode has built-in semantics the plugin cannot change: **approving a plan executes it immediately in the same conversation.** That conflicts with skills that route to `/optimus:tdd` afterwards, because plan-mode execution bypasses TDD's Red-Green-Refactor discipline (the Iron Law, verification protocol, circuit breaker).

Plan mode is also **read-only**: Claude cannot write files while the conversation is in plan mode. Any persistence ("append the refined plan to the doc") happens *after* the user toggles plan mode off **and sends a follow-up message** in normal mode, in the same conversation — the toggle itself is a permission-state change that does not trigger Claude; Claude only acts on the next user message, and only because the pasted plan-mode prompt told it to. There is no automatic persistence; it is prompt-driven.

Plan mode is a **client UI toggle** — no phrase exits it. The user must press the client's plan-mode control (CLI: `Shift+Tab`; VSCode extension and other clients: the equivalent toggle). Alternate entry points: launch with `claude --permission-mode plan`, or prefix the first message with `/plan`. Skill closing copy should describe the action client-agnostically and mention `Shift+Tab` only as an example. Note: some approval dialogs offer an "Ultraplan" option — it executes the plan, so treat it like approval and ignore it.

When a skill recommends plan mode as a handoff step:

- Treat plan mode as **review-only**. Tell the user not to approve the plan — use it to iterate on the design with Claude grounded against the real codebase.
- The generated plan-mode prompt must include a closing instruction telling Claude to **append a "Refined plan" section** to the underlying design/task doc (`docs/design/…` or `docs/jira/…`) once the user signals they're done iterating. Append (not overwrite) preserves the original design/task context for audit. The write happens in normal mode after the user toggles plan mode off and sends a follow-up message — it is prompt-driven and requires an explicit trigger message, not automatic.
- After Claude writes the refined plan, the user starts a **fresh conversation** and invokes the next skill (typically `/optimus:tdd` for code deliverables, or pastes an execution prompt for prose deliverables), which gathers context from scratch against the updated doc.

## Why fresh conversations

Each skill gathers its own context (doc loads, pre-flight checks, suitability analysis). Reusing a conversation mixes unrelated context and can bias the new skill's decisions. A fresh conversation keeps every skill's Step 1 honest.

The exception is continuation skills (see "Continuation skills — exception to fresh-conversation" above), where the current conversation **is** the context. For those, staying in the conversation is the honest choice.
