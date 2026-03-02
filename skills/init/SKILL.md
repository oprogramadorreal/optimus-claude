---
description: Prime project setup for Claude Code — generates CLAUDE.md with progressive disclosure docs, auto-format hooks, and code-quality agents. Replaces /init. Supports monorepos.
disable-model-invocation: true
---

# Prime Project for Claude Code

Analyze the project and set up Claude Code for optimal performance: generate CLAUDE.md with supporting docs (WHAT/WHY/HOW, progressive disclosure), install auto-format hooks per detected stack, deploy code-simplifier and test-guardian agents, and sync existing documentation against source code. Supports single projects and monorepos.

## Before You Start

Read `$CLAUDE_PLUGIN_ROOT/skills/init/references/claude-md-best-practices.md`. Key constraints:
- Every CLAUDE.md <= 60 lines
- Use file:line references, not code snippets
- Only universally-applicable instructions

## Step 1: Detect Project Context

**Identify project type** from manifest files:

| Manifest | Type | Package Manager |
|----------|------|-----------------|
| package.json | Node.js | npm, yarn, pnpm, bun |
| Cargo.toml | Rust | cargo |
| pyproject.toml, setup.py, requirements.txt | Python | pip, poetry, uv |
| *.csproj, *.sln | C#/.NET | dotnet |
| pom.xml | Java | maven |
| build.gradle | Java | gradle |
| go.mod | Go | go |
| CMakeLists.txt, Makefile | C/C++ | cmake, make |
| Gemfile | Ruby | bundler |

Note: `.sln` files reference `.csproj` projects — they confirm .NET presence but aren't independent project manifests. Don't count a root `.sln` for root-as-project detection.

**Extract**: Project name, tech stack, build system, available scripts.

**Detect active package manager** (this determines command prefixes for CLAUDE.md):

| Type | Check (in priority order) | Result |
|------|---------------------------|--------|
| Node.js | `pnpm-lock.yaml` exists | pnpm |
| Node.js | `yarn.lock` exists | yarn |
| Node.js | `bun.lockb` exists | bun |
| Node.js | default / `package-lock.json` | npm |
| Python | `uv.lock` exists OR `[tool.uv]` in pyproject.toml | uv (prefix commands with `uv run`) |
| Python | `poetry.lock` exists OR `[tool.poetry]` in pyproject.toml | poetry (prefix with `poetry run`) |
| Python | default | pip (bare commands: `pytest`, `ruff`, etc.) |

Use the detected package manager for all commands in CLAUDE.md. For example, if the Node.js project uses pnpm, write `pnpm run build` not `npm run build`. If the Python project uses uv, write `uv run pytest` not just `pytest`.

**Analyze structure and extract doc insights:**
- Top-level directories for architecture pattern
- Entry points (main.ts, index.ts, app.module.ts, etc.)
- README.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/ directory files
- Monorepo: also each subproject's README.md

**Source code is the source of truth.** Manifests and actual project files always override what documentation claims. When reading existing docs:
1. **Extract non-code insights** — information not derivable from source code alone:
   - Architecture rationale and design decisions ("why" content for CLAUDE.md)
   - Contributor workflow conventions (branching strategy, PR process, commit format)
   - Coding conventions not enforced by linters (naming schemes, architectural boundaries)
2. **Discard** any insight that directly contradicts source code (e.g., doc says "we use Redux" but only Zustand is in dependencies). Keep insights that are neither confirmed nor contradicted — non-code conventions and rationale are inherently unverifiable from source alone.

Factual contradictions in existing docs (wrong commands, outdated tech references, etc.) are detected and addressed in Step 6b.

These insights flow into generated files in Steps 4–6b. The Detection Summary confirms doc reading occurred, but do not narrate insights during analysis.

**Check for monorepo indicators:**

**Step A — Check for workspace config files** (confirms monorepo alone):
- npm/yarn/pnpm workspaces: `workspaces` in root `package.json`, or `pnpm-workspace.yaml`
- Lerna (`lerna.json`), Nx (`nx.json`), Turborepo (`turbo.json`), Rush (`rush.json`)
- Cargo workspace: `[workspace]` in root `Cargo.toml`; Go workspace: `go.work`
- Gradle: `settings.gradle(.kts)` with `include`; Maven: `pom.xml` with `<modules>`
- Bazel: `WORKSPACE` or `WORKSPACE.bazel`

**Step B — Scan for independent manifests** (confirms monorepo if 2+ projects found):

Scan top-level directories for manifest files (from the manifest table above). Skip:
- **Dot-directories**: `.git`, `.github`, `.vscode`, etc.
- **Dependencies**: `node_modules`, `vendor`, `.venv`, `venv`, `env`
- **Build output**: `dist`, `build`, `out`, `target`, `bin`, `obj`
- **Framework/cache**: `.next`, `.nuxt`, `__pycache__`, `.cache`, `.tox`
- **Non-project**: `examples`, `demos`, `test-fixtures`, `e2e`, `__tests__`, `.storybook`, `samples`, `experiments`, `scripts`, `tools`, `docs`

**Depth-2 check for container directories:** For any scanned top-level directory that has no manifest and is not in the skip list, check its immediate subdirectories for manifest files (applying the same skip rules). This catches nested subprojects inside container directories (e.g., `app/API/` and `app/client/` inside `app/`). Count each qualifying subdirectory as a separate project using its full relative path (e.g., `app/API`, `app/client`).

**Root-as-project check** (only when the total number of qualifying projects found in Step B — including depth-2 results — equals exactly 1):
The root itself may be an independent project. Count it as an additional project if the root has a manifest file AND at least one of:
- A **framework-specific config** at root (`angular.json`, `next.config.*`, `nuxt.config.*`, `vue.config.*`, `svelte.config.*`, `astro.config.*`, `webpack.config.*`, `vite.config.*`, `tsconfig.app.json`)
- A **root source directory** (`src/`, `app/`, or `lib/`) containing source files, where the subdirectory project also has its own source files — indicating two separate codebases
- A **different test framework** at root vs the subdirectory (e.g., root has `karma.conf.js` while subdirectory has `jest.config.js`)

**Step C — Check supporting signals** (cannot confirm alone):

- `README.md` describes multi-component architecture (mentions separate apps, services, or components: "frontend and backend", "client and server", "API server", "microservices", etc.)
- `docker-compose.yml` / `compose.yml` defines multiple services with `build:` contexts pointing to different subdirectories
- Root manifest scripts use `concurrently`, `npm-run-all`, or `run-p`/`run-s` to launch multiple processes
- Proxy configuration exists (`proxy.conf.json`, `proxy.conf.js`, `setupProxy.js`) indicating a frontend proxying to a local backend

**Decision:**
- Workspace config found (Step A) → confirmed monorepo, enumerate from config
- 2+ projects with manifests (Step B) → confirmed monorepo, enumerate from projects
- Supporting signals (Step C) + 1 dir with manifest → likely monorepo, ask user to confirm
- Supporting signals only → insufficient evidence, ask user to identify subproject dirs
- No signals → single project

**If monorepo detected:** Inform user of detection signals and identified subprojects with tech stacks. Confirm before proceeding.

**Enumerate subprojects:**
- Step A detected: use workspace member list + any additional top-level dirs with manifests not in the config.
- Step B only: use all qualifying directories (including nested ones found via depth-2 check). If the root-as-project check qualified the root, include it too.
- Root-as-project or root-as-workspace-member (e.g., `"."` in workspaces): include in subproject table but do NOT create a separate CLAUDE.md — root CLAUDE.md covers it. Its docs go in `.claude/docs/`.
- For each subproject, detect its tech stack using the manifest table.

### Step 1 Checkpoint

Before proceeding, confirm you have all of the following. If any are missing, re-examine the project:

- **Project name** (from manifest or README)
- **Tech stack(s)** (languages, frameworks, from manifest dependencies)
- **Package manager** (detected from lock files / config — e.g., npm, pnpm, yarn, uv, poetry, pip)
- **Build/test/lint commands** (from manifest scripts, prefixed with the detected package manager)
- **Monorepo status**: single project, confirmed monorepo, or ambiguous (awaiting user input)
- If monorepo: **subproject list** with each subproject's path, purpose, and tech stack
- If monorepo: **workspace tool** (if any)
- **Existing files inventory** (existence check only — content of docs is read in Step 1b; agents are never audited, always overwritten): which of `.claude/CLAUDE.md`, `.claude/settings.json`, `.claude/docs/*`, `.claude/agents/code-simplifier.md`, `.claude/agents/test-guardian.md`, root `CLAUDE.md`, subproject `CLAUDE.md` files already exist
- **Test infrastructure detected** (yes/no): test framework in dependencies, test command in scripts, or test directory present
- **Doc-sourced insights** (if any documentation found): verified conventions, architecture rationale, workflow rules — all cross-checked against source code

Print this as a **Detection Summary** to the user before proceeding. This gives the user a chance to correct any misdetection before files are generated. If the user provides corrections, update the detection results accordingly before proceeding.

### Step 1b: Documentation Audit (only when existing docs found)

**Skip this step entirely if no existing documentation files were found in the inventory.** Proceed directly to Step 2.

If existing docs were found, analyze them to identify what needs updating:

1. **Read all existing doc files** from the inventory (CLAUDE.md, settings.json, all `.claude/docs/*.md`, and for monorepos each subproject's CLAUDE.md and `docs/*.md`).

2. **Compare documented state vs detected state:**

| Dimension | Check |
|-----------|-------|
| **Commands** | Do build/test/lint commands in CLAUDE.md match current manifest scripts? |
| **Tech stack** | Does the documented stack match current dependencies in manifest files? |
| **Structure** | Do folder names, entry points, and architecture references in docs match the actual filesystem? |
| **Doc coverage** | Are there detected project aspects (test framework, UI deps, complex architecture) with no corresponding doc? Are there docs for aspects no longer present? |
| **Monorepo** | Do subproject tables match current workspace members? Any added/removed subprojects? |

3. **Present an Audit Report** to the user, organized as:
   - **Outdated** — items in docs that no longer match the project (with specific before/after)
   - **Missing** — project aspects that should have docs but don't
   - **Accurate** — items that are still correct (brief summary, no action needed)

4. **Ask the user** how to proceed:
   - **Update all** — apply all recommended changes
   - **Selective** — present findings as a numbered list; user picks which numbers to apply. Unapproved findings are left as-is (existing content preserved).
   - **Fresh start** — ignore existing docs and regenerate from scratch (proceeds to Step 2 as if no docs existed)

Remember the user's choice and approved findings. Steps 2–6 will reference them to make targeted updates rather than full overwrites. (Step 6b runs independently — see Step 6b.)

## Step 2: Handle Existing Files

**Audit-aware rule (applies to Steps 2–6, not Step 6b):** If user chose "Fresh start", treat all files as Missing. Otherwise: if Step 1b marked a file as Accurate, skip it. If Outdated, apply only user-approved changes — preserve everything else. If Missing or no audit was run, create normally. For "Selective" updates, only act on approved findings.

**Before creating any file**, check if it already exists. If so, read it first. Inform the user what was preserved vs changed.

**Relocate when scope changes:** If docs need to move (e.g., root `.claude/docs/testing.md` → subproject-scoped in a monorepo), move content to the new location and remove the old file. Keep only `coding-guidelines.md` at root.

If root `CLAUDE.md` exists (not in `.claude/`), suggest removing it after `.claude/CLAUDE.md` is created.

## Step 3: Create Directory Structure

```bash
mkdir -p .claude/docs .claude/hooks .claude/agents
# Monorepo: also mkdir -p <subproject>/docs for each subproject from Step 1
```

## Step 4: Create CLAUDE.md

### Single project

Use template from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/single-project-claude.md`. Fill in all placeholders:
- Replace `[PROJECT NAME]` with the actual project name
- Replace `[One-line description]` with purpose from README or manifest
- Replace `[TECH STACK]` with detected languages and frameworks
- Fill the Conventions section with 2-5 bullets drawn from doc-sourced insights (Step 1): architectural patterns, naming conventions, key entry points, and non-obvious rules. If no insights were found, infer conventions from the project structure (e.g., "Express routes in `src/routes/`, middleware in `src/middleware/`", "CLI entry point at `src/index.ts` using Commander.js").
- Replace command placeholders with real commands using the detected package manager
- Replace directory placeholders with actual project directories
- In the Documentation section, list only docs that were actually created using `.claude/docs/` prefix
- In the Agents section, list only agents that were actually installed: code-simplifier is always listed; test-guardian only if test infrastructure was detected (Step 1)

The template follows WHAT/WHY/HOW structure. Keep total file under 60 lines. If no manifest was detected, use generic placeholders and inform user that manual customization is recommended.

### Monorepo

Use template from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/monorepo-claude.md` instead. Fill in:
- Subproject table with all detected subprojects (path, purpose, tech stack)
- Root-level / workspace-wide commands only (not subproject-specific commands)
- References to each subproject's CLAUDE.md
- If a workspace tool was detected (Step A), include "managed by [tool]" in the description line
- If no workspace tool was detected (Step B only), use "Monorepo with [N] packages" or "Multi-project repository with [N] components" without referencing a workspace tool

If root-as-project: also list root-scoped docs from `.claude/docs/` (testing.md, styling.md, architecture.md as applicable) in the Documentation section, alongside the shared `coding-guidelines.md`.

In the Agents section, list only agents that were actually installed: code-simplifier is always listed; test-guardian only if test infrastructure was detected (Step 1).

If more than 6 subprojects, group by category (apps, libs, services) in the root CLAUDE.md and move the full subproject table to `.claude/docs/architecture.md`. Keep descriptions concise (abbreviate stacks, e.g., "TS/React" not "TypeScript, React, Vite, Tailwind") to stay under 60 lines.

## Step 4b: Create Subproject CLAUDE.md Files (monorepo only)

For each detected subproject (except root-as-project/root-as-member — the root CLAUDE.md already covers it), create `<subproject>/CLAUDE.md` using template from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/subproject-claude.md`:
- Scope WHAT/WHY/HOW to that subproject's tech stack and purpose
- Include only commands specific to this subproject (run from its directory)
- Reference its local `docs/` folder for detailed documentation
- Mention parent monorepo name in the opening line
- Keep under 60 lines

## Step 5: Install Formatter Hooks

Add auto-format hooks so files stay consistently formatted after every Edit/MultiEdit/Write. Use templates from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/`.

**Audit-aware rule applies** (see Step 2). Additionally, skip a hook if `.claude/hooks/` already contains a file named `format-<stack>.*` (e.g., `format-python.py`, `format-python.sh`).

| Stack | Template | Formatter | Requires | Install when |
|-------|----------|-----------|----------|--------------|
| Python | `format-python.py` | black + isort | Python 3 | In project deps (requirements*.txt, pyproject.toml, Pipfile), or user approves |
| Node.js | `format-node.js` | prettier + organize-imports plugin | Node.js | In package.json devDependencies, or user approves |
| Rust | `format-rust.sh` | rustfmt | Bash | Always (rustfmt is built-in) |
| Go | `format-go.sh` | goimports → gofmt fallback | Bash | Always (hook detects goimports at runtime; offer `go install golang.org/x/tools/cmd/goimports@latest` if absent) |
| C#/.NET | `format-csharp.sh` | csharpier | Bash | In `.config/dotnet-tools.json`, or user approves (suggest `dotnet tool install csharpier`) |
| Java | `format-java.sh` | google-java-format | Bash | `google-java-format` is on PATH, or user approves (suggest installing from github.com/google/google-java-format) |
| C/C++ | `format-cpp.sh` | clang-format | Bash | `clang-format` is on PATH, or user approves (bundled with LLVM/Clang; available via system package manager) |

**Detect Python command** (only when the Python formatter hook will be installed): Run `python3 --version`. If it fails, run `python --version` and verify the output shows Python 3.x. Use whichever succeeds as `<python-cmd>` in hook commands below. If neither works, skip the Python hook and inform the user.

1. Copy applicable template(s) from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/hooks/` to `.claude/hooks/`.
2. External formatters not in deps → ask user "Add [formatter] as dev dependency and install format hook?" If declined, skip.
3. If any hooks were installed, create `.claude/settings.json` using the template from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/settings.json` as reference. Keep only entries for hooks actually installed. For Python, replace `<python-cmd>` with the detected command (`python3` or `python`). For Node.js use `node "..."`, for Bash-based hooks (Rust, Go, C#, Java, C/C++) use `bash "..."`. Monorepos: install all applicable hooks (each filters by file extension internally).

**If no hooks were installed**, do not create settings.json (unless it already exists with other content).

**Preserve existing content:** If an existing settings.json contains a `permissions` section or other custom configuration beyond `hooks`, preserve those sections. Merge hook changes into the existing file structure rather than overwriting.

**Node.js plugin setup** (when the Node.js hook is installed): Ensure `prettier-plugin-organize-imports` is a devDependency (install with detected package manager if missing; skip config below if user declines). Then add it to the Prettier config's `plugins` array. Check for config in this order: `.prettierrc`, `.prettierrc.json`, `.prettierrc.yaml`, `.prettierrc.yml`, `.prettierrc.toml`, `.prettierrc.mjs`, `.prettierrc.cjs`, `prettier.config.js`, `prettier.config.mjs`, `prettier.config.cjs`, `prettier.config.ts`, or `"prettier"` key in `package.json`. If `prettier-plugin-tailwindcss` is present, insert organize-imports **before** it. If no config exists, create `.prettierrc` with `{ "plugins": ["prettier-plugin-organize-imports"] }`.

## Step 5b: Install Code Simplifier Agent

Copy `$CLAUDE_PLUGIN_ROOT/skills/init/templates/agents/code-simplifier.md` to `.claude/agents/code-simplifier.md`.

Always overwrite — this is a verbatim template, not project-customized content.

## Step 5c: Install Test Guardian Agent (conditional)

**Only install when test infrastructure was detected in Step 1** — same condition as `testing.md` creation in Step 6: test framework in dependencies, `test`/`test:*` script in manifest, or `tests/`/`test/`/`spec/`/`__tests__/` directory exists.

If detected: Copy `$CLAUDE_PLUGIN_ROOT/skills/init/templates/agents/test-guardian.md` to `.claude/agents/test-guardian.md`. Always overwrite — this is a verbatim template, not project-customized content.

If not detected: Skip installation. In Step 7 summary, include: "⚠ No test infrastructure detected. Skipping test-guardian agent and testing docs. To set up a test framework and improve test coverage, run `/prime:unit-test`."

## Step 6: Create Documentation Files

**Always create in `.claude/docs/`:**
- `coding-guidelines.md` - Use template from `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/coding-guidelines.md` (replace [PROJECT NAME]). Shared across the entire repo.

**Create based on these detection rules:**

| File | Template | Create when ANY of these are true |
|------|----------|-----------------------------------|
| `testing.md` | `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/testing.md` | Manifest lists a test dependency (jest, vitest, mocha, karma, pytest, unittest, rspec, gtest, catch2, doctest, ctest, etc.) OR a `test`/`test:*` script exists in manifest OR a `tests/`, `test/`, `spec/`, `__tests__/` directory exists |
| `styling.md` | `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/styling.md` | Manifest lists a UI framework (react, vue, angular, svelte, solid) OR lists CSS tooling (tailwindcss, styled-components, sass, less, postcss) OR `.css`/`.scss`/`.less` files exist in `src/` |
| `architecture.md` | `$CLAUDE_PLUGIN_ROOT/skills/init/templates/docs/architecture.md` | Project has 3+ top-level source directories (excluding config, tests, docs, build output) OR uses recognized pattern directories (controllers/, services/, repositories/, handlers/, models/) |

Use each template as a skeleton — fill in all placeholders with actual project details (framework names, commands, directory paths, conventions). Don't leave any `[placeholder]` text in the final output.

**Placement rules:**
- **Single project:** All files go in `.claude/docs/`.
- **Monorepo:** `testing.md`, `styling.md`, and `architecture.md` go in each subproject's `docs/` folder, scoped to that subproject's stack. Apply the detection rules above **per subproject** (e.g., skip `styling.md` for a subproject with no UI deps). For root-as-project, its scoped docs go in `.claude/docs/` alongside the shared `coding-guidelines.md`. Each subproject can also get its own `coding-guidelines.md` only if its conventions differ significantly from root.

## Step 6b: Sync Existing Documentation

**Skip this step** if no project documentation exists (no README.md, CONTRIBUTING.md, ARCHITECTURE.md, or docs/ files). Proceed to Step 7.

This step runs independently of the Step 1b audit choice (including "Fresh start," which only governs `.claude/` files). It operates on project-owned files, not Claude-generated files.

Cross-check existing project documentation against the source code (manifests, lock files, directory structure). Fix **genuinely contradictory or outdated content** only — do not rewrite documents.

**Scope — only if they already exist:**
- README.md (root, and each subproject's for monorepos)
- CONTRIBUTING.md, ARCHITECTURE.md
- Files in docs/ that overlap with generated `.claude/docs/` topics

**Check for contradictions against source code (manifests, lock files, directory structure):**

| Type | Example |
|------|---------|
| Wrong command | README says `npm test`, but lock file and manifest show pnpm |
| Outdated tech ref | CONTRIBUTING references Webpack, but `vite.config.ts` exists and no Webpack in deps |
| Incorrect structure | README describes `src/controllers/`, but actual dir is `src/handlers/` |
| Stale subproject list | README lists 3 services, but workspace config has 4 |
| Removed dependency | Docs reference a library no longer in manifest dependencies |

The goal is surgical correction of factual errors, not editorial improvement. Only change content where source code directly contradicts a specific claim. Leave prose, tone, structure, and imprecise-but-not-wrong descriptions (e.g., "JavaScript" when project uses TypeScript with JS interop) untouched. Do not add sections, create files, or touch files outside the project root.

**If contradictions found:** Present a Sync Report (file, current content, proposed fix, source code evidence). Ask user: **Apply all**, **Selective** (numbered), or **Skip sync**. Apply only approved changes.

**If no contradictions found:** report this and proceed to Step 7.

## Step 7: Verify and Report

Run through this checklist. **Fix any failures before reporting to the user.**

**File existence** — verify every expected file was created. List all files in `.claude/` matching `*.md`, `*.json`, or `hooks/*`, and for monorepos also check each subproject path from Step 1 for `CLAUDE.md` and `docs/*.md`.

**Content checks** — verify each file has real content, not placeholders:
- `.claude/CLAUDE.md`: Actual project name, real commands, Conventions section (single project), Documentation section. Line count <= 60.
- `.claude/settings.json` (if created): `hooks.PostToolUse` references every installed hook file and vice versa. If file had custom sections (permissions, etc.), verify they're preserved.
- `.claude/docs/coding-guidelines.md`: `[PROJECT NAME]` replaced with actual name.
- Each `testing.md`, `styling.md`, `architecture.md`: References the project's actual frameworks, tooling, and directory names.
- Monorepo: each subproject's `CLAUDE.md` exists, mentions subproject name, and is <= 60 lines.
- `.claude/hooks/*`: Each hook file matches its template.
- `.claude/agents/code-simplifier.md`: File exists and matches template.
- `.claude/agents/test-guardian.md` (if test infrastructure was detected): File exists and matches template.
- **Sync changes (Step 6b)**: If sync changes were applied, verify each modified file still has valid markdown and no truncated content.

**Cross-reference checks:**
- Every doc listed in a CLAUDE.md Documentation section actually exists as a file.
- Every agent listed in a CLAUDE.md Agents section actually exists as a file in `.claude/agents/`.
- Monorepo: every subproject in root CLAUDE.md's Architecture table has a corresponding `CLAUDE.md` file.

**If any check fails:** Fix the issue, then re-verify. Do not proceed to the summary until all checks pass.

**Summary:** Report to the user: files created, detected tech stack, and decisions made (monorepo detection rationale, which optional docs were created and why, which were skipped and why).
