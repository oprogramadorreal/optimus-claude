# optimus:init

The foundation skill of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. Analyzes your project and sets up Claude Code for optimal performance: a compact CLAUDE.md with progressive-disclosure docs, coding guidelines, auto-format hooks, and test infrastructure — all inside the project directory, so the setup travels with the repo via git.

What makes a good developer productive in a codebase also makes Claude Code productive: clean code, good test coverage, and clear documentation. Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, LLM performance [degrades sharply](https://arxiv.org/abs/2510.05381) as context grows, and Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code is giving it a way to verify its own work.

## What it does

1. **Detects project context** with a dedicated analysis agent — tech stack, package manager, commands, structure (single project / monorepo / multi-repo workspace), existing docs, test infrastructure, and skill-authoring stacks. You confirm the detection summary before anything is written. Empty directory? It offers to scaffold a new project first using official stack tooling (Vite, Cargo, Flutter, .NET CLI, ...).
2. **Generates CLAUDE.md** following [research-backed practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md): a ~60-line root file within the model's peak attention window, with details pushed to docs loaded on demand. Monorepos get a scoped CLAUDE.md per subproject; multi-repo workspaces get a fully self-contained `.claude/` per repo.
3. **Installs formatter hooks** per detected stack (Python, Node.js, Rust, Go, C#, Java, C/C++, Dart/Flutter — other stacks via best-effort web search). Files are auto-formatted after every edit, preventing formatting drift. Formatters not already in your dependencies are only installed with your approval.
4. **Sets up test infrastructure** — health-checks an existing suite, or offers to install a framework and coverage tooling (with approval). Generates `testing.md`, wires test commands into CLAUDE.md, and appends a README testing section. If the baseline is broken, it says so honestly instead of papering over it.
5. **Creates scoped guideline docs** — `coding-guidelines.md` always; `styling.md`, `architecture.md`, and `skill-writing-guidelines.md` when the project's shape calls for them. Skill-authoring projects (Claude Code plugins, prompt libraries) are a first-class stack: review and refactor skills route markdown instruction files through the skill-writing lens automatically.
6. **Syncs your existing docs** — cross-checks README, CONTRIBUTING, etc. against source code and proposes surgical fixes for factual contradictions only. Stale docs in context actively degrade output quality.

## Optional add-ons

Offered at the end of setup:

- **Safety guardrails** — a PreToolUse hook plus permission defaults for low-prompt autonomous work: writes outside the project prompt for approval, deletes outside are blocked, precious unversioned files (`.env`, keys, local databases) are protected, and git commit/push/rebase/merge are blocked on protected branches. Defense-in-depth, not OS-level sandboxing — the deny list blocks ~30 destructive command patterns, and everything merges cleanly into an existing `settings.json`.
- **HOW-TO-RUN.md** — a developer onboarding doc (fresh clone to running project) built exclusively from verified commands: manifest scripts, lock files, config files, web-verified Docker images. It never guesses ports, versions, or paths.

## Re-running

Safe and encouraged — after major changes, new stack components, or plugin updates. An audit agent compares existing docs against the current project state and classifies content as Outdated / Missing / Accurate / User-added; you choose what to apply. Content is only called outdated when source code directly contradicts it, and **user-added content is never discarded** — even on a full regeneration. `.claude/.optimus-version` tracks which plugin version last ran, so template improvements surface on update.

Note the split write policies: hooks and `coding-guidelines.md` are always refreshed verbatim from templates (use `git diff` to review); `testing.md`, `styling.md`, `architecture.md`, and `skill-writing-guidelines.md` are treated as yours — init proposes changes rather than overwriting. Project-specific rules that must survive re-runs belong in `.claude/CLAUDE.md` or those customizable docs, not in `coding-guidelines.md`.

## Usage

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin — see the [main README](../../README.md) for installation.

```
/optimus:init
/optimus:init focus on the backend services
```

## Generated files

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Project overview, commands, doc references |
| `.claude/settings.json` | Hook registration and (with guardrails) permission rules — always merged, never overwritten |
| `.claude/docs/coding-guidelines.md` | Coding standards (the control surface for the code-simplifier agent, `/optimus:refactor`, and `/optimus:code-review`) |
| `.claude/docs/testing.md`, `styling.md`, `architecture.md` | Scoped conventions, created when detected |
| `.claude/docs/skill-writing-guidelines.md` | Review lens for markdown instruction files (skill-authoring projects) |
| `.claude/hooks/` | Auto-format hooks; `restrict-paths.sh` with guardrails |
| `HOW-TO-RUN.md` | Optional onboarding doc at the project root |
| `.claude/.optimus-version` | Plugin version that last generated these files |

Monorepos add a `CLAUDE.md` and `docs/` per subproject. Multi-repo workspaces get a complete `.claude/` per repo plus a lightweight, local-only workspace `CLAUDE.md`.

## Customization

Start with `SKILL.md` for the full flow. The CLAUDE.md and doc templates live in `templates/`, formatter hooks in `templates/hooks/`, and the detection/provisioning procedures in `references/`. The plugin-level [code-simplifier](../../agents/code-simplifier.md) and [test-guardian](../../agents/test-guardian.md) agents enforce whatever your generated guideline docs say — editing those docs directly changes what the quality tools flag.

## After init

Run `/optimus:unit-test` to build real coverage on the fresh setup — or `/optimus:spec` first if you scaffolded a brand-new project. `/optimus:reset` uninstalls everything init created.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git

## License

[MIT](../../LICENSE)
