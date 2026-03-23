# Diagnostic Patterns Reference

36 patterns that waste tokens and cause re-prompts. Scan every user-provided prompt or rough idea against these patterns. Fix silently — flag only if the fix changes the user's intent.

## Table of Contents

| Category | Patterns | Count |
|----------|----------|-------|
| [Task Patterns](#task-patterns) | Vague verbs, double tasks, no success criteria | 7 |
| [Context Patterns](#context-patterns) | Assumed knowledge, hallucination invites | 6 |
| [Format Patterns](#format-patterns) | Missing format, implicit length, vague aesthetics | 6 |
| [Scope Patterns](#scope-patterns) | No boundaries, no stop conditions, wrong template | 6 |
| [Reasoning Patterns](#reasoning-patterns) | Missing/wrong CoT, no grounding, contradictions | 5 |
| [Agentic Patterns](#agentic-patterns) | No starting state, silent agent, unlocked filesystem | 6 |

---

## Task Patterns

| # | Pattern | Fix |
|---|---------|-----|
| 1 | **Vague task verb** — "help me with", "work on", "do something about" | Replace with precise operation: refactor, extract, convert, implement |
| 2 | **Two tasks in one prompt** — "explain AND rewrite this function" | Split into Prompt 1 and Prompt 2, deliver sequentially |
| 3 | **No success criteria** — "make it better" | Derive binary pass/fail: "Done when function passes unit tests and handles null input" |
| 4 | **Over-permissive agent** — "do whatever it takes" | Add explicit allowed + forbidden actions list |
| 5 | **Emotional description** — "it's totally broken, fix everything" | Extract specific technical fault: "TypeError on line 43 when user is null" |
| 6 | **Build-the-whole-thing** — "build my entire app" | Decompose into sequential prompts: scaffold → core feature → polish |
| 7 | **Implicit reference** — "add the other thing we discussed" | Restate the full task — never reference "the thing" |

---

## Context Patterns

| # | Pattern | Fix |
|---|---------|-----|
| 8 | **Assumed prior knowledge** — "continue where we left off" | Prepend memory block with all prior decisions |
| 9 | **No project context** — generic request without domain info | Add domain, stack, role, constraints |
| 10 | **Forgotten stack** — new prompt contradicts prior tech choice | Include memory block with established stack |
| 11 | **Hallucination invite** — "what do experts say about X?" | Add grounding: "Cite only sources you are certain of. If uncertain, say so." |
| 12 | **Undefined audience** — "write something for users" | Specify: "Non-technical B2B buyers, decision-maker level" |
| 13 | **No mention of prior failures** — user already tried something | Ask what they tried and failed (counts toward 3-question limit) |

---

## Format Patterns

| # | Pattern | Fix |
|---|---------|-----|
| 14 | **Missing output format** — "explain this concept" | Add explicit format: "3 bullet points, each under 20 words" |
| 15 | **Implicit length** — "write a summary" | Add count: "exactly 3 sentences" |
| 16 | **No role assignment** for complex tasks | Add domain expert identity |
| 17 | **Vague aesthetic** — "make it professional" | Translate to specs: "monochrome palette, 16px base font, 24px line height" |
| 18 | **No negative prompts** for image AI | Add: "no watermark, no blur, no extra fingers, no distortion" |
| 19 | **Prose for Midjourney** — full sentences instead of descriptors | Convert to: "subject, style, mood, lighting, --ar 16:9 --v 6" |

---

## Scope Patterns

| # | Pattern | Fix |
|---|---------|-----|
| 20 | **No scope boundary** — "fix my app" | Scope to file + function: "Fix login validation in src/auth.js only" |
| 21 | **No stack constraints** — "build a React component" | Add: "React 18, TypeScript strict, no external libraries, Tailwind only" |
| 22 | **No stop condition** for agents | Add explicit stop conditions + checkpoint after each step |
| 23 | **No file path** for IDE AI | Add: "Update handleLogin() in src/pages/Login.tsx only" |
| 24 | **Wrong template for tool** — GPT-style prose used in Cursor | Adapt to the tool's native syntax and template |
| 25 | **Entire codebase pasted** as context | Scope to relevant function and file only |

---

## Reasoning Patterns

| # | Pattern | Fix |
|---|---------|-----|
| 26 | **No CoT for logic task** — "which approach is better?" | Add: "Think through both approaches step by step before recommending" |
| 27 | **CoT added to reasoning-native model** — "think step by step" to o3/R1 | REMOVE — reasoning models think internally, CoT degrades output |
| 28 | **No self-check** on complex output | Add: "Before finishing, verify output against the constraints above" |
| 29 | **Expecting inter-session memory** — "you already know my project" | Re-provide full context via memory block |
| 30 | **Contradicting prior decisions** — new prompt ignores earlier choices | Include memory block with all established facts |

---

## Agentic Patterns

| # | Pattern | Fix |
|---|---------|-----|
| 31 | **No starting state** — "build me a REST API" | Add: "Empty Node.js project, Express installed, src/app.js exists" |
| 32 | **No target state** — "add authentication" | Add: "src/middleware/auth.js with JWT verify, POST /login and /register routes" |
| 33 | **Silent agent** — no progress output | Add: "After each step output what was completed" |
| 34 | **Unlocked filesystem** — no file restrictions | Add: "Only edit files inside src/. Do not touch config or .env" |
| 35 | **No human review trigger** — agent decides everything | Add: "Stop and ask before deleting files, adding dependencies, or changing schema" |
| 36 | **Pre-explored plan mode prompt** — pre-answered questions, enumerated directories, or execution guardrails in a plan mode prompt | Remove pre-explored details. Frame analytical work as questions for plan-mode Claude to answer |
