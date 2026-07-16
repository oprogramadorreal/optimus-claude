# Skill-writing guidelines

The upstream source is Anthropic's [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices);
this file adds what is specific to this plugin and omits what the model already knows.

## Core principle

Claude is already very smart — only add context it doesn't have. Challenge every
instruction: "Would removing this cause a capable model to make a mistake?" If not,
cut it. Over-prescription is not free: instructions written for earlier, weaker
models actively degrade current ones, and bloated skills bury the rules that matter.

## Degrees of freedom

Match specificity to fragility:

- **High freedom** (brief goals and constraints) for anything conversational or
  context-dependent: design discussions, review judgment, report wording, when to ask
  the user. Never script exact dialog wording, option labels for routine
  confirmations, or verbatim phrases the model must emit.
- **Low freedom** (exact commands, pinned strings) only where a machine parses the
  output or a fragile sequence must hold: the harness CLI protocol
  (`references/orchestrator-loop.md`, `harness-mode.md`), JSON output schemas, the
  spec↔tdd `## Scenarios` heading contract. These are contracts — copy them exactly
  and change them only together with their consumers and tests.

Safety gates (user confirmation before destructive actions, never-commit rules,
secret-file warnings) are requirements, not over-prescription — keep them explicit.

## Plugin rules (non-inferable)

- Every SKILL.md sets `disable-model-invocation: true` — skills are explicitly
  user-invoked, never auto-triggered.
- Do NOT add a `name:` field to SKILL.md frontmatter — it strips the plugin
  namespace prefix and shadows builtin commands
  ([anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063)).
- Quote `argument-hint` values (bare brackets parse as a YAML list).
- Descriptions: third person, lead with the differentiating verb phrase, state what
  the skill does and when to use it, declare side effects (branch creation, commits,
  pushes, file writes) and hard prerequisites. Platform cap is 1024 characters
  (enforced by `scripts/validate.sh`).
- The installed `.claude/docs/coding-guidelines.md` is the single source of truth for
  code-quality rules — skills and agents reference it, never restate its principles.
- Skill output stays plain: markdown headings, bold, blockquotes — no decorative
  emoji, no hand-rolled `[Step N/M]` progress lines. When a step's design depends on
  a parallel fan-out, state the expected agent count explicitly.

## Structure

- `SKILL.md` + `README.md` required in every skill directory (validated).
- Keep SKILL.md well under 500 lines; most should be far smaller. Push detail that
  is only sometimes needed into `references/` files loaded on demand.
- References at most two levels deep from SKILL.md (validated); prefer one.
- Agent prompts live in `skills/<name>/agents/`, one file per agent, with
  `shared-constraints.md` for skill-wide rules — see
  `references/agent-architecture.md` for the two-tier design and the prompt-assembly
  rule for dispatching subagents.
- When 2+ skills need the same procedure, extract it to a reference owned by the
  canonical skill (e.g. `skills/init/references/multi-repo-detection.md`); don't
  duplicate and don't extract for hypothetical reuse.

## Scope

Skills here are user-invoked, so a sprawling `/optimus:` menu hurts discovery as
much as a bloated skill hurts execution. Before adding a skill or capability, ask:
does Claude Code or the bare model already do this well? If yes, don't ship it.
Extend an existing skill when the capability runs on the same inputs in the same
conversation and a user would look for it there; otherwise create a new one.

## Ending a skill

Close with a short, natural recommendation of what to do next, when there is a
genuine next step (e.g. after tdd: open a PR, then run `/optimus:code-review` in a
fresh conversation). Plain prose — no mandated wording, no tip boilerplate. Skills
that analyze from scratch benefit from fresh conversations; say so only where it
actually matters.

## Anti-patterns

- Verbatim output the model must emit (pinned phrases, rigid report templates for
  human-facing text).
- Scripted conversation flows: enumerated AskUserQuestion headers/labels for routine
  confirmations, branches for situations the model handles naturally.
- Restating default model behavior ("read the file before editing", "run the tests
  after changes", "be careful with secrets").
- Time-sensitive content, inconsistent terminology, Windows-style paths.
- Telling the model to narrate its reasoning as output.
- Drive-by improvements: when fixing a skill, change only what the task requires.
