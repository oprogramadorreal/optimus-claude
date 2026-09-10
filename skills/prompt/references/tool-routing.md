# Tool Routing Reference

Prompt-specific guidance for each AI tool category. Load only the section matching the target tool — do not load the entire file.

## Table of Contents

| Category | Tools |
|----------|-------|
| [General-Purpose LLMs](#general-purpose-llms) | Claude, GPT-6 Astra, ChatGPT / GPT-5.x, Gemini 2.x / 3 Pro, MiniMax |
| [Reasoning-Native LLMs](#reasoning-native-llms) | o3 / o4-mini, DeepSeek-R1, Qwen3 thinking mode |
| [Open-Weight LLMs](#open-weight-llms) | Qwen 2.5, Llama, Mistral, Ollama |
| [IDE AI](#ide-ai) | Claude Code, OpenAI Codex, Cursor / Windsurf, Cline, GitHub Copilot, Antigravity |
| [Agentic AI](#agentic-ai) | Devin / SWE-agent, Bolt / v0 / Lovable / Figma Make / Google Stitch |
| [Computer-Use Agents](#computer-use-agents) | Perplexity Comet, OpenAI Atlas, Claude in Chrome |
| [Research / Orchestration](#research--orchestration) | Perplexity, Manus, Perplexity Computer |
| [Image AI — Generation](#image-ai--generation) | Midjourney, OpenAI image tools, Stable Diffusion, SeeDream |
| [Image AI — Editing](#image-ai--editing) | Reference image modification workflows |
| [Image AI — ComfyUI](#image-ai--comfyui) | Node-based workflows |
| [3D AI](#3d-ai) | Meshy, Tripo, Rodin, Unity AI, BlenderGPT |
| [Video AI](#video-ai) | Sora, Runway, Kling, LTX Video, Dream Machine, Seedance 2 |
| [Voice AI](#voice-ai) | ElevenLabs |
| [Workflow AI](#workflow-ai) | Zapier, Make, n8n |

## General-Purpose LLMs

Use these profiles as starting defaults, not proof of performance on every model and task. Request task-specific intermediate outputs when useful, without asking for private reasoning transcripts. Follow the selected model's current official guidance and the host's available controls before adding generic reasoning scaffolding (Template E).

### Claude (claude.ai, Claude API)

Covers the Claude 5 family (Opus 5, Sonnet 5, Fable 5 and 5.1) and Claude 4.x. Where they differ, the bullet says so.

- Be explicit and specific — Claude follows instructions literally, not by inference; always specify output format and length
- XML tags for complex multi-section prompts: `<context>`, `<task>`, `<constraints>`, `<output_format>`
- Provide context and reasoning WHY, not just WHAT — Claude generalizes better from explanations
- For complex or multi-step tasks, front-load everything in one turn — intent, constraints, acceptance criteria, relevant files; extra back-and-forth adds reasoning overhead and cost
- Don't add "think step by step" or a fixed thinking budget — current Claude calibrates reasoning depth automatically. On the API, depth is the `effort` setting, not prompt text; in claude.ai, where the user has no such control, a one-line nudge is the only lever: "Think carefully before responding" (more) or "Prioritize responding quickly" (less)
- Prefer concrete acceptance criteria and external checks (a test suite, a schema, a live API) over repeated generic self-check instructions. Keep a targeted check when it addresses an observed failure. For a long autonomous build on Fable 5.1, state how its checking harness validates progress against the spec; evaluate changes to that cadence rather than assuming self-verification always helps or never helps.
- **Bound scope with intent, not prohibitions.** Claude 5 models can widen a task past what was asked (Claude 4.x and Fable 5 over-tidy the same way). One line covers it: *"Deliver what was asked, at the scope intended. Make routine judgment calls yourself; check in only when two readings of the request would lead to materially different work. If a better approach exists, say so in a sentence and continue as asked."*
- **Length is a separate lever from reasoning.** Claude 5 responses run longer by default, and lowering reasoning effort does not shorten them — ask directly: *"Keep responses focused and brief; spend most of the response on the main answer."* When the prompt produces a written file, add: *"Match the document's length to the substance — no filler sections, redundant summaries, or boilerplate."*
- Don't add anti-formatting rules ("no bullets", "no headers", "no bold") — Fable 5.1 already under-formats, so they strip formatting the reader wanted. Say when formatting is appropriate instead: *"Use lists and headers when the content is multifaceted enough that they help; plain prose for simple answers and conversational exchanges."*
- Don't instruct Fable 5.x to echo or transcribe its reasoning as output text — the reasoning-extraction safeguard can refuse the request (and fall back to Opus where fallbacks are configured)

### GPT-6 Astra

Exact model identifier: `gpt-6-astra`. Keep this target when the user requests it; do not silently route it to GPT-5.x or a Claude model.

- State the intended outcome, scope, existing authorization, and externally checkable completion criteria. Let routine implementation choices proceed; ask when an unresolved choice materially changes the requested work.
- Resolve conflicting project/skill instructions using the host's instruction hierarchy and the user's explicit task. Preserve approved work across follow-ups instead of introducing another approval gate for the same action.
- Delegate substantial independent work when useful, supply its context, and continue local work while it runs. Match verification to the change and required checks; do not infer a need for broader testing merely from model capability.
- Use host-supported effort/tool controls, not invented prompt commands or API transport settings. For Codex, also apply the host entry below.

Source: [official Astra prompting guidance](https://developers.openai.com/api/docs/guides/latest-model), checked 2026-09-09. These are starting recommendations; task comparisons determine whether further guidance improves results.

### ChatGPT / GPT-5.x

- Start with the smallest prompt that achieves the goal — add structure only when needed; handles dense, compact instruction well
- Be explicit about the output contract: format, length, what "done" looks like; state tool-use expectations if the model has tools
- Constrain verbosity when needed: "Respond in under 150 words. No preamble. No caveats."

### Gemini 2.x / Gemini 3 Pro

- Prone to hallucinated citations — always add "Cite only sources you are certain of. If uncertain, say [uncertain]."
- Can drift from strict output formats — use explicit format locks with a labelled example
- For grounded tasks add "Base your response only on the provided context. Do not extrapolate."
- Strong at long-context and multimodal — leverage the large context window for document-heavy prompts

### MiniMax (M3 / M2.7)

- OpenAI-compatible API — prompts that work with GPT transfer directly; for function calling, include OpenAI-style tool schemas
- Strong at instruction following, structured (JSON) output, and long-context synthesis; M2.7-highspeed is tuned for latency-sensitive tasks
- Temperature must be in the range [0, 1] — values above 1 fail
- May emit reasoning in `<think>` tags — add "Output only the final answer, no reasoning tags." if visible thinking is unwanted

## Reasoning-Native LLMs

These models perform internal reasoning. Prefer a clear task and output contract over generic "think step by step" scaffolding; do not request private reasoning transcripts. Keep concrete intermediate outputs when they are part of the task. Evaluate changes against the specific model and task rather than asserting universal degradation.

### o3 / o4-mini

- Start with clear instructions stating the task and completion criteria; add examples or constraints when the task needs them, without an arbitrary word cap
- Prefer zero-shot first — add few-shot only if strictly needed

### DeepSeek-R1

- Short clean instructions — goal and output format only
- Outputs reasoning in `<think>` tags by default — add "Output only the final answer, no reasoning." if needed

### Qwen3 (thinking mode)

- Thinking mode (/think or enable_thinking=True): treat exactly like o3 — short clean instructions, no scaffolding
- Non-thinking mode: treat like Qwen 2.5 instruct — full structure, explicit format, role assignment

## Open-Weight LLMs

### Qwen 2.5 (instruct variants)

- Excellent instruction following, JSON output, structured data — works well with explicit format specs including JSON schemas
- Provide a clear system prompt defining the role; shorter focused prompts outperform long complex ones

### Llama / Mistral / open-weight LLMs

- Shorter prompts with simple flat structure — these models lose coherence with deeply nested instructions
- Be more explicit than with Claude or GPT — instruction following is weaker; always include a role in the system prompt

### Ollama (local model deployment)

- ALWAYS ask which model is running before writing — Llama3, Mistral, Qwen2.5, CodeLlama behave differently
- System prompt is the most impactful lever — include it in the output so the user can set it in their Modelfile
- Shorter simpler prompts outperform complex ones — local models lose coherence with deep nesting
- Temperature 0.1 for coding/deterministic tasks, 0.7-0.8 for creative tasks
- For coding: CodeLlama or Qwen2.5-Coder, not general Llama

## IDE AI

Every entry below: anchor each instruction to a path — never a global instruction without a file or directory anchor. Split work that spans several independent changes into sequential prompts per the output contract in SKILL.md.

### Claude Code

- Agentic — runs tools, edits files, executes commands autonomously. Structure per Template H: starting state + target state + allowed/forbidden actions + stop conditions + checkpoints
- Stop conditions are MANDATORY — runaway loops are the biggest credit killer
- Apply the [Claude entry](#claude-claudeai-claude-api), including scope, length, and evidence-based verification; effort and thinking depth are host-managed, so never invent an effort command or thinking budget in the task prompt
- Delegation bias differs by model. Opus 5 over-delegates — cap it: *"Delegate only for large, genuinely independent tracks of work. Don't delegate what you can finish in a handful of tool calls. Keep spawn counts low."* Fable 5.1's parallel subagents are dependable — say when delegation is wanted and let it keep working while they run: *"Delegate independent subtasks to subagents and keep working while they run; intervene if one goes off track or lacks context."* On either model, never use a subagent to verify its own work.
- Narration cadence differs by model — Opus 5 narrates readily, Fable 5.1 goes quiet during long tool chains — so describe the shape you want rather than banning or demanding updates: *"Say in one sentence what you're about to do before your first tool call; while working, update on something important or a change of direction; close with a short recap that stands on its own — what you found, what you did, what's next."*
- Carry forward explicit authorization for edits, dependencies, and schema work. Ask before consequential actions outside that authorization or when an unresolved choice changes the scope

### OpenAI Codex

- Use Template H for scoped implementation; for an audit or plan, state the requested read/write boundary and deliverable. Do not transplant Claude's `/goal`, `/workflows`, `AskUserQuestion`, or plan-mode transitions as literal Codex commands.
- Read the project's discovered AGENTS instructions and the files they route to. For Optimus, invoke the explicitly requested skill with the host's `$optimus:<skill>` syntax and resolve shared references from the installed plugin root.
- Use the tools actually available in the current Codex surface and mode. Ask through its question tool when available, otherwise plain text; prose cannot grant permissions or change plan mode. Bound delegation to available capacity and pass each worker the task, context, and required output.
- Preserve prior user authorization and complete independent work while a real decision is pending. Keep important task state in the requested artifact when a handoff/resume needs it; do not assume another session has this conversation.
- If the selected model is GPT-6 Astra, also use its model entry above. Host tools, memory, approvals, and plugin availability are separate from model capabilities; do not promise the same integration on every Codex surface.

Sources: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [AGENTS discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md), and [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), checked 2026-09-09.

### Claude Code (plan mode)

- Produces a self-contained prompt pasted as the first message of a fresh plan-mode conversation — no prior context available
- All behavioral rules live in templates.md Template M

### Claude Code (dynamic workflow)

- For fan-out / parallel work at scale: a natural-language prompt that launches a NATIVE dynamic workflow — real subagents in parallel, orchestration designed by Claude Code. Distinct from the [Workflow AI](#workflow-ai) section (Zapier / Make / n8n)
- Output is a PROMPT only, never a .js script; all behavioral rules live in templates.md Template N

### Cursor / Windsurf

- File path + function name + current behavior + desired change + do-not-touch list + language and version
- "Done when:" is required — defines when the agent stops editing

### Cline (formerly Claude Dev)

- Agentic VS Code extension — edits files, runs terminal commands, uses browser tools; powered by Claude, GPT, or others, so match the prompt style to the underlying model
- Starting state + target state + file scope + stop conditions + approval gates; specify which files to edit and which to leave untouched
- Add "Ask before running terminal commands" or "Ask before installing dependencies" to prevent unwanted actions
- Shows a task list before executing

### GitHub Copilot

- Write the exact function signature, docstring, or comment immediately before invoking
- Describe input types, return type, edge cases, and what the function must NOT do
- Copilot completes what it predicts, not what you intend — leave no ambiguity in the comment

### Antigravity (Google, powered by Gemini 3 Pro)

- Task-based prompting — describe outcomes, not steps; scope to one deliverable per session
- Prompt for an Artifact (task list, implementation plan) before execution so you can review it first
- Browser automation is built-in — include verification steps: "After building, verify UI at 375px and 1440px using the browser agent"
- Specify autonomy level: "Ask before running destructive terminal commands"

## Agentic AI

### Devin / SWE-agent

- Fully autonomous — can browse web, run terminal, write and test code; very explicit starting state + target state required
- Forbidden actions list is critical — these agents make decisions you did not intend without explicit constraints
- Scope the filesystem: "Only work within /src. Do not touch infrastructure, config, or CI files."

### Bolt / v0 / Lovable / Figma Make / Google Stitch

- Full-stack generators default to bloated boilerplate — always specify stack, version, what NOT to scaffold, clear component boundaries
- Add "Do not add authentication, dark mode, or features not explicitly listed" to prevent feature bloat
- Lovable responds well to design-forward descriptions — include visual/UX intent
- v0 is Vercel-native — specify if you need non-Next.js output; Bolt handles full-stack — be explicit about frontend vs backend vs database parts
- Figma Make references your Figma component names directly; Google Stitch is prompt-to-UI — describe the interface goal, add "match Material Design 3 guidelines" for Google-native styling

## Computer-Use Agents

Perplexity Comet, OpenAI Atlas, Claude in Chrome — these agents control a real browser (click, scroll, fill forms, complete transactions autonomously).

- Describe the outcome with explicit constraints, not navigation steps: "Find the cheapest flight from X to Y on Emirates or KLM, no Boeing 737 Max, one stop maximum" — the agent makes its own decisions without them
- Add permission boundaries: "Do not make any purchase. Research only."
- Add a stop condition for irreversible actions: "Ask me before submitting any form, completing any transaction, or sending any message"
- Comet is best for web research, comparison, and data extraction; Atlas is stronger for multi-step commerce and account management

## Research / Orchestration

### Perplexity / SearchGPT

- Specify mode: search vs analyze vs compare; add citation requirements
- Reframe hallucination-prone questions as grounded queries

### Manus / Perplexity Computer

- Multi-agent orchestrators — describe the end deliverable, not the steps; they decompose internally. Specify the output artifact type (report / spreadsheet / code / summary)
- Add "Flag any data point you are not confident about."
- For long multi-step tasks: add verification checkpoints — each chained step compounds hallucination risk

## Image AI — Generation

First detect: generation from scratch or editing an existing image? If editing → see [Image AI — Editing](#image-ai--editing).

### Midjourney

- Comma-separated descriptors, not prose. Subject first, then style, mood, lighting, composition
- Parameters at end: `--ar 16:9 --v 6 --style raw`; negative prompts via `--no [unwanted elements]`

### OpenAI image tools

- Prose description works well; add "do not include text in the image unless specified."
- Describe foreground, midground, background separately for complex compositions
- Confirm the target interface and available image model. DALL-E 3 has been removed from the OpenAI API and has no editing endpoint; if explicitly requested, explain the limitation and let the user choose a supported target rather than silently changing models. Use the current interface's image-generation or editing capability. [Official DALL-E 3 status](https://developers.openai.com/api/docs/models/dall-e-3), [image API guidance](https://developers.openai.com/api/docs/guides/image-generation), checked 2026-09-09.

### Stable Diffusion

- `(word:weight)` syntax. CFG 7-12. Negative prompt is MANDATORY
- Steps 20-30 for drafts, 40-50 for finals

### SeeDream

- Strong at artistic and stylized generation — specify art style explicitly (anime, cinematic, painterly) before scene content
- Mood and atmosphere descriptors work well. Negative prompt recommended
- Images only — not to be confused with **Seedance 2**, ByteDance's *video* model (see [Video AI](#video-ai))

## Image AI — Editing

When the user mentions "change", "edit", "modify", "adjust" anything in an existing image, or uploads a reference.

- Always instruct the user to attach the reference image to the tool first
- Build the prompt around the delta ONLY — what changes, what stays the same
- Midjourney: `--cref [image URL]` for character reference or `--sref` for style reference
- OpenAI image tools: attach the reference to the chosen interface; use its image-editing capability. For the API, select a currently supported GPT Image model and the documented edits or Responses image tool path; a ChatGPT attachment is not an API endpoint
- Stable Diffusion: use img2img mode, not txt2img. Denoising strength 0.3-0.6 to preserve the original

## Image AI — ComfyUI

Node-based workflow — not a single prompt box.

- Ask which checkpoint model is loaded before writing (SD 1.5, SDXL, Flux)
- Always output two separate blocks: Positive Prompt and Negative Prompt. Never merge them
- SD 1.5: shorter prompts, under 75 tokens per block, use (word:weight) syntax. SDXL: handles longer prompts, more natural language. Flux: natural language, less weighted syntax, very responsive to style descriptions

## 3D AI

### Text to 3D (Meshy, Tripo, Rodin)

- Describe: style keyword (low-poly / realistic / stylized cartoon) + subject + key features + primary material + texture detail + technical spec
- Negative prompt supported: "no background, no base, no floating parts"
- Meshy: best for game assets. Tripo: fastest for clean topology. Rodin: highest quality for photorealistic
- Specify intended export: game engine (GLB/FBX), 3D printing (STL), web (GLB); for characters, specify A-pose or T-pose if the model will be rigged

### In-Engine AI (Unity AI, BlenderGPT)

- Unity AI (Unity 6.2+): use /ask for docs, /run for automating Editor tasks, /code for C# code. Be precise about Editor operations
- Unity AI Generators: text-to-sprite, text-to-texture, text-to-animation. Describe asset type, art style, technical constraints (resolution, color palette, animation loop or one-shot)
- BlenderGPT / Blender AI add-ons: these generate Python scripts for Blender. Be specific about geometry, material names, and scene context. Include "apply to selected object" or "apply to entire scene"

## Video AI

- **Sora**: describe as if directing a film shot. Camera movement is critical — static vs dolly vs crane changes output dramatically
- **Runway Gen-3**: responds to cinematic language — reference film styles for consistent aesthetic
- **Kling**: strong at realistic human motion — describe body movement explicitly, specify camera angle and shot type
- **LTX Video**: fast generation, prompt-sensitive — keep descriptions concise and visual. Specify resolution and motion intensity
- **Dream Machine (Luma)**: cinematic quality — reference lighting setups, lens types, and color grading styles
- **Seedance 2 (ByteDance video, ≠ SeeDream)**: prose director-style (Subject → Action → Environment → Camera → Lighting → Style → Audio, ~60-100 words). ONE primary camera move per shot; pacing words, not specs ("slow dolly" not "24fps"). NO negative prompts — phrase exclusions positively ("clean motion, correct hands"). Native synced audio (dialogue in quotes) and `@Image1`/`@Video1` reference tags distinguish it from Sora/Kling. Multi-shot in one prompt: chain with "camera cuts to…" (or "Shot 1: / Shot 2:") and re-name the subject each shot so identity holds. Image-to-video: describe only the motion/change plus "preserve composition and colors"

## Voice AI

### ElevenLabs

- Specify emotion, pacing, emphasis markers, and speech rate directly — prose descriptions do not translate
- Use SSML-like markers for emphasis: indicate which words to stress, where to pause

## Workflow AI

### Zapier / Make / n8n

- Trigger app + trigger event → action app + action + field mapping. Step by step.
- Auth requirements noted explicitly — "assumes [app] is already connected"
- For multi-step workflows: number each step and specify what data passes between steps
