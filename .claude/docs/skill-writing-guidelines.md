# Skill-writing guidelines

Deliberately not a copy of `skills/init/templates/docs/skill-writing-guidelines.md`, the version shipped to user projects: that one is stack-agnostic, this one carries plugin-specific rules a user project has no use for. When a rule applies to both, add it to both — `validate.sh` cannot pin these together the way it pins `coding-guidelines.md`.

## The one principle

Prioritize project-specific procedures, constraints, inter-skill contracts, and fragile sequences. Challenge repeated advice, but judge its value through task outcomes: model capability alone proves neither that a reminder is redundant nor that it helps. Keep instructions that prevent observed errors; simplify when comparable tasks show no benefit. Shared prompts are the default for Claude Code and Codex; add a host or model adaptation only for a demonstrated difference.

## Size and loading

- A skill's real invocation cost is SKILL.md **plus every file it reads unconditionally**. Budget the sum, not just SKILL.md.
- Keep SKILL.md well under 500 lines; most skills here should be 50–180.
- Gate cross-cutting reads behind reliable cheap conditions. Query Git's working-tree context when detecting multi-repo layouts; a `.git` file can represent a linked worktree or submodule. Never load a reference on every run that only matters on some runs.
- Progressive disclosure: SKILL.md is the overview; conditional detail goes in `references/`. A reference that would load on every run belongs inline. Reference depth: prefer one level from SKILL.md; two (SKILL → ref → ref) is the enforced maximum. Reference files >100 lines start with a table of contents.

## Degrees of freedom

Match specificity to fragility:

- **High freedom** (brief goals and criteria) — judgment tasks: review criteria, doc structure, report content. This is the default.
- **Low freedom** (exact commands, no deviation) — fragile sequences: the harness protocol, git surgery, JSON contracts parsed by scripts. Exact commands here are not bloat.

Over-specified step lists for judgment tasks are the plugin's historical failure mode. Provide one sensible default with an escape hatch, not an option menu. Scripted AskUserQuestion dialogs are justified only at genuine decision gates (destructive actions, scope approval, cost confirmation) — not for choreography.

## What not to instruct

These are candidates for simplification, not universal claims about every model or host. Compare correctness, completion, regressions, user intervention, and maintenance cost before removing consequential guidance.

- **Vague self-verification** — prefer concrete acceptance criteria and external checks: tests, schema validation, or installed-file comparison. Keep a focused self-check when it prevents an observed failure. The harness's no-child-tests rule has a different purpose: the parent owns test execution and rollback.
- **Automatic subagent review** — delegate independent review when its perspective or context isolation justifies the cost, supplying the needed evidence. Reuse `/optimus:code-review` where applicable instead of maintaining a private copy. Neither adding an agent nor sharing context guarantees a better result.
- **Delegating what the skill could do inline** — a fan-out that fires regardless of input size spawns agents on a three-file diff. Give every agent step a floor below which the skill does the work itself; the fan-out earns its cost on genuinely independent tracks, or when the material would crowd out the step that follows.
- **Per-step narration** — describe the cadence you want (one line up front, updates on something important, outcome first at the end) rather than mandating a report after every step.
- **Conservatism in analysis agents** — "only report what you're confident about" makes the model report less. Have agents report with an honest confidence label and filter in the consuming step, where the code is actually available to check against.

## Structure

- Skill = one concern; extend an existing skill instead of adding a new one when the capability runs on the same inputs in the same conversation and a user would look for it under that name. Fewer, well-scoped skills beat many narrow ones — skills are user-invoked, and a sprawling `/optimus:` menu hurts recall. (Exception: `init` is a deliberate one-time orchestrator.)
- Frontmatter: `description` (required), `disable-model-invocation: true` (required — skills never auto-trigger), quoted `argument-hint` when arguments exist. Keep `name:` omitted: this convention loads correctly in Claude Code 2.1.263 and Codex 0.153.4. [Issue 22063](https://github.com/anthropics/claude-code/issues/22063) records historical namespace trouble on Claude Code 2.1.27; current [Claude documentation](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name) preserves plugin namespaces. The [Codex public guide](https://learn.chatgpt.com/docs/build-skills) requires a name while the tested loader derives it from the directory. Preserve the working convention and test both hosts before changing it; do not generalize the old issue to every current release. Pair invocation control with `agents/openai.yaml` setting `policy.allow_implicit_invocation: false`; `validate.sh` requires both host flags.
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

Test instructions on representative tasks and iterate on observed behavior. For consequential changes compare current instructions, a minimal candidate, and an omitted-guidance baseline where useful; hold task inputs and runtime settings constant and repeat trials. Record exact host/model identifiers, correctness, completion, regressions, user intervention, and token/latency data when available. GPT-6 Astra (`gpt-6-astra`) and Claude Fable 5.1 (`claude-fable-5-1`) remain distinct evaluation targets; do not silently substitute another model. Label unavailable experiments and loader-only tests accurately. Prompt length alone does not measure quality.

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
