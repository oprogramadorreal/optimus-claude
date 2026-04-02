# optimus:prompt

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that crafts optimized, copy-ready prompts for any AI tool — from LLMs and coding agents to image generators and workflow automation.

A well-crafted prompt is optimal context. Vague prompts waste tokens and credits through iterative re-prompting; sharp prompts where every word is load-bearing get the right output on the first attempt. This skill applies the same principle that drives all of optimus: **context quality determines AI output quality**.

## Features

- **9-dimension intent extraction** — silently analyzes task, target tool, output format, constraints, input, context, audience, success criteria, and examples before writing a single word
- **30+ AI tool profiles** — tool-specific routing for LLMs (Claude, ChatGPT, Gemini, o3), IDE AI (Cursor, Copilot, Claude Code), image generators (Midjourney, DALL-E, Stable Diffusion), video AI, 3D AI, voice AI, workflow automation, and more
- **13 prompt templates** — auto-selected architecture (RTF, CO-STAR, RISEN, ReAct, Exploration + Plan, Visual Descriptor, etc.) based on task type and target tool
- **36 diagnostic patterns** — detects and fixes credit-killing patterns (vague verbs, missing scope, no stop conditions, wrong template for tool)
- **5 safe techniques only** — role assignment, few-shot examples, XML structure, grounding anchors, Chain of Thought. Explicitly excludes fabrication-prone methods (Tree of Thought, Graph of Thought, Mixture of Experts, Universal Self-Consistency, prompt chaining)
- **Multilingual input** — write your request in any language. The skill communicates in your language and generates the prompt in English by default (better AI tool performance) with option to keep your original language
- **Token efficiency audit** — every sentence must be load-bearing, no vague adjectives, strongest signal words, explicit format and scope
- **Prompt Decompiler mode** — paste an existing prompt to break it down, adapt it for a different tool, simplify it, or split it

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

Invoke with `/optimus:prompt` followed by what you need:

```
/optimus:prompt Write a prompt for Cursor to refactor my auth module
```

```
/optimus:prompt I need a Claude Code prompt to build a REST API with Express and Prisma
```

```
/optimus:prompt Create a prompt for Claude Code plan mode to explore and plan adding WebSocket support
```

```
/optimus:prompt Generate a Midjourney prompt for a cyberpunk cityscape at night
```

```
/optimus:prompt Here's a bad prompt I wrote for GPT, fix it: [paste prompt]
```

Works with any language — describe what you need in Portuguese, Spanish, or any language you're comfortable with:

```
/optimus:prompt Preciso de um prompt para o Cursor refatorar meu modulo de autenticacao
```

## When to Use

- Writing a prompt for any AI tool (Claude, ChatGPT, Cursor, Midjourney, Zapier, etc.)
- Fixing a prompt that produces wrong or inconsistent output
- Adapting a prompt from one tool to another (e.g., ChatGPT prompt → Claude Code prompt)
- Breaking down a complex prompt into sequential parts
- Improving a prompt that wastes tokens through vagueness

## When NOT to Use

- Quick, simple questions to Claude that don't need structured prompting
- Tasks where you're already getting good results — if it works, don't optimize it
- Generating CLAUDE.md files or project documentation — use `/optimus:init` instead

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `/optimus:init` | Init creates project-level context (CLAUDE.md, guidelines). Prompt creates task-level context (individual prompts for AI tools). |
| `/optimus:commit` | After crafting a prompt that produces code changes, use commit to save the work. |
| `/optimus:tdd` | For code generation prompts, TDD ensures the generated code is correct via tests. |
| `/optimus:brainstorm` | Brainstorm generates plan-mode prompts inline for the brainstorm→plan→tdd chain. Use `/optimus:prompt` directly when you need prompts for other AI tools or non-brainstorm workflows. |
| `/optimus:code-review` | Review code that was generated from a crafted prompt. |

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | 9-step prompt crafting workflow |
| `references/tool-routing.md` | Tool-specific routing for 30+ AI tools |
| `references/templates.md` | 13 prompt architecture templates |
| `references/diagnostic-patterns.md` | 36 credit-killing pattern checklist |

## Acknowledgements

The prompt engineering techniques in this skill — intent extraction, tool routing, diagnostic patterns, prompt templates, safe/excluded technique classification — are adapted from [prompt-master](https://github.com/nidhinjs/prompt-master) by [@nidhinjs](https://github.com/nidhinjs), licensed under MIT. This skill adds multilingual input support, optimus plugin integration, and progressive disclosure via reference files.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+

## License

[MIT](../../LICENSE)
