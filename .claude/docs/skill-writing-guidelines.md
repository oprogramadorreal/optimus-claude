# Skill-writing guidelines

Deliberately not a copy of `skills/init/templates/docs/skill-writing-guidelines.md`, the version shipped to user projects: that one is stack-agnostic, this one carries plugin-specific rules a user project has no use for. When a rule applies to both, add it to both — `validate.sh` cannot pin these together the way it pins `coding-guidelines.md`.

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

## What not to instruct

Current models already do these. Instructing them again costs tokens and can degrade behavior.

- **Self-verification** — no "double-check", "verify before responding", or a final verification step appended to a task. What *is* worth instructing is a check against something external the model cannot self-assess: run the suite, validate against the schema, `diff` the installed file against its template. `references/harness-mode.md`'s "not even to 'verify' your own fixes" is the model to copy.
- **Subagent verification of the skill's own output** — delegation is for large, genuinely independent work. An agent reviewing what this conversation just wrote has less context, not more. Recommend `/optimus:code-review` instead of inlining a private copy of it.
- **Delegating what the skill could do inline** — a fan-out that fires regardless of input size spawns agents on a three-file diff. Give every agent step a floor below which the skill does the work itself; the fan-out earns its cost on genuinely independent tracks, or when the material would crowd out the step that follows.
- **Per-step narration** — describe the cadence you want (one line up front, updates on something important, outcome first at the end) rather than mandating a report after every step.
- **Conservatism in analysis agents** — "only report what you're confident about" makes the model report less. Have agents report with an honest confidence label and filter in the consuming step, where the code is actually available to check against.

## Structure

- Skill = one concern; extend an existing skill instead of adding a new one when the capability runs on the same inputs in the same conversation and a user would look for it under that name. Fewer, well-scoped skills beat many narrow ones — skills are user-invoked, and a sprawling `/optimus:` menu hurts recall. (Exception: `init` is a deliberate one-time orchestrator.)
- Frontmatter: `description` (required), `disable-model-invocation: true` (required — skills never auto-trigger), quoted `argument-hint` when arguments exist. Do NOT add a `name:` field — it strips the plugin namespace prefix ([anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063)); Codex derives the name from the directory. Pair the flag with `agents/openai.yaml` setting `policy.allow_implicit_invocation: false` — its Codex twin; each host reads only its own, and `validate.sh` requires both.
- Descriptions must parse as YAML: a `: ` inside an unquoted scalar ("Read-only: applies…") makes Claude Code load the skill with empty metadata — dropping `disable-model-invocation` — and makes Codex skip it. Use the folded `>-` form when in doubt. `validate_skill_metadata.py` parses frontmatter and the Codex policy and requires actual boolean values, not strings.
- Descriptions: third person, lead with the differentiating verb phrase, state WHAT and WHEN, declare side effects (commits, pushes, file writes) and hard prerequisites. Target 250–450 chars (platform cap 1024). Feature inventories belong in README.md.
- Names: short verb/noun slash-command style (`init`, `commit`, `deep`), consistent with the existing set.
- Directory: `SKILL.md`, `README.md`, and `agents/openai.yaml` (all required); optional `references/`, `templates/`, and agent prompt files under `agents/`. Agent prompt files are self-contained — inline their criteria; do not chain them through plugin-level agent files or pointer files.
- Host portability: write for Claude Code and name its tools (`AskUserQuestion`, the Agent tool) — the session-start hook tells a Codex model how to map them, so host-neutral paraphrases only add words. Never rely on `$CLAUDE_PLUGIN_ROOT` being set in a Bash call: Claude Code leaves it empty on some platforms and Codex sets it only for hooks. Resolve the root once, the way `deep` does, and substitute absolute paths into every subagent prompt.
- When a procedure is used by 2+ skills, extract it to a reference owned by the canonical skill; consumers read it and apply their own policy. Don't extract single-use content.
- `.claude/docs/coding-guidelines.md` (installed by init) is the single source of truth for code-quality rules — reference it, never restate it.

## Writing style

- Imperative steps, consistent terminology (one term per concept), no time-sensitive content.
- Output templates stay plain: headings, bold, blockquotes — no decorative emoji, no hand-rolled "[Step N/M]" progress lines.
- For parallel-agent steps, say to launch them in a single message — that instruction is about parallelism, not head count. Size the fan-out to the input rather than mandating a count: a step that always spawns N agents spawns them on inputs one pass would cover, and how readily a model delegates on its own changes between releases, so the input-size floor is the rule that survives. Name the lenses that must be covered, give a floor below which the skill does them inline, and let the model size the rest.
- Don't instruct Claude to narrate or transcribe its reasoning; ask for conclusions and rationale.
- Calibrate authored deliverables. A skill that writes a document states its target length once, where the template is defined (`brainstorm`'s "keep the spec under 200 lines" is the model). Current models write long by default, and an uncalibrated document fills with filler sections and restated summaries.

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
