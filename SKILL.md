---
name: bootstrap
description: Bootstrap effective documentation following LLM-optimized practices
disable-model-invocation: true
---

# Bootstrap Project Documentation

Create optimized CLAUDE.md and supporting docs using research-backed practices. Unlike `/init`, this generates structured documentation following the WHAT/WHY/HOW framework with progressive disclosure. Supports both single projects and monorepos.

## Before You Start

Read `.claude/skills/claude-code-bootstrap/references/claude-md-best-practices.md`. Key constraints:
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

**Extract**: Project name, tech stack, build system, available scripts.

**Analyze structure** (stay shallow):
- README.md for project purpose and features
- Top-level directories for architecture pattern
- Entry points (main.ts, index.ts, app.module.ts, etc.)

**Check for monorepo indicators:**

**Step A — Check for workspace config files** (confirms monorepo alone):

| Tool | Detection |
|------|-----------|
| npm/yarn/pnpm workspaces | `workspaces` field in root `package.json`, or `pnpm-workspace.yaml` |
| Lerna | `lerna.json` |
| Nx | `nx.json` |
| Turborepo | `turbo.json` |
| Rush | `rush.json` |
| Cargo workspace | `[workspace]` section in root `Cargo.toml` |
| Go workspace | `go.work` file |
| Gradle multi-project | `settings.gradle(.kts)` with `include` statements |
| Maven multi-module | `pom.xml` with `<modules>` section |
| Bazel | `WORKSPACE` or `WORKSPACE.bazel` file |

**Step B — Scan for independent manifests** (confirms monorepo if 2+ dirs found):

Scan top-level directories for manifest files (from the manifest table above). Skip:
- **Dot-directories**: `.git`, `.github`, `.vscode`, etc.
- **Dependencies**: `node_modules`, `vendor`, `.venv`, `venv`, `env`
- **Build output**: `dist`, `build`, `out`, `target`, `bin`, `obj`
- **Framework/cache**: `.next`, `.nuxt`, `__pycache__`, `.cache`, `.tox`
- **Non-project**: `examples`, `demos`, `test-fixtures`, `e2e`, `__tests__`, `.storybook`

**Step C — Check supporting signals** (cannot confirm alone):

- `README.md` describes multi-component architecture ("frontend and backend", "client and server", "microservices", etc.)
- `docker-compose.yml` / `compose.yml` defines multiple services with `build:` contexts pointing to different subdirectories

**Decision:**
- Workspace config found (Step A) → confirmed monorepo, enumerate from config
- 2+ dirs with manifests (Step B) → confirmed monorepo, enumerate from dirs
- Supporting signals (Step C) + 1 dir with manifest → likely monorepo, ask user to confirm
- Supporting signals only → insufficient evidence, ask user to identify subproject dirs
- No signals → single project

**If monorepo detected:** Inform user of detection signals and identified subprojects with tech stacks. Confirm before proceeding.

**Enumerate subprojects:**
- Step A detected: use workspace member list + any additional top-level dirs with manifests not in the config.
- Step B only: use all qualifying top-level dirs.
- Root-as-workspace-member (e.g., `"."` in workspaces): include in subproject table but do NOT create a separate CLAUDE.md — root CLAUDE.md covers it.
- For each subproject, detect its tech stack using the manifest table.

### Step 1 Checkpoint

Before proceeding, confirm you have all of the following. If any are missing, re-examine the project:

- **Project name** (from manifest or README)
- **Tech stack(s)** (languages, frameworks, from manifest dependencies)
- **Build/test/lint commands** (from manifest scripts or standard tooling)
- **Monorepo status**: single project, confirmed monorepo, or ambiguous (awaiting user input)
- If monorepo: **subproject list** with each subproject's path, purpose, and tech stack
- If monorepo: **workspace tool** (if any)
- **Existing files inventory** (requires separate filesystem checks): which of `.claude/CLAUDE.md`, `.claude/settings.json`, `.claude/docs/*`, root `CLAUDE.md`, subproject `CLAUDE.md` files already exist

Print this as a **Detection Summary** to the user before proceeding. This gives the user a chance to correct any misdetection before files are generated. If the user provides corrections, update the detection results accordingly before proceeding.

## Step 2: Handle Existing Files

**Before creating any file**, check if it (or a related version) already exists. Use the existing files inventory from the Step 1 Checkpoint.

**Rule 1 — Read before overwriting:** If a file you are about to create already exists (including root `CLAUDE.md` which maps to `.claude/CLAUDE.md`), read it first. Preserve all project-specific content (custom commands, architectural notes, team conventions) unless it conflicts with the new structure. Inform the user what was preserved and what changed.

**Rule 2 — Relocate when scope changes:** If existing docs need to move (e.g., root `.claude/docs/testing.md` should become subproject-scoped in a monorepo), move the relevant content to the new location and remove the old file. Keep only `coding-guidelines.md` at root level.

If root `CLAUDE.md` exists (not in `.claude/`), suggest removing it after `.claude/CLAUDE.md` is created.

## Step 3: Create Directory Structure

```bash
mkdir -p .claude/docs
# Monorepo: also mkdir -p <subproject>/docs for each subproject from Step 1
```

## Step 4: Create CLAUDE.md

### Single project

Create `.claude/CLAUDE.md` with living document header:

```markdown
<!-- Keep this file and .claude/docs/ updated when project structure, conventions, or tooling changes -->

# Project Name
```

**Structure content using WHAT/WHY/HOW:**

| Section | Content |
|---------|---------|
| **WHAT** | Project name, purpose (1 line), tech stack summary |
| **WHY** | Essential commands: build, test, lint (from project manifest) |
| **HOW** | Documentation references with task-oriented descriptions |

**Documentation section format:**
```markdown
## Documentation
Read the relevant doc before making changes:
- `coding-guidelines.md` - For new features, refactoring, code structure
- `testing.md` - For writing or modifying tests
- `styling.md` - For UI components, CSS, visual changes
- `architecture.md` - For understanding project structure, data flow
```

Only list docs that were actually created. Keep total file under 60 lines.

### No manifest detected

Create generic docs with placeholders and inform user that manual customization is recommended.

### Monorepo

Use template from `.claude/skills/claude-code-bootstrap/templates/monorepo-claude.md` instead. Fill in:
- Subproject table with all detected subprojects (path, purpose, tech stack)
- Root-level / workspace-wide commands only (not subproject-specific commands)
- References to each subproject's CLAUDE.md
- If a workspace tool was detected (Step A), include "managed by [tool]" in the description line
- If no workspace tool was detected (Step B only), use "Monorepo with [N] packages" or "Multi-project repository with [N] components" without referencing a workspace tool

If more than 6 subprojects, group by category (apps, libs, services) in the root CLAUDE.md and move the full subproject table to `.claude/docs/architecture.md`. Keep descriptions concise (abbreviate stacks, e.g., "TS/React" not "TypeScript, React, Vite, Tailwind") to stay under 60 lines.

## Step 4b: Create Subproject CLAUDE.md Files (monorepo only)

For each detected subproject (except root-as-member — the root CLAUDE.md already covers it), create `<subproject>/CLAUDE.md` using template from `.claude/skills/claude-code-bootstrap/templates/subproject-claude.md`:
- Scope WHAT/WHY/HOW to that subproject's tech stack and purpose
- Include only commands specific to this subproject (run from its directory)
- Reference its local `docs/` folder for detailed documentation
- Mention parent monorepo name in the opening line
- Keep under 60 lines

## Step 5: Create settings.json

Use template from `.claude/skills/claude-code-bootstrap/templates/settings.json`. Customize allow list based on detected project type:

| Type | Commands to Allow |
|------|-------------------|
| Node.js | `npm run`, `npx`, `yarn`, `pnpm` |
| Rust | `cargo build`, `cargo test`, `cargo run`, `cargo clippy` |
| Python | `pytest`, `pip`, `poetry`, `uv`, `ruff`, `mypy` |
| C#/.NET | `dotnet build`, `dotnet test`, `dotnet run`, `dotnet restore` |
| Java/Maven | `mvn compile`, `mvn test`, `mvn package` |
| Java/Gradle | `gradle build`, `gradle test`, `gradlew` |
| Go | `go build`, `go test`, `go run`, `go vet`, `golangci-lint` |
| C/C++ | `cmake`, `make`, `ctest`, `ninja` |
| Ruby | `bundle`, `rake`, `rspec` |

**If monorepo:** Union the permission sets for all tech stacks detected across subprojects into a single root `.claude/settings.json`.

## Step 6: Create Documentation Files

**Always create in `.claude/docs/`:**
- `coding-guidelines.md` - Use template from `.claude/skills/claude-code-bootstrap/templates/docs/coding-guidelines.md` (replace [PROJECT NAME]). Shared across the entire repo.

**Create based on these detection rules:**

| File | Create when ANY of these are true |
|------|-----------------------------------|
| `testing.md` | Manifest lists a test dependency (jest, vitest, mocha, karma, pytest, unittest, rspec, etc.) OR a `test`/`test:*` script exists in manifest OR a `tests/`, `test/`, `spec/`, `__tests__/` directory exists |
| `styling.md` | Manifest lists a UI framework (react, vue, angular, svelte, solid) OR lists CSS tooling (tailwindcss, styled-components, sass, less, postcss) OR `.css`/`.scss`/`.less` files exist in `src/` |
| `architecture.md` | Project has 3+ top-level source directories (excluding config, tests, docs, build output) OR uses recognized pattern directories (controllers/, services/, repositories/, handlers/, models/) |

**Placement rules:**
- **Single project:** All files go in `.claude/docs/`.
- **Monorepo:** `testing.md`, `styling.md`, and `architecture.md` go in each subproject's `docs/` folder, scoped to that subproject's stack. Apply the detection rules above **per subproject** (e.g., skip `styling.md` for a subproject with no UI deps). Each subproject can also get its own `coding-guidelines.md` only if its conventions differ significantly from root.

## Step 7: Verify and Report

Run through this checklist. **Fix any failures before reporting to the user.**

**File existence** — verify every expected file was created. List all files in `.claude/` matching `*.md` or `*.json`, and for monorepos also check each subproject path from Step 1 for `CLAUDE.md` and `docs/*.md`.

**Content checks** — for each file, verify it has real content (not just placeholders):
- `.claude/CLAUDE.md`: Contains actual project name, at least one real command, and a Documentation section. Line count <= 60.
- `.claude/settings.json`: `allow` list includes commands matching the detected tech stack from Step 1.
- `.claude/docs/coding-guidelines.md`: `[PROJECT NAME]` placeholder replaced with actual project name.
- Each `testing.md`: References the project's actual test framework and commands.
- Each `styling.md`: References the project's actual CSS/UI tooling.
- Each `architecture.md`: References actual directory names from the project.
- Monorepo: each subproject's `CLAUDE.md` exists, mentions the subproject name, and is <= 60 lines.

**Cross-reference checks:**
- Every doc listed in a CLAUDE.md Documentation section actually exists as a file.
- Monorepo: every subproject in root CLAUDE.md's Architecture table has a corresponding `CLAUDE.md` file.

**If any check fails:** Fix the issue, then re-verify. Do not proceed to the summary until all checks pass.

**Summary:** Report to the user: files created, detected tech stack, and decisions made (monorepo detection rationale, which optional docs were created and why, which were skipped and why).
