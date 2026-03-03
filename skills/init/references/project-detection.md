# Project Structure Detection Logic

Detailed detection algorithm for identifying monorepo and multi-repo workspace structures. Referenced from Step 1 of the init skill.

## Step 0 — Check for multi-repo workspace (runs before Steps A/B/C)

If the current directory has no `.git/` directory:
- Scan immediate subdirectories for `.git/` directories (skip dot-directories and non-project dirs from the Step B skip list)
- If 2+ subdirectories have `.git/`: confirmed **multi-repo workspace** — each is an independent repo
- If 1 subdirectory has `.git/`: not a workspace — suggest user cd into that repo and run init there
- If 0 `.git/` found: not a recognized project structure — inform user

When multi-repo workspace is detected:
- Enumerate each repo with its path and name
- For each repo, run Steps A/B/C internally to detect if the repo is itself a monorepo or single project

If `.git/` exists in the current directory, skip this step and proceed to Step A (standard monorepo detection within a single repo).

**Manifest validity (applies to all steps):** A lock file without its corresponding manifest (e.g., `package-lock.json` without `package.json`) does not count as a valid manifest.

## Step A — Check for Workspace Config Files (confirms monorepo alone)

- npm/yarn/pnpm workspaces: `workspaces` in root `package.json`, or `pnpm-workspace.yaml`
- Lerna (`lerna.json`), Nx (`nx.json`), Turborepo (`turbo.json`), Rush (`rush.json`)
- Cargo workspace: `[workspace]` in root `Cargo.toml`; Go workspace: `go.work`
- Gradle: `settings.gradle(.kts)` with `include`; Maven: `pom.xml` with `<modules>`
- Bazel: `WORKSPACE` or `WORKSPACE.bazel`

## Step B — Scan for Independent Manifests (confirms monorepo if 2+ projects found)

Scan top-level directories for manifest files (from the manifest table in SKILL.md). Skip:
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

**.NET solution consolidation** (post-scan refinement — runs before decision matrix):
If a single `.sln` file exists at the root, parse its `Project(...)` entries to get referenced `.csproj` paths. If every `.csproj` found by Step B is referenced by that `.sln`, collapse all those directories into one project for the decision matrix count. Non-`.csproj` manifests (e.g., `package.json` in a frontend directory) still count separately — so a repo with one `.sln` plus a `frontend/package.json` yields 2 projects and still qualifies as a monorepo. Skip consolidation when: no `.sln` exists, multiple `.sln` files exist at root, or any `.csproj` is not referenced by the `.sln`.

## Step C — Check Supporting Signals (cannot confirm alone)

- `README.md` describes multi-component architecture (mentions separate apps, services, or components: "frontend and backend", "client and server", "API server", "microservices", etc.)
- `docker-compose.yml` / `compose.yml` defines multiple services with `build:` contexts pointing to different subdirectories
- Root manifest scripts use `concurrently`, `npm-run-all`, or `run-p`/`run-s` to launch multiple processes
- Proxy configuration exists (`proxy.conf.json`, `proxy.conf.js`, `setupProxy.js`) indicating a frontend proxying to a local backend

## Decision Matrix

- Multi-repo workspace (Step 0) → confirmed multi-repo, enumerate repos
- Workspace config found (Step A) → confirmed monorepo, enumerate from config
- 2+ projects with manifests (Step B) → confirmed monorepo, enumerate from projects
- Supporting signals (Step C) + 1 dir with manifest → likely monorepo, ask user to confirm
- Supporting signals only → insufficient evidence, ask user to identify subproject dirs
- No signals → single project

## Subproject Enumeration

**If monorepo detected:** Inform user of detection signals and identified subprojects with tech stacks. Confirm before proceeding.

- Step A detected: use workspace member list + any additional top-level dirs with manifests not in the config.
- Step B only: use all qualifying directories (including nested ones found via depth-2 check). If the root-as-project check qualified the root, include it too.
- Root-as-project or root-as-workspace-member (e.g., `"."` in workspaces): include in subproject table but do NOT create a separate CLAUDE.md — root CLAUDE.md covers it. Its docs go in `.claude/docs/`.
- For each subproject, detect its tech stack using the manifest table.
