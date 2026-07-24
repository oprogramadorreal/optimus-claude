# Skill-writing guidelines

## The one principle

Claude is already very smart. A skill earns its context cost only with things Claude cannot infer: project-specific procedures, safety constraints, inter-skill contracts, and genuinely fragile sequences. Challenge every instruction: "Would a capable model get this wrong without being told?" If not, delete it. Restating what Claude does natively (how to read a diff, how to phrase a report, that it should read a file before editing it) actively degrades output by burying the rules that matter.

## Size and loading

- A skill's real invocation cost is SKILL.md **plus every file it reads unconditionally**. Budget the sum, not just SKILL.md.
- Keep SKILL.md well under 500 lines; most skills here should be 50–180.
- Gate cross-cutting reads behind cheap inline conditions (e.g. multi-repo detection: "If the cwd has no `.git/` directory, read `skills/init/references/multi-repo-detection.md`"). Never load a reference on every run that only matters on some runs.
- Progressive disclosure: SKILL.md is the overview; conditional detail goes in `references/`. A reference that would load on every run belongs inline. Reference depth: prefer one level from SKILL.md; two (SKILL → ref → ref) is the enforced maximum. Reference files >100 lines start with a table of contents.

## Degrees of freedom

Match specificity to fragility:

- **High freedom** (brief goals and criteria) — judgment tasks: review criteria, doc structure, report content. This is the default.
- **Low freedom** (exact commands, no deviation) — fragile sequences: the harness protocol, git surgery, JSON contracts parsed by scripts. Exact commands here are not bloat.

Over-specified step lists for judgment tasks are the plugin's historical failure mode. Provide one sensible default with an escape hatch, not an option menu. Scripted AskUserQuestion dialogs are justified only at genuine decision gates (destructive actions, scope approval, cost confirmation) — not for choreography.

## Structure

- Skill = one concern; extend an existing skill instead of adding a new one when the capability runs on the same inputs in the same conversation and a user would look for it under that name. Fewer, well-scoped skills beat many narrow ones — skills are user-invoked, and a sprawling `/optimus:` menu hurts recall. (Exception: `init` is a deliberate one-time orchestrator.)
- Frontmatter: `description` (required), `disable-model-invocation: true` (required — skills never auto-trigger), quoted `argument-hint` when arguments exist. Do NOT add a `name:` field — it strips the plugin namespace prefix ([anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063)).
- Descriptions: third person, lead with the differentiating verb phrase, state WHAT and WHEN, declare side effects (commits, pushes, file writes) and hard prerequisites. Target 250–450 chars (platform cap 1024). Feature inventories belong in README.md.
- Names: short verb/noun slash-command style (`init`, `commit`, `deep`), consistent with the existing set.
- Directory: `SKILL.md` + `README.md` (both required); optional `references/`, `templates/`, `agents/`. Agent prompt files are self-contained — inline their criteria; do not chain them through plugin-level agent files or pointer files.
- When a procedure is used by 2+ skills, extract it to a reference owned by the canonical skill; consumers read it and apply their own policy. Don't extract single-use content.
- `.claude/docs/coding-guidelines.md` (installed by init) is the single source of truth for code-quality rules — reference it, never restate it.

## Writing style

- Imperative steps, consistent terminology (one term per concept), no time-sensitive content.
- Output templates stay plain: headings, bold, blockquotes — no decorative emoji, no hand-rolled "[Step N/M]" progress lines.
- For parallel-agent steps, state the fan-out imperatively ("Launch all 4 agents in a single message") — some models under-spawn otherwise.
- Don't instruct Claude to narrate or transcribe its reasoning; ask for conclusions and rationale.

## Closing a skill

End with one or two plain lines recommending the next step, chosen by outcome (fixed issues → `/optimus:commit`; committed → `/optimus:pr`). When the recommended skill captures the current conversation into an artifact (`/optimus:commit`, `/optimus:pr`, `/optimus:handoff`), say to stay in this conversation; otherwise suggest a fresh one. No verbatim tip wording, no variants — one honest sentence.

## Agents

- Skill-level agents (`skills/<name>/agents/*.md`) carry their own criteria inline. Shared behavioral rules live once in `references/shared-agent-constraints.md`; a skill's `agents/shared-constraints.md` holds only genuine addendums plus the skill's canonical output format.
- Subagents inherit neither `$CLAUDE_PLUGIN_ROOT` nor the agents directory as cwd — at dispatch, substitute the resolved absolute root into every path and inline or absolutize bare relative references (see `references/agent-architecture.md`).

## Evaluation

Write minimal instructions, test on real tasks, and iterate on observed behavior — watch whether Claude misses references, over-relies on one section, or ignores bundled files. Don't document imagined problems.

## Documentation

Every skill has a user-facing README.md (never context-loaded — verbosity is cheaper there, but duplication with SKILL.md still rots). After any skill change, verify the root README.md and the skill's README.md still match actual behavior; new skills are added to the root README table and CONTRIBUTING's tree.

## Anti-patterns

- Over-explaining concepts Claude knows; defensive branches for hypothetical scenarios; dead steps.
- Option menus where a default + escape hatch suffices.
- Windows-style paths — always forward slashes.
- Drive-by improvements: when fixing a skill, change only what the task requires.
- Verbatim-pinned prose: never make CI assert exact wording of model-facing instructions except genuine two-sided contracts (a heading one skill emits and another parses).

## Further reading

Anthropic's [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) is the upstream source. Plugin-specific divergences: `disable-model-invocation: true` everywhere, no `name:` field, and the two-level reference-depth allowance.
