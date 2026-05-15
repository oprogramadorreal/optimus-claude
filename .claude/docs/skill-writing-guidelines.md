# Skill-writing guidelines

## Foundation

These quality principles apply to skill authoring just as they apply to code:

- **Follow Existing Patterns** — match existing skill structure, frontmatter conventions, and reference patterns. Prefer established approaches over novel ones. When introducing a different pattern, apply it consistently — don't leave skills in a mixed state.
- **KISS** — default to the simplest instructions that meet current requirements. Don't add steps or branches for hypothetical scenarios. Remove dead steps — unused branches, commented-out instructions, and redundant clarifications add noise without value. Safety procedures (validation rules, command allowlists, user-approval gates) and explicit behavioral constraints are requirements — their detail is justified, not a simplicity violation.
- **SRP** — each skill focused on one concern, each step on one action. When a step handles multiple concerns or mixes abstraction levels, decompose it. See [Scope and Granularity](#scope-and-granularity) for when to merge vs. split.

  > **Exception — orchestration skills:** A skill may span multiple concerns when it serves as a one-time setup orchestrator whose value depends on executing all steps atomically (e.g., `skills/init/` handles project detection, CLAUDE.md generation, hooks, agents, and test infrastructure as a single coherent setup). Decomposing these into separate skills would force users to run them in sequence with no clear benefit. Keep orchestration skills well-structured internally — each step should still follow SRP.

- **Intention-Revealing Names** — skill names, template files, and reference docs should convey purpose without tracing through content. Avoid generic names like `helper.md`, `utils.md`, or `doc2.md`.
- **Pragmatic Abstractions** — extract shared references when 2+ skills reuse a procedure. Don't add indirection for its own sake. Don't extract for hypothetical future reuse.

## Scope and Granularity

Two failure modes pull in opposite directions — aim for the balance, not either extreme:

- **Skill bloat** — a skill that does many things wastes context on every invocation and makes its description vague. Already mitigated by [SRP](#foundation) and the 500-line cap in [Writing Style](#writing-style).
- **Skill-count bloat** — skills here are user-invoked, never auto-selected by Claude (see [Design Principles](#design-principles)), so a sprawling `/optimus:*` list hurts user discovery and recall. Fewer, well-scoped skills beat many narrow ones.

When adding a capability, prefer extending an existing skill if **all** hold; otherwise create a new one:

- It runs in the same conversation as skill X, on the same inputs, producing related outputs.
- It wouldn't push X past ~500 lines or force X's description to mix unrelated triggers.
- A user reaching for X would also expect it — they wouldn't search for it under a separate name.

If a procedure ends up reused by 2+ skills after splitting, extract it per [Shared References](#shared-references) rather than re-merging.

## Design Principles

- `disable-model-invocation: true` required on all skills — skills are tools users explicitly reach for, never auto-triggered. The plugin enhances Claude Code without changing its default behavior behind the user's back.
- Do NOT add a `name` field to SKILL.md frontmatter — it strips the plugin namespace prefix ([anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063)). Note: Anthropic's official docs require a `name` field for standalone skills, but plugins must omit it to avoid namespace collision.
- `coding-guidelines.md` (the template at `skills/init/templates/docs/`) is the single source of truth for code quality rules — skills and agents must reference it, never duplicate its principles inline.

## Writing Style

- Claude is already very smart — only add context it doesn't already have. Challenge each instruction: "Does Claude really need this?" Omit explanations of concepts Claude already knows; include behavioral rules, safety constraints, and domain procedures it can't infer.
- Imperative step-by-step instructions, not conversational prose.
- Keep SKILL.md body under 500 lines — move detailed reference material to separate files.
- No time-sensitive information; consistent terminology throughout — pick one term per concept and use it everywhere (e.g., always "field" not a mix of "field", "box", "element").

## Degrees of Freedom

Match the level of specificity to the task's fragility:

- **High freedom** (text-based guidance) — when multiple approaches are valid and decisions depend on context. Example: code review criteria, documentation structure.
- **Medium freedom** (pseudocode or parameterized templates) — when a preferred pattern exists but some variation is acceptable. Example: report generation with configurable sections.
- **Low freedom** (exact scripts, no deviation) — when operations are fragile, consistency is critical, or a specific sequence must be followed. Example: database migrations, validation commands.

Default to high freedom unless the task is fragile. Provide a sensible default with an escape hatch rather than listing many options.

## Description Quality (frontmatter)

- Must describe both WHAT the skill does AND WHEN to use it — Claude uses descriptions to select the right skill from potentially many available skills.
- Write descriptions in third person — they are injected into the system prompt. Good: "Generates commit messages by analyzing diffs." Avoid: "I can help you generate commit messages."
- Include specific keywords users would naturally say.
- Be concrete and specific, not vague. Bad: "Helps with documents." Good: "Extracts text and tables from PDF files, fills forms, merges documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."
- Prefer gerund form for skill names when possible: `processing-pdfs`, `analyzing-code`. Avoid vague names: `helper`, `utils`, `tools`.
- Max 1024 characters.

## Progressive Disclosure

- Load only metadata (description) at startup.
- Load full SKILL.md when skill is invoked.
- Load reference files only as needed within the skill's execution.
- Reference depth should not exceed two levels from SKILL.md (SKILL→A→B maximum). If you find yourself needing A→B→C→D, restructure by flattening the chain (preferred) — make SKILL.md reference the deeper files directly. Only inline content when the extracted file is small, single-use, and tightly coupled to its parent; otherwise inlining violates SRP by mixing concerns in one file. Circular references between files are never allowed.
- For reference files longer than 100 lines, include a table of contents at the top so Claude can see the full scope even when previewing with partial reads.

## Directory Layout

- `SKILL.md` (required) + `README.md` (required).
- Templates in `templates/` (`hooks/`, `docs/` subdirs).
- Reference docs in `references/`.
- When agents use prompt templates, split into individual files under `agents/` — one file per agent, plus `shared-constraints.md` for common rules and `context-blocks.md` for conditional context injection. Don't inline agent prompts in SKILL.md (see `skills/code-review/` for the pattern). Plugin-level agent definitions (reusable across skills) live in the top-level `agents/` directory — see `references/agent-architecture.md` for the two-tier architecture and when to use each tier.

## Shared References

- When a procedure is used by 2+ skills, extract to a reference file owned by the canonical skill.
- Consuming skills read the reference and apply their own policy — this avoids logic duplication while keeping each skill self-contained.
- Examples: `multi-repo-detection.md` (owned by init), `platform-detection.md` (owned by pr).

## Workflows and Feedback Loops

For complex multi-step skills:

- Break operations into clear sequential steps. For particularly complex workflows, provide a checklist Claude can copy and track progress against.
- Implement feedback loops for quality-critical tasks: run validator → fix errors → repeat. Make validation a gate — "only proceed when validation passes."
- Use conditional workflows to guide Claude through decision points: "Creating new? → follow creation workflow. Editing existing? → follow editing workflow."

## Common Patterns

- **Template pattern** — provide output format templates. Use strict templates ("ALWAYS use this exact structure") when consistency is critical; use flexible templates ("sensible default, adapt as needed") when context should drive the structure.
- **Examples pattern** — provide input/output pairs (like few-shot prompting) when output quality depends on matching a specific style or format. Examples communicate style and detail level more clearly than descriptions alone.
- **Conditional workflow** — branch instructions based on detected state or user intent. Push large branches into separate reference files rather than inlining them all in SKILL.md.

## Evaluation and Iteration

- Build evaluations before writing extensive documentation — identify what Claude gets wrong without the skill, then write minimal instructions to address those gaps.
- Test skills iteratively: write minimal instructions → test with real tasks → observe behavior → refine. Each iteration improves the skill based on observed behavior, not assumptions.
- Watch how Claude navigates the skill in practice: does it miss references? Over-rely on certain sections? Ignore bundled files? Iterate based on these observations.

## Anti-patterns

- **Over-explaining** — don't explain what PDFs are or how libraries work. Claude knows. Add only what it can't infer: project-specific rules, domain procedures, safety constraints.
- **Too many options** — don't list five libraries for the same task. Provide one sensible default with an escape hatch for edge cases.
- **Windows-style paths** — always use forward slashes (`reference/guide.md`), never backslashes. Forward slashes work cross-platform.
- **Inconsistent terminology** — pick one term per concept. Don't mix "field"/"box"/"element" or "extract"/"pull"/"get" for the same operation.
- **Drive-by improvements** — when fixing or updating a skill, only change what the task requires. Don't restructure adjacent sections, rename variables in examples, or reformat content you're passing through.

## Documentation

- Every skill must have a user-facing `README.md`.
- After any skill change, verify root `README.md` and the skill's `README.md` still reflect current behavior.
- Add new skills to the Skills section in root `README.md`.

## Next Step

Every skill must end with a recommendation for the next logical optimus skill. This guides the user through the workflow and increases plugin adoption.

- Choose the next skill based on the outcome (e.g., after fixing issues → commit; after committing → PR).
- If multiple paths are possible, present them conditionally (e.g., "if X → skill A; if Y → skill B").
- Always include the fresh-conversation tip as part of the recommendation to the user — e.g., "Recommend running `/optimus:X` to do Y. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch." The tip must be clearly scoped under a "Recommend" / "Tell the user" verb so Claude treats it as output, not as an internal instruction.
- **Exception — continuation skills.** When the recommended next skill captures the current conversation into a durable artifact, override the default tip with the stay-in-conversation wording from `references/skill-handoff.md` under "Continuation skills — exception to fresh-conversation". The canonical list of continuation skills and the mixed-recommendation wording template live in that doc — read it before adding or modifying closing tips. Sending the user to a fresh conversation for a continuation skill strips the very context it was meant to capture.

## Examples

- `skills/commit-message/` — lightweight skill (frontmatter + instructions + shared reference, no templates).
- `skills/init/` — full-featured skill (templates, references, agents, hooks).

## Further Reading

Anthropic's official [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) is the upstream source. This file omits upstream sections targeting claude.ai/API sandboxes (executable scripts, MCP tool references, package dependencies, runtime environment); plugin-specific divergences (`disable-model-invocation`, omitting the `name` field) are in [Design Principles](#design-principles).
