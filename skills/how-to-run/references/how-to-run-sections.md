# How-to-Run Section Templates

Rendering rules for Step 4 (content generation). Per-service Docker/local/shared-cloud logic lives in [`external-services-docker.md`](external-services-docker.md).

## Contents

- [Signal → Section Digest](#signal--section-digest)
- [Section Shapes](#section-shapes)
- [External Services](#external-services)
- [Workspace-Kind Command Branches](#workspace-kind-command-branches)
- [Schema Bootstrap](#schema-bootstrap)
- [Diagnostic Ladder](#diagnostic-ladder--container-running-but-host-cant-connect) (container running but host can't connect)
- [Multi-Repo Workspace Template](#multi-repo-workspace-template)

## Signal → Section Digest

| Detected signal | Render |
|--------|----------------------|
| Runtime version constraints / version-manager files | Prerequisites — "X ≥N required (source); M recommended (pin file)" when both exist |
| Hardware/OS tokens; private-registry files | Prerequisites (OS-version token as the first bullet when present) |
| Recommended Developer Tools rows | Prerequisites — *Recommended developer tools* sub-list (one bullet per detected token, detector order, optional one-line "why"; never invent tools) |
| Build system / SDK / engine files; `vcpkg.json` / `conanfile.*` | Toolchain & SDKs (+ Build, Running in Development for the produced artifact) |
| `.gitmodules`; sibling repos; CMake FetchContent/ExternalProject; `west.yml` / repo tool | Source Dependencies |
| Setup scripts (Dev Workflow Signals) | Installation — *One-shot setup* block BEFORE the per-PM install ("Alternate setup scripts: …" when >1; don't auto-pick) |
| `docker-compose.yml` services | External Services (Branch A) |
| Framework-config candidates (detector Task 5b) | External Services (Branch B, `(candidate)` marker) |
| `Dockerfile` without local-run scripts | Running in Development (Docker-based primary path) |
| `Makefile` / `Justfile` dev targets (`dev` / `start` / `setup` / `run` / `serve` / `up` / `docker-up`) | Running in Development (invoke the make/just target) |
| `flake.nix` / `shell.nix` / `default.nix` | Prerequisites + Installation (`nix develop` / `nix-shell` replaces manual toolchain setup) |
| Dotenv templates / framework config files | Environment Setup |
| Migration tools / codegen configs | Installation (post-install steps) |
| `.devcontainer/devcontainer.json` | Running in Development — `#### Quick start (Dev Container)` H4 immediately under the section heading, above the component layout (VS Code *Reopen in Container*, or `devcontainer up --workspace-folder .` via the dev container CLI); the container build replaces manual Installation |
| `.pre-commit-config.yaml` | Prerequisites (`pre-commit install` after cloning) + Common Issues |
| `.envrc` (direnv) | Prerequisites (`direnv allow` after cloning) + Common Issues |
| `mkcert` in scripts | Prerequisites (`mkcert -install` once per machine) + Common Issues |
| `template.yaml` (SAM) / `serverless.yml` / `.ts` | Running in Development (`sam local start-api` / `serverless offline`) |
| Test framework + test script | Running Tests |
| Components table rows | Running in Development — layout by row count (below) |
| Runtime Ports rows | `Expected result:` URLs — no grounded port means omit the port, never a framework default |

## Section Shapes

Write each section as a competent onboarding doc would — the rules below are the non-obvious constraints, not skeletons:

- **Prerequisites** — bullets: OS-version token first (when detected), hardware, runtimes with constraints, Docker (when compose detected), system tools, then the *Recommended developer tools* sub-list.
- **Toolchain & SDKs** — only for stacks with a non-trivial compile step or detected SDK. Group install commands per OS (Windows `powershell` / macOS + Linux `bash` fences) when multiple OSes are plausible.
- **Source Dependencies** — fix-after-clone only; the primary clone lives in Installation (multi-repo: in the workspace template's *Source Dependencies / Clone All*). Submodules: `git submodule update --init --recursive` fence. Sibling repos: table (Repo | Expected path | Clone URL) + clone fence. FetchContent/ExternalProject: one note — fetched automatically at configure time, network required.
- **Installation** — clone (`git clone --recursive` when `.gitmodules` exists) + `cd`, language-level install with the correct PM prefix, vcpkg/Conan bootstrap, codegen, then the Schema Bootstrap sub-block (below) when detected. One-shot setup block first when detected: script invocation verbatim, with the manual flow kept below it.
- **Environment Setup** — pick by the detector's Environment Setup table:
  - *(a) dotenv:* `cp .env.example .env` fence + brief per-variable descriptions (names only — never secret values).
  - *(b) config-file-driven:* open with "There is no `.env.example` template. Local configuration lives in `<file>` (format: `<format>`)…" — or "Additionally, local configuration lives in…" when (a) also rendered. One bullet per top-level section, detector order, description derived from section-name semantics only (a bare bullet beats a wrong guess); append "Keys you will edit: `<leaf1>`, `<leaf2>`" when the detector's `Key leaves` column has entries for the section (split the cell on `; ` then `<Section>: <leaves>` on `:`). Add "See `<file>` for the full list of <N> sections." only when `Variable count` > 25. When `Secrets committed` is `yes`, render immediately after the list: a **Caution** blockquote — the file appears to contain live credentials; verify git-tracking with `git ls-files --error-unmatch <file>` before treating it as a leak; if tracked, rotate and move to a locally-ignored overlay. Close with: **Never commit real secrets** — treat keys matching `(?i)(key|secret|password|token|credential|private)` as sensitive.
  - Both kinds → one `### Environment Setup` heading, (a)'s body then (b)'s body.
- **Build** — compiled stacks only. Multi-configuration build systems (CMake, MSBuild, .NET, Xcode): render both a Debug and a Release fence (`--config` / `--configuration` / `/p:Configuration=` / `-configuration`; single-config CMake generators like Ninja set the type at configure time — `cmake -B build-debug -DCMAKE_BUILD_TYPE=Debug && cmake --build build-debug`). Single-output systems (Cargo, Go): one fence.
- **Running in Development** — layout by Components-table row count (excluding the `No runnable components detected.` sentinel and `+N more` rows): **0** → omit the section (library). **1–2** → flat block per component: command fence, mandatory `Expected result:` line (URL/port/window/stdout the reader can check; literal `Expected result: <unknown — verify manually>` when nothing is assertable), optional single `Verify:` probe line only when a natural, grounded probe exists (grounded HTTP port → `curl -fsS http://localhost:<port>/`; omit for workers; never fabricate an endpoint path; drop `Verify:` when it would only restate the `Expected result:` URL). **3–5** → a `**Boot order:**` intro (services first, then migrations, then components in topological order; `Requires: <X>` starts after `<X>`) + one numbered bullet per component: `**<Component>** (<kind>) — <start command>. Expected result: <…>. Requires: <…>.` — no `Verify:` lines (probes go to Common Issues), no per-component H4s. **6+** → quick-reference table (Subproject | Path | Dev command | URL/port — port only when grounded). When every component shares a parent directory, render `From <shared-parent>/` once instead of per-component parentheticals. Wrapper commands that run non-obvious extra steps get one line below the fence: `> <wrapper> runs: <expanded form>` (skip direct aliases like `npm run dev` → `next dev`). Docker-only setups: `docker compose up` as the primary path.
- **Running Tests** — test command fence; coverage fence when available.
- **Common Issues** — only on clear signals: `.nvmrc` → `nvm use` before install; `.tool-versions`/`mise` → `mise install` / `asdf install`; Docker services → `docker compose up -d` must run first; private registry → authenticate before install; codegen → re-run on missing-file errors; submodules → `git submodule update --init --recursive` after pull; sibling repos → build fails when not cloned at the documented path; multi-config builds → `--config Debug` vs `Release`; Python → activate the venv. Plus *Verify `<service>` is reachable* bullets and the diagnostic ladder per [`external-services-docker.md`](external-services-docker.md) §Verify Commands and §Diagnostic Ladder trigger below.

## External Services

- **Branch A — compose covers all infrastructure:** table (Service | Port | Purpose from compose) + `docker compose up -d` fence + `docker compose ps` verify fence.
- **Branch B — no compose:** overview table (Service | Recommended runtime | Alternative | Role) + one per-service subsection per service using the matching template from `external-services-docker.md` (Docker-preferred / Shared-cloud primary / Shared-cloud no-Docker / Local install only).
- **Hybrid:** Branch A scoped to compose-covered services, then Branch B scoped to the rest — never duplicate a compose-covered service as a standalone subsection.
- The detector's External Services table is the source of truth for which services exist; classification is owned by `external-services-docker.md` §Decision Heuristics — do not re-derive it here. Credentials: defaults from compose or shared-cloud config, never actual password values.
- **All-candidate compression:** when ≥3 services are `Confidence: candidate` AND none is `confirmed`, drop the `(candidate)` markers (they convey no signal without confirmed rows to contrast) and render one overview sentence instead: "Services below were detected from `<config file>` rather than a compose file. Drop any incorrect rows via *Correct first* in Step 1."
- **Per-service "Update `<key>` in `<config file>`" consolidation:** when ≥3 shared-cloud services share the same source config file, drop the per-service update line and render one overview sentence: "The shared-cloud endpoints below come from `<config-file>`; swap them per environment by editing the matching config key listed in [Environment Setup](#environment-setup)." Keep per-service lines for ≤2 services or multiple config files.

## Workspace-Kind Command Branches

When the detector's `Workspace kind` is not `none`, use these forms — the wrong per-package form is a silent failure (`cargo build` at a workspace root builds only the root crate; `go mod download` does not resolve `go.work` modules). Render the Install row under Installation, Build-all under Build, per-module Run rows under Running in Development.

| Workspace kind | Install | Build (all) | Build (one) | Run (one) | Test (all) |
|----------------|---------|-------------|-------------|-----------|------------|
| `npm-workspaces` | `npm install` (at root) | `npm run build --workspaces --if-present` | `npm run build --workspace=<pkg>` | `npm run <script> --workspace=<pkg>` | `npm test --workspaces --if-present` |
| `pnpm-workspaces` | `pnpm install` (at root) | `pnpm -r build` | `pnpm --filter <pkg> build` | `pnpm --filter <pkg> <script>` | `pnpm -r test` |
| `yarn-workspaces` | `yarn install` (at root) | `yarn workspaces foreach -A run build` | `yarn workspace <pkg> build` | `yarn workspace <pkg> <script>` | `yarn workspaces foreach -A run test` |
| `lerna` | `npm install` (root) | `npx lerna run build` | `npx lerna run build --scope=<pkg>` | `npx lerna run <script> --scope=<pkg>` | `npx lerna run test` |
| `nx` | `npm install` (root) | `npx nx run-many -t build` | `npx nx build <pkg>` | `npx nx serve <pkg>` / `npx nx run <pkg>:<target>` | `npx nx run-many -t test` |
| `turbo` | `npm install` (root) | `npx turbo run build` | `npx turbo run build --filter=<pkg>` | `npx turbo run <script> --filter=<pkg>` | `npx turbo run test` |
| `cargo-workspace` | — (Cargo resolves automatically) | `cargo build --workspace` | `cargo build -p <crate>` | `cargo run -p <crate>` | `cargo test --workspace` |
| `go-workspace` | `go work sync` (at root) | `go build ./...` (at root — walks every module on Go ≥1.18) | `go build ./<module>/...` | `go run ./<module>` (or `./cmd/<name>`) | `go test ./...` |
| `gradle-multi-module` | — (Gradle resolves automatically) | `./gradlew build` | `./gradlew :<module>:build` | `./gradlew :<module>:run` | `./gradlew test` |
| `maven-multi-module` | — (Maven resolves automatically) | `mvn install` (root; `-DskipTests` for faster dev builds) | `mvn -pl <module> -am install` | `mvn -pl <module> exec:java` (if configured) | `mvn test` |

When `Workspace kind: none`, use the detected package manager's standard per-package commands with the **actual script names from the manifest** (e.g., `pnpm run start:dev`, not `pnpm run dev`, when the script is named `start:dev`).

## Schema Bootstrap

Rendered inside Installation. **Pick exactly one primary mechanism per destination DB** — never present two schema-creating mechanisms as fungible (an ORM history plus a hand-maintained `DatabaseNew.sql` against the same DB usually conflict). Precedence:

1. **ORM migration tool detected** (*Database migrations* signal) → its migrate command from the catalog below is primary; demote `raw-sql` rows.
2. **Raw-SQL only** → the first `raw-sql` row by detector order is primary; demote the rest.
3. **Seed / fixture only** → render as the "populate seed data" step. Seeds never compete with schema mechanisms — when both exist, schema first, then a follow-up bullet: "After the schema is in place, populate seed data: `<seed-invocation>`".

| ORM tool | Migrate command |
|---|---|
| `prisma` | `npx prisma migrate deploy` |
| `alembic` | `alembic upgrade head` |
| `flyway` | `flyway migrate` |
| `ef` / Entity Framework Core | `dotnet ef database update` |
| `liquibase` | `liquibase update` |
| `knex` | `npx knex migrate:latest` |
| `sequelize` | `npx sequelize db:migrate` |
| `typeorm` | `npm run typeorm migration:run` (or the project's wrapping script) |
| `rails` | `bundle exec rails db:migrate` |
| `phoenix-ecto` | `mix ecto.migrate` |

In-code migrations (e.g., GORM `AutoMigrate`): skip the migrate bullet and render `> Schema is migrated in application code — there is no separate migrate command.` Demoted mechanisms render as a 2-space-indented blockquote under the primary bullet, exactly: `> **Alternative bootstrap script:** \`<demoted-invocation>\` — apply only if the primary leaves required tables missing. Otherwise running both can conflict.`

**Connection-mode-aware invocation.** When the destination DB's *Recommended runtime* is `Docker-preferred` (or the user kept *Docker (offline)*), replace the detector's bare invocation hint with the host-side form below — the bare form assumes a local default instance with Windows/peer auth, wrong for Docker. Keep the bare form for *Local install only*. Passwords go through the per-tool env var (`export <VAR>='<password-placeholder>'` bash; `$env:<VAR> = '<password-placeholder>'` PowerShell); `mongosh` keeps the password in the URI (no env-var alternative).

| CLI | Bare form (Local install only) | Docker-preferred / Docker (offline) form | Password env var |
|---|---|---|---|
| `sqlcmd` (SQL Server) | `sqlcmd -i <file>` | `sqlcmd -S "<host>,<host-port>" -U <user> -C [-d <db>] -i <file>` | `SQLCMDPASSWORD` |
| `psql` (PostgreSQL) | `psql -f <file>` | `psql -h <host> -p <host-port> -U <user> -d <db> -f <file>` | `PGPASSWORD` |
| `mysql` (MySQL/MariaDB) | `mysql < <file>` | `mysql -h <host> -P <host-port> -u <user> <db> < <file>` | `MYSQL_PWD` |
| `mongosh` (no auth) | `mongosh --file <file>` | `mongosh "mongodb://<host>:<host-port>/<db>" --file <file>` | — |
| `mongosh` (root credentials set) | `mongosh --file <file>` | `mongosh "mongodb://<user>:<password-placeholder>@<host>:<host-port>/<db>?authSource=admin" --file <file>` | (password in URI) |

Substitution — from the same snippet the External Services subsection rendered: `<host>` → `127.0.0.1` on Windows, else `localhost` (see `external-services-docker.md` §Pre-Conditions Block); `<host-port>` → the snippet's `-p` host port; `<user>` → the snippet's user env var value or the image default (`sa` / `postgres` / `root` / `MONGO_INITDB_ROOT_USERNAME` value); `<password-placeholder>` → the snippet's password placeholder, kept as a placeholder (the file is committed); `<db>` → the placeholder `<db-name>` (the reader fills it in); `<file>` → the Schema Bootstrap row's *File* column verbatim (already root-relative — never re-join the *Directory* column). Select the `mongosh` row by snippet shape per `external-services-docker.md` §Verify Commands. ORM migrate commands are NOT enriched with connection flags — ORMs read their own config. Step 6 re-checks every rendered invocation against the flag sets and substitution rules above.

## Diagnostic Ladder — container running but host can't connect

**Trigger:** a service is Docker-preferred (or Docker (offline) kept) AND its *Verify `<service>` is reachable* bullet rendered in Common Issues (if that bullet was dropped, drop the ladder too). Render as one bullet in Common Issues:

```markdown
- **Host can't connect to <Service> on `<host>:<host-port>` but `docker ps` shows the container as `Up`?** Walk down this ladder:
  1. **Does the connection work from inside the container?** Run the `**Verify <service> is reachable.**` bullet above. If it succeeds inside but the host fails, the problem is between the host and the published port.
  2. **(Windows hosts) Does your connection string still use `localhost`?** Replace `localhost` with `127.0.0.1`. The snippet publishes `-p 127.0.0.1:<host-port>:<container-port>` (IPv4-only); Windows resolves `localhost` to `::1` (IPv6) first and the lookup times out. (Render only when Hardware / OS Requirements contains Windows; otherwise drop and renumber.)
  3. **Is the host port actually mapped?** `docker port <project-slug>-<service-slug>` — expect `<container-port>/tcp -> 127.0.0.1:<host-port>`. If not, recreate the container with the correct `-p`.
```

Substitute `<service>`, `<host>`, `<host-port>`, `<project-slug>-<service-slug>` from the rendered snippet's values.

## Multi-Repo Workspace Template

For the workspace root (not version-controlled). H2 sections, in this order:

```markdown
# [Workspace Name] — How to Run

## Repositories
[table: Repo | Path | Purpose]

## Source Dependencies / Clone All
[git clone --recursive <meta-repo-url> when a meta-repo with submodules exists; else per-repo clone commands — the primary clone lives ONLY here, never repeated under Setup]

## Prerequisites
[aggregated across repos — OS, hardware, toolchain & SDKs]

## Environment Setup
[per-repo env files and shared config keys to set BEFORE running Setup; point at the External Services Pre-Conditions Blocks for keys that must change when a service runs in Docker]

## Setup
[per-repo install commands, or a setup script]

## External Services
[shared infrastructure across repos]

## Running Everything
[how to start all services/apps together]
```

Environment Setup is deliberately BEFORE Setup here: per-repo Setup commands (installs, migrations, seeds) frequently read connection strings, registry tokens, and credentials whose committed defaults must be overridden first. The single-project analog: when the *Private registry* signal is set or *Local TLS cert* is `mkcert`, Environment Setup must precede the language-level install — Step 6 surfaces a conflict when it doesn't.
