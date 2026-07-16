# Skill-writing guidelines for [PROJECT NAME]

This file governs the quality of **markdown instruction files** authored for an AI
agent — skills, agents, prompts, commands, or instructions. Code files follow
`coding-guidelines.md` instead. When reviewing, refactoring, or evaluating any file,
route to the lens that matches the file's type. The upstream source for generic
authoring practice is Anthropic's
[skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices);
this file keeps only what reviewers of this project need to enforce.

## Core principle

The AI agent is already very smart — only add context it doesn't have. Challenge
each instruction: "Would removing this cause the agent to make a mistake?" If not,
cut it. Over-prescription is not free: instructions written for weaker models
actively degrade current ones, and bloated files bury the rules that matter.
Safety procedures (validation rules, command allowlists, user-approval gates) are
requirements, not over-prescription — keep them explicit.

## Degrees of freedom

Match specificity to fragility:

- **High freedom** (brief goals and constraints) when multiple approaches are valid
  and decisions depend on context — review criteria, document structure,
  conversational flow. Never script exact dialog wording or verbatim phrases the
  agent must emit.
- **Low freedom** (exact commands, pinned strings) only where operations are fragile
  or a machine parses the output — validation commands, state-file formats,
  producer/consumer heading contracts. Change these only together with their
  consumers.

Default to high freedom. Provide one sensible default with an escape hatch rather
than listing many options.

## Structure

- Follow the project's existing instruction structure, frontmatter conventions, and
  directory layout; when introducing a new pattern, apply it consistently.
- Each instruction file owns one concern; keep bodies under 500 lines and move
  detail that is only sometimes needed into reference files loaded on demand.
- Reference depth: at most two levels from the main instruction file; no circular
  references. Give reference files longer than 100 lines a table of contents.
- Extract a shared reference when 2+ instructions reuse a procedure — owned by one
  canonical instruction. Don't extract for hypothetical reuse.
- Intention-revealing names everywhere; avoid `helper.md`, `utils.md`, `doc2.md`.
- Descriptions (frontmatter): third person, lead with the differentiating verb
  phrase, state what the instruction does and when to use it, declare side effects
  and hard prerequisites.

## Anti-patterns

- Verbatim output the agent must emit; rigid report templates for human-facing text.
- Scripted conversation flows and enumerated dialog options for routine
  confirmations; branches for situations the agent handles naturally.
- Restating default agent behavior ("read the file before editing", "run the tests
  after changes").
- Over-explaining concepts the agent already knows; too many options; time-sensitive
  content; inconsistent terminology (one term per concept); Windows-style paths.
- Drive-by improvements — when fixing an instruction, change only what the task
  requires.
- Reasoning-echo instructions — ask for conclusions and rationale, not a replay of
  the agent's chain of thought.

## Documentation

Every instruction should have a user-facing description or README explaining what it
does and when to use it. After any change, verify the description and any referring
indexes still reflect actual behavior.
