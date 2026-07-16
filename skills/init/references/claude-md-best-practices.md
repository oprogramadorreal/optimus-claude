# CLAUDE.md Best Practices

Research-backed guidance for generating effective CLAUDE.md files (drawing on the HumanLayer engineering blog and Anthropic's Claude Code best practices). CLAUDE.md is the only file automatically included in every conversation — one of the highest-leverage points in a Claude Code setup, and every line affects every task.

## Size and instruction budget

- Frontier LLMs follow roughly 150–200 instructions with reasonable consistency, and Claude Code's system prompt already consumes a large share of that budget.
- Target: **under 60 lines**. Hard ceiling: 300. Every line must earn its place.
- Include only instructions that apply to essentially all tasks. Task-specific commands, schema dumps, and rarely-needed detail don't just waste space — non-universal content trains the model to ignore the file entirely (Claude Code's system reminders tell it to use only "highly relevant" context).

## Structure: WHAT / WHY / HOW

- **WHAT** — tech stack, project structure, codebase map (especially in monorepos: which apps and packages exist and what each is for).
- **WHY** — project purpose and the reasoning behind architectural decisions and conventions.
- **HOW** — package manager, build/test/lint commands, verification methods.

## Progressive disclosure

Keep CLAUDE.md an index, not an encyclopedia. Push details into separate docs (`testing.md`, `architecture.md`, `styling.md`) referenced with brief descriptions — Claude loads them when the task needs them. Use `file:line` pointers instead of embedded code snippets; embedded code goes stale.

## What NOT to include

- **Code style rules.** Never send an LLM to do a linter's job — formatter hooks are cheaper, faster, and deterministic, and style instructions burn instruction budget.
- **Generic boilerplate.** Template-guided generation is fine only when filled with real, project-specific analysis; content that could describe any project dilutes the file.

## Monorepo pattern

- Root CLAUDE.md is an orchestrator: subproject table (path, purpose, stack), workspace-wide commands only, references to each subproject's CLAUDE.md and shared docs. Still under 60 lines.
- Each subproject gets its own CLAUDE.md in its directory (Claude Code auto-discovers it when working there): same WHAT/WHY/HOW scoped to that subproject, references to its local `docs/`, parent monorepo named for context. Under 60 lines each.
- Shared docs (coding guidelines) live at root `.claude/docs/` only; subproject-specific docs (testing, styling, architecture) live in each subproject's `docs/`, scoped to its stack.

## Multi-repo workspace pattern

Each independent repo under the shared parent gets its own full `.claude/` setup, exactly as if init ran inside it — fully self-contained, so a teammate cloning one repo gets the complete experience. A lightweight parent `CLAUDE.md` (local-only, never version-controlled) maps the repos and cross-repo conventions; nothing else is shared at the workspace root.

## Quality checklist

- [ ] Under 60 lines, only universally-applicable instructions
- [ ] WHAT/WHY/HOW structure; details delegated to separate docs
- [ ] `file:line` references, no code snippets, no style rules
- [ ] Every line reflects the actual project, not a template
- [ ] Monorepo: root file orchestrates; each subproject has its own scoped file
- [ ] Multi-repo: each repo self-contained; parent file local-only
