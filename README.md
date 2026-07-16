<div align="center">
  <img src="assets/banner.png" alt="optimus-claude" width="600">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Claude_Code-1.0.33+-blueviolet" alt="Claude Code">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey" alt="Platform">
</p>

**A Claude Code plugin that sets up your project for effective AI-assisted engineering.**

---

**The problem:** AI amplifies whatever it finds. Messy code leads to messier AI-generated code, which becomes the new context for even worse output — a vicious cycle that compounds faster than any human could create technical debt. Without maintained context, any AI coding tool's quality degrades with every file it reads.

**The solution:** Optimus Claude generates project-tailored context — CLAUDE.md, coding guidelines, formatter hooks, test infrastructure — from your actual codebase, then enforces those standards in every quality workflow: spec-driven design, test-driven implementation, guideline-aware review and refactoring, and a resumable deep-fix loop with deterministic test bisection.

*Use it regularly and your project stays clean, consistent, tested, and well-documented — exactly the conditions where Claude Code performs at its prime.*

## Quick Start

Run these commands inside Claude Code:

```shell
/plugin marketplace add https://github.com/oprogramadorreal/optimus-claude.git
/plugin install optimus@optimus-claude
```

Then start a new session and type `/optimus:init` in any project directory.

> Having trouble? See [Troubleshooting](#troubleshooting).

## Skills

One story in eight skills: **generate your project's standards, enforce them in every quality pass, sustain the fix loop across sessions.**

| Skill | Description |
|-------|-------------|
| [`/optimus:init`](skills/init/README.md) | Generates and audits project context: CLAUDE.md, coding guidelines, formatter hooks, test infrastructure. Optional extras: safety guardrails (branch-protection / precious-file hook) and a verified HOW-TO-RUN.md onboarding doc. Re-run to audit and refresh. |
| [`/optimus:spec`](skills/spec/README.md) | The design front door — an inline idea, a JIRA ticket (read-only via MCP), or a greenfield product-docs scaffold becomes an explored, approved spec in `docs/specs/` that `/optimus:tdd` consumes automatically. |
| [`/optimus:tdd`](skills/tdd/README.md) | Test-driven implementation through Red-Green-Refactor cycles: failing test first (the Iron Law), minimal green, guideline-driven refactor, one commit per behavior, quality-gate agents at the end. |
| [`/optimus:unit-test`](skills/unit-test/README.md) | Discovers coverage gaps and writes convention-following tests. Never refactors source code; flags structurally untestable code instead. |
| [`/optimus:refactor`](skills/refactor/README.md) | Project-wide refactoring against your own coding guidelines and testability barriers, using parallel analysis agents — the project-wide complement to the built-in `/simplify`. |
| [`/optimus:code-review`](skills/code-review/README.md) | Reviews local changes, branch diffs, or PRs/MRs against *your* guidelines with parallel agents and independent finding validation — the project-standards complement to the built-in `/code-review`. |
| [`/optimus:deep`](skills/deep/README.md) | Resumable multi-iteration auto-fix orchestrator: `deep review`, `deep refactor`, or `deep coverage`. Fresh subagent per iteration, deterministic per-fix test bisection, checkpoint commits, on-disk resumable state. |
| [`/optimus:reset`](skills/reset/README.md) | Removes everything init installed — classifies each file before deletion and always asks for confirmation. |

## How It Works

`/optimus:init` analyzes your codebase and generates constraint docs — coding guidelines, CLAUDE.md, formatter hooks, and test infrastructure — into `.claude/`. These travel with the repo via git, so every teammate benefits without installing the plugin. If your project's "source code" includes markdown instructions for an AI agent (a Claude Code plugin, a prompt library), init also installs `skill-writing-guidelines.md`, and the review/refactor skills route instruction files through that lens.

From then on, every skill enforces those project-defined standards: `/optimus:code-review` checks *your* naming conventions and architectural patterns alongside bugs and security; `/optimus:tdd` applies the guidelines in its Refactor step; `/optimus:refactor` uses them as its quality lens; `/optimus:unit-test` follows your testing conventions. A shared [verification protocol](skills/init/references/verification-protocol.md) requires evidence before any completion claim.

**A typical flow:** `/optimus:init` once → `/optimus:spec` to design a feature → `/optimus:tdd` to build it test-first (it auto-detects the approved spec) → open a PR → `/optimus:code-review` in a fresh conversation. For codebase-wide improvement, `/optimus:unit-test` and `/optimus:refactor` run standalone, and `/optimus:deep` automates either one (or review) as a resumable fix loop that runs tests after every iteration and bisects failures. After major changes, re-run `/optimus:init` to audit and refresh the docs.

**Design principles:** skills never auto-trigger (`disable-model-invocation: true` everywhere). The only always-on component is a lightweight, read-only SessionStart hook that surfaces project state; the plugin's two quality agents (code-simplifier, test-guardian) act only when Claude or a skill dispatches them. Generated output is project-scoped, self-contained, and version-controlled.

## Why It Works

What makes a good developer productive also makes Claude Code productive: **clean code, good tests, and clear docs.**

Research backs this up: AI tools introduce [30%+ more defects](https://arxiv.org/abs/2601.02200) on poorly maintained code, and LLM performance [degrades up to 85%](https://arxiv.org/abs/2510.05381) as context length grows. Clean, DRY code with meaningful names keeps context lean and gives the LLM better semantic signals. The [2025 DORA report](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) puts it simply: AI amplifies existing practices, good or bad. And [providing LLMs with tests alongside tasks consistently improves code generation](https://arxiv.org/abs/2402.13521) — tests enable self-correction, which is Anthropic's [#1 best practice](https://code.claude.com/docs/en/best-practices) for Claude Code ("give Claude a way to verify its work").

AI assistants also tend toward [sycophancy](https://blog.scielo.org/en/2026/03/13/sycophancy-in-ai-the-risk-of-complacency/) — validating ideas without pushback; a [2025 METR trial](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) found developers using AI were [19% slower yet believed they were faster](https://arxiv.org/abs/2507.09089). This plugin counters that: project-defined standards are the source of truth, the verification protocol demands evidence before completion claims, code review runs independent duplicate guideline agents and validates each finding against the actual code, and TDD makes tests define correctness instead of the AI's confidence.

## Complementary Tools

optimus-claude works alongside official tooling rather than replacing it. The built-in `/code-review` reviews diffs for bugs in fresh subagents — `/optimus:code-review` adds your project's guideline lens. The built-in `/simplify` cleans up per-change — `/optimus:refactor` restructures project-wide. Claude Code's [dynamic workflows](https://code.claude.com/docs/en/workflows) handle one-off multi-agent fan-outs (including implementing an `/optimus:spec` output in parallel) — `/optimus:deep` is the persistent, resumable, test-bisecting fix loop those don't provide. [`/goal`](https://code.claude.com/docs/en/goal) auto-iterates toward a session-scoped condition with a read-only evaluator — `/optimus:deep` adds deterministic bisection, fresh context per iteration, and on-disk resumable state. For fully autonomous runs, use Claude Code's [sandboxing](https://code.claude.com/docs/en/sandboxing) or containers.

## Troubleshooting

### Windows: SSL certificate error during install

If you see `SSL certificate OpenSSL verify result: unable to get local issuer certificate` when running `/plugin marketplace add`, Git for Windows is using an outdated OpenSSL CA bundle. Switch to the native Windows certificate store and retry:

```shell
git config --global http.sslBackend schannel
```

### Upgrading from 2.x

3.0 consolidated 22 skills into 8. If you scripted or habitually used a removed skill:

| Removed in 3.0 | Use instead |
|----------------|-------------|
| `/optimus:code-review-deep` / `refactor-deep` / `unit-test-deep` | `/optimus:deep review` / `deep refactor` / `deep coverage` (same harness, same `--resume` / `--yes` / `--no-commit` flags) |
| `/optimus:brainstorm`, `/optimus:spec-init`, `/optimus:jira` | `/optimus:spec` (inline idea, ticket key, or greenfield scaffold) |
| `/optimus:permissions` | `/optimus:init` (optional guardrails step) |
| `/optimus:how-to-run` | `/optimus:init` (optional HOW-TO-RUN.md step) |
| `/optimus:commit`, `/optimus:commit-message`, `/optimus:branch`, `/optimus:worktree`, `/optimus:pr`, `/optimus:prompt`, `/optimus:workflow`, `/optimus:handoff` | Claude Code does these natively — just ask (commit messages, branches, worktrees, PRs, prompt drafting, dynamic workflows, handoff notes). |

Existing `.claude/` files generated by 2.x keep working; re-run `/optimus:init` to refresh them.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for project structure, skill anatomy, feature-branch testing, and local development setup.

## Research & References

- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) — Anthropic: verification as #1 practice, compact CLAUDE.md, deterministic hooks, custom subagents
- [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — Anthropic: conciseness, degrees of freedom, progressive disclosure
- [How TDD Amplifies AI Success](https://cloud.google.com/discover/how-test-driven-development-amplifies-ai-success) — DORA Report 2025: AI adoption increases delivery instability; TDD provides the control system
- [Code for Machines, Not Just Humans](https://arxiv.org/abs/2601.02200) — Borg et al. 2026: AI defect risk increases 30%+ on unhealthy code
- [AI-Friendly Code Design](https://www.thoughtworks.com/radar/techniques/ai-friendly-code-design) — Thoughtworks Tech Radar Vol. 32: "good software design for humans also benefits AI"
- [Context Length Alone Hurts LLM Performance](https://arxiv.org/abs/2510.05381) — Du et al. 2025: 13.9%–85% degradation as input length increases
- [Test-Driven Development for Code Generation](https://arxiv.org/abs/2402.13521) — Mathews et al. 2024: providing LLMs with tests alongside problem statements consistently improves outcomes
- [AI Developer Productivity: Perception vs. Reality](https://arxiv.org/abs/2507.09089) — METR 2025: experienced developers were 19% slower with AI but believed they were 24% faster
- [Sycophancy in AI: The Risk of Complacency](https://blog.scielo.org/en/2026/03/13/sycophancy-in-ai-the-risk-of-complacency/) — SciELO 2026: AI sycophancy increases short-term productivity but reduces quality of collaborative work
