# Skill-writing guidelines

## Foundation

These quality principles apply to skill authoring just as they apply to code:

- **Follow Existing Patterns** — match existing skill structure, frontmatter conventions, and reference patterns. Prefer established approaches over novel ones. When introducing a different pattern, apply it consistently — don't leave skills in a mixed state.
- **KISS** — default to the simplest instructions that meet current requirements. Don't add steps or branches for hypothetical scenarios. Remove dead steps — unused branches, commented-out instructions, and redundant clarifications add noise without value. Safety procedures (validation rules, command allowlists, user-approval gates) and explicit behavioral constraints are requirements — their detail is justified, not a simplicity violation.
- **SRP** — each skill focused on one concern, each step on one action. When a step handles multiple concerns or mixes abstraction levels, decompose it.
- **Intention-Revealing Names** — skill names, template files, and reference docs should convey purpose without tracing through content. Avoid generic names like `helper.md`, `utils.md`, or `doc2.md`.
- **Pragmatic Abstractions** — extract shared references when 2+ skills reuse a procedure. Don't add indirection for its own sake. Don't extract for hypothetical future reuse.

## Design Principles

- `disable-model-invocation: true` required on all skills — skills are tools users explicitly reach for, never auto-triggered. The plugin enhances Claude Code without changing its default behavior behind the user's back.
- Do NOT add a `name` field to SKILL.md frontmatter — it strips the plugin namespace prefix ([anthropics/claude-code#22063](https://github.com/anthropics/claude-code/issues/22063)).
- `coding-guidelines.md` (the template at `skills/init/templates/docs/`) is the single source of truth for code quality rules — skills and agents must reference it, never duplicate its principles inline.

## Writing Style

- Imperative step-by-step instructions, not conversational prose.
- Keep SKILL.md body under 500 lines — move detailed reference material to separate files.
- Omit generic tool instructions Claude already has (how to read files, run commands, search code). Include behavioral rules, safety constraints, and domain procedures — these are requirements, not hints Claude can infer.
- No time-sensitive information; consistent terminology throughout.

## Description Quality (frontmatter)

- Must describe both WHAT the skill does AND WHEN to use it.
- Include specific keywords users would naturally say.
- Be concrete and specific, not vague.
- Max 1024 characters.

## Progressive Disclosure

- Load only metadata (name + description) at startup.
- Load full SKILL.md when skill is invoked.
- Load reference files only as needed within the skill's execution.
- Reference depth should not exceed two levels from SKILL.md (SKILL→A→B maximum). If you find yourself needing A→B→C→D, restructure by flattening the chain (preferred) — make SKILL.md reference the deeper files directly. Only inline content when the extracted file is small, single-use, and tightly coupled to its parent; otherwise inlining violates SRP by mixing concerns in one file. Circular references between files are never allowed.

## Directory Layout

- `SKILL.md` (required) + `README.md` (required).
- Templates in `templates/` (`hooks/`, `agents/`, `docs/` subdirs).
- Reference docs in `references/`.
- When agents use prompt templates, externalize to `references/agent-prompts.md` — don't inline them in SKILL.md (see `skills/code-review/` for the pattern).

## Shared References

- When a procedure is used by 2+ skills, extract to a reference file owned by the canonical skill.
- Consuming skills read the reference and apply their own policy — this avoids logic duplication while keeping each skill self-contained.
- Examples: `multi-repo-detection.md` (owned by init), `platform-detection.md` (owned by pr).

## Documentation

- Every skill must have a user-facing `README.md`.
- After any skill change, verify root `README.md` and the skill's `README.md` still reflect current behavior.
- Add new skills to the Skills section in root `README.md`.

## Next Step

Every skill must end with a recommendation for the next logical optimus skill. This guides the user through the workflow and increases plugin adoption.

- Choose the next skill based on the outcome (e.g., after fixing issues → commit; after committing → PR).
- If multiple paths are possible, present them conditionally (e.g., "if X → skill A; if Y → skill B").
- Always include the fresh-conversation tip as part of the recommendation to the user — e.g., "Recommend running `/optimus:X` to do Y. **Tip:** for best results, start a fresh conversation for the next skill — each skill gathers its own context from scratch." The tip must be clearly scoped under a "Recommend" / "Tell the user" verb so Claude treats it as output, not as an internal instruction.

## Examples

- `skills/commit-message/` — minimal skill (frontmatter + instructions, no templates).
- `skills/init/` — full-featured skill (templates, references, agents, hooks).
