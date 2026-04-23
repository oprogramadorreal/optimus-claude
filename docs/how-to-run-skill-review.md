# `/optimus:how-to-run` skill review

## Refined evaluation

### Context

`/optimus:how-to-run` was re-run against the Audaces ISA project (C#/.NET 8 backend + Angular 19 frontend multi-repo workspace) with the current plugin. The output (`HOW-TO-RUN.md`, 295 lines) was compared to a prior-plugin output (`HOW-TO-RUN_old.md`, 346 lines). This review documents how the skill behaved, where it regressed, and the concrete skill-level changes that would restore breadth without undoing the recent Docker-gates hardening.

Anti-overfit constraint: every accepted change must help a broad project class (Python/Poetry, Node pnpm monorepo, Go single-binary CLI, Rust workspace, polyglot Docker-Compose stack, Java/Gradle multi-module). ISA is a test case, not a target.

### Executive verdict

- **Tone and onboarding narrative improved; reference completeness regressed.** The new version has a warmer opening, explicit start-order ("backend first"), "Expected result" validation lines under Running in Development, and tighter Docker snippets that cite vendor pages. These are real wins.
- **The Docker-gates hardening produced a systemic regression: service coverage collapsed from 7 → 4.** Firebase, Audaces ID / OIDC, and four internal APIs disappeared from External Services; the Environment-Setup config-key list shrank from 18 → 5; the LocalStack offline alternative for AWS S3/SNS was dropped. These are not ISA quirks — the same skill would silently omit any service referenced only in app-config files on Spring, Rails, Elixir, .NET, Laravel, or any cloud-native project.
- **Single highest-impact issue.** The detector only scans `docker-compose.yml` + migration tooling for external services and `.env.example` for environment variables. Projects that configure services through their framework's config files (`appsettings*.json`, `application.yml`, `config/config.exs`, Rails initializers) are systematically under-documented.
- **Two secondary but generalizable issues.** (a) The Canonical Image Catalogue is keyed by exact service name, so vendor-branded cloud services (AWS S3, Azure Cosmos, GCP Pub/Sub) don't resolve to their emulators. (b) Clone commands appear in both *Source Dependencies* and *Installation* templates, producing a confused top-down flow.
- **Net verdict.** New version wins on structure and start-path clarity, loses on completeness. The 6-item skill change below restores the lost breadth without reintroducing the accuracy problems the Docker-gates hardening fixed.

### Quality assessment of the current HOW-TO-RUN.md

Each finding is tagged: `all-projects` / `stack-class: <X>` / `ISA-specific — discard`.

#### Strengths worth preserving in the skill
- Opening is purpose-driven, not file-pedantic. [`all-projects`]
- "Expected result: ASP.NET Core listens at..." under Running-in-Development gives devs a concrete check. [`all-projects`]
- "Start order: backend first" guidance removes a real ambiguity. [`all-projects`, applies to any multi-component dev loop]
- Per-service `- Source: [...]` citations under Docker snippets are honest about where the image info came from. [`all-projects`]
- Explicit "there is no `.env.example`" statement when none exists — stops the reader from hunting for a file that isn't there. [`all-projects`]
- Docker snippets bind `127.0.0.1:` only and use versioned tags — safer than the old blanket `-p 6379:6379`. [`all-projects`]

#### Gaps
- External Services table is incomplete. Firebase, OIDC, internal REST APIs are in `appsettings.development.json` but missing from the rendered doc. [`stack-class: non-.env config files` — .NET, Spring Boot, Rails, Elixir, PHP, Go with Viper/Koanf]
- Environment Setup lists only 5 config keys where the project has ~18 top-level sections. Devs don't know what to ask for. [`stack-class: non-.env config files`]
- No schema-bootstrap instructions for projects with raw SQL scripts (`DatabaseNew.sql`, `db/*.sql`) or seed files (`db/seeds.rb`, `seed.exs`, `loaddata` fixtures). The skill only handles ORM migrations. [`all-projects` with a DB but no ORM migration directory]
- No LocalStack / Cosmos Emulator / Pub-Sub-emulator alternative for cloud-native services. [`stack-class: cloud-native projects`]
- Redis "Port 6379 is the Redis default; the vendor page did not expose the port in structured form" is robot-speak. [`all-projects`]
- Clone commands appear in two sections (Source Dependencies *and* Installation). A reader following top-down hits "clone" twice. [`all-projects`]
- No mention of dev tools like Chrome/Chromium for Karma tests, SSMS for SQL Server, IDEs the README recommends. [`all-projects`, any project with browser-driven test runners, DB GUIs, or SDK installers]
- "Obtain credentials from a teammate" doesn't say *what* to ask for. [`all-projects` with shared-cloud defaults]
- `npm run export-scss-vars` is surfaced but not explained — non-obvious wrapper commands need "does: ..." hints. [`all-projects`]
- "15 .csproj projects" is an unverified exact-count claim. [`all-projects`]
- ISA-specific friction (IIS Express port 51914 fixed; Docker Desktop Linux-container mode; Audaces GitLab access; theme submodule blocks SCSS compile) is correctly surfaced by existing skill machinery. [`ISA-specific — discard`]

### Regressions vs improvements

| Aspect | Old | New | Verdict | Fix if regression |
|---|---|---|---|---|
| Opening | Technical ("not version-controlled") | Purpose-driven ("fashion-collection platform — fresh clone to running") | **Improvement** | — |
| Repositories table | 4 columns, stack isolated | 3 columns, stack folded into Purpose prose | **Improvement** | — |
| Prerequisites scope | Ambiguous about OSes | Explicitly scopes Windows + Docker | **Improvement** | — |
| External Services table | 7 rows | 4 rows | **Regression** | Detector: scan app-config files for service references (item #1) |
| SQL Server schema bootstrap | 3 paths (manual / SQL script / EF) | 0 in External Services, 1 optional in Installation | **Regression** | Detect raw-SQL + seed-file bootstrap (item #4) |
| LocalStack (S3+SNS) | Present with Docker snippet | Dropped | **Regression** | Vendor→emulator index (item #3) |
| Firebase section | Present, Emulator Suite | Dropped | **Regression** | Items #1 + #3 |
| OIDC / identity section | Present with local-mock note | Dropped | **Regression** | Item #1 |
| Internal APIs section | Present with domain names | Dropped | **Regression** | Item #1 |
| Environment Setup key list | 18 sections enumerated | 5 keys enumerated | **Regression** | Enumerate app-config top-level sections (item #2) |
| Environment override note | Absent | Adds `launchSettings.json` env-var override note | **Improvement** | — |
| Installation backend | Restore only | Adds optional EF migration command | **Improvement** | — |
| Clone instructions | Single block at top | Split across Source Deps + Installation | **Regression** | Consolidate clone into Installation (item #5) |
| Running-in-Dev backend | Just a command | Adds "Expected result:" validation line | **Improvement** | — |
| Running-in-Dev frontend env list | 13 configurations listed | "E.g., dev, beta, alpha" | Neutral / slight regression | Acceptable at any scale |
| Windows-containers warning in Common Issues | Names all 4 affected services | Names only SQL Server | Regression (minor) | Auto-fixes with item #3 |
| Redis caveat wording | N/A | "not exposed in structured form" | Regression (polish) | Humanize caveats (item #6) |
| Tone / length | 346 lines encyclopedic | 295 lines tight | Neutral | — |

**8 regressions, 6 improvements. All 8 regressions trace to one of 6 skill-level changes below.**

### Skill improvements — ordered by impact

Each item lists: (1) the gap, (2) files to change, (3) the concrete change, (4) archetypes helped, (5) regression risk + mitigation.

#### 1. Detect external services from framework config files, not just `docker-compose.yml` + ORM migrations

**Gap.** The detector's External Services source list (Task 5 in [project-environment-detector.md](../../../skills/how-to-run/agents/project-environment-detector.md)) covers `docker-compose.yml`, `database.yml`, `prisma/schema.prisma`, `alembic.ini`, `knexfile.*`, `ormconfig.*`, and migration directories. Services wired up through framework config files (authority URLs, SNS topic ARNs, Firebase project IDs, internal REST endpoints) are invisible. This is what pruned ISA's table from 7 → 4 and would do the same to any Spring/Rails/Elixir/.NET/Laravel project.

**Files.**
- [skills/how-to-run/agents/project-environment-detector.md](../../../skills/how-to-run/agents/project-environment-detector.md) — add Task 5b, extend return schema with a `Confidence` column.
- [skills/how-to-run/references/how-to-run-sections.md](../../../skills/how-to-run/references/how-to-run-sections.md) — add a signal row mapping app-config service references to External Services.
- [skills/how-to-run/references/external-services-docker.md](../../../skills/how-to-run/references/external-services-docker.md) — extend §Service Classification Tables to resolve `<vendor>Settings` suffixes and auth-config names to `cloud-native-only`.

**Concrete change.** Add **Task 5b — Detect external services from framework config files**:

> For each framework config file present at repo root or under standard locations (`appsettings*.json`, `application.yml`, `application.yaml`, `application.properties`, `config/*.yml` [Rails], `config/*.exs` [Elixir/Phoenix], `config/config.php`, `config.php`, `config.yaml`, `config.yml`, Spring profile variants), parse top-level keys (or YAML/JSON sections) and flag sections whose name or contents match any of: `redis`, `mongo`, `mongodb`, `nosql`, `database`, `db`, `connectionstring`, `connection_string`, `datasource`, `authority`, `oidc`, `openidconnect`, `identity`, `auth0`, `cognito`, `okta`, `keycloak`, `firebase`, `firestore`, `aws`, `s3`, `sns`, `sqs`, `storage`, `blob`, `queue`, `bus`, `messaging`, `elastic`, `search`, `rabbitmq`, `kafka`, `smtp`, `mail`, `license`, `licensemanager`, external FQDNs (hostname with a dot, not `localhost`). For each match, emit a row with `Service = <section-name>` (title-cased), `Source = <file>:<line>`, `Endpoint = <extracted-URL-or-"shared-cloud endpoint">`, `Type = <inferred-from-section-name>`, and `Confidence: candidate`.
>
> Never parse secret values — only key names, section names, and hostnames. Apply the same path/URL sanitization regexes used in Task 0b (reject `..`, scheme smuggling, control chars). Cap at 20 services per file; beyond that, emit "N+ more — see <file>" without enumerating further.

Add a `Confidence` column to the External Services return table (`confirmed` for compose/migration sources, `candidate` for app-config sources). Render candidates with a `(candidate)` marker in Step 3's assessment and in the final HOW-TO-RUN.md; the user can drop any candidate via Step 1 "Correct first" (see Resolution #1 below — candidates are auto-included, not per-item prompted).

Extend the `cloud-native-only` classification: service names matching `OIDC`/`OpenIDConnect`/`IdentityProvider`, `Firebase`/`Firestore`, or vendor-branded names with a `<vendor>Settings` suffix (`AudacesIdSettings`, `LicenseManagerSettings`) resolve to `cloud-native-only`, triggering the *Shared-cloud, no Docker alternative* template.

**Archetypes helped.**
- .NET / ASP.NET (appsettings sections like `AWS`, `RedisSettings`, `OpenIdConnect`).
- Spring Boot (`spring.datasource`, `spring.redis`, `spring.security.oauth2`).
- Rails (`config/database.yml`, `config/storage.yml`, `config/initializers`).
- Phoenix/Elixir (`config/config.exs`, `config/runtime.exs`).
- Laravel/PHP (`config/*.php`).
- Go with Viper/Koanf (`config.yaml`, `config.toml`).
- Any polyglot Docker stack where services are shared-cloud, not compose-managed.

**Risk / mitigation.** False positives from strings that look like service names but aren't. Mitigate with: (a) `Confidence: candidate` marker + the existing Step 1 "Correct first" flow; (b) require a known keyword OR an FQDN-shaped value, not just a `<vendor>Settings` label; (c) cap at 20/file. Node + compose-managed-only projects are unaffected (no app-config file match → no rows added).

#### 2. Enumerate environment config keys from app-config files, not just `.env.example`

**Gap.** [Task 6](../../../skills/how-to-run/agents/project-environment-detector.md) reads `.env.example`/`.env.sample`/`.env.template` only. Projects configured via `appsettings.json`, `application.yml`, Rails `config/secrets.yml`, or Spring profile files produce an empty Environment Setup — the 18 → 5 collapse. The template at [how-to-run-sections.md §Environment Setup](../../../skills/how-to-run/references/how-to-run-sections.md) assumes `.env.example` → `.env`.

**Files.**
- [skills/how-to-run/agents/project-environment-detector.md](../../../skills/how-to-run/agents/project-environment-detector.md) — extend Task 6 to enumerate top-level sections of detected app-config files.
- [skills/how-to-run/references/how-to-run-sections.md](../../../skills/how-to-run/references/how-to-run-sections.md) — add a "Config-file-driven environment (non-dotenv stacks)" template variant.

**Concrete change.** Extend Task 6's Environment Setup return schema: `File`, `Format` (`dotenv`/`json`/`yaml`/`properties`/`exs`), `Variable count`, `Key variables` (top-level section names or env-var names). Cap `Key variables` **at 25 names per file** (see Resolution #2).

Add template (b) to §Environment Setup:

```markdown
**(b) Config-file-driven environment (non-dotenv stacks)**

### Environment Setup

Local configuration lives in `<config file>` (format: `<format>`). The file is committed with development defaults; override locally by editing it or by setting the runtime environment variables listed in `<launch-file or override-hint>`.

Top-level sections that require values before running locally:

- `<SectionName>` — `<one-line description derived from section-name semantics>`
- ... [one bullet per detected top-level section, capped at 25 per file]

[If truncated:] See `<config file>` for the full list.

**Never commit real secrets.** Treat any key whose name matches `(?i)(key|secret|password|token|credential|private)` as sensitive.
```

SKILL.md Step 4 picks template (a) when `.env.example` exists, (b) when only app-config files exist, or both when both exist.

**Archetypes helped.** Same class as #1 — any non-dotenv stack. A Go CLI with a single `.env.example` keeps rendering (a). A pnpm monorepo with `.env.example` is unchanged.

**Risk / mitigation.** Risk: dumping dozens of keys. Mitigation: cap at 25 per file with an explicit "See `<file>` for the full list" fallback.

#### 3. Vendor-service → emulator mapping in the canonical image catalogue

**Gap.** [§Canonical Image Catalogue](../../../skills/how-to-run/references/external-services-docker.md) is keyed by exact service name. Decision Heuristics rule 3 sets the Docker alternative only "if the service type appears in the canonical image catalogue" — so a detected `AWS S3` finds no row, Alternative becomes `—`, and LocalStack is dropped. Same miss affects DynamoDB (vendor emulator exists), Cosmos DB (emulator in Known Vendor Emulators but no path from service name), Pub/Sub, and anything Azure Blob Storage-shaped.

**Files.**
- [skills/how-to-run/references/external-services-docker.md](../../../skills/how-to-run/references/external-services-docker.md) — add a *Vendor-Service → Emulator Index*, update rule 3, append Azurite to the Canonical Image Catalogue.

**Concrete change.** Insert a new section between *Canonical Image Catalogue* and *Known Vendor Emulators*:

```markdown
## Vendor-Service → Emulator Index

When Decision Heuristics rule 3 evaluates a service with Docker suitability `cloud-native-only`, or any cloud-branded name that does not match a row in the Canonical Image Catalogue by name, match first against this index. A hit means the emulator image (or launch tool) from the referenced row is the offline alternative.

| Detected service name pattern (case-insensitive whole-token) | Maps to |
|---|---|
| `AWS S3`, `AWS SNS`, `AWS SQS`, `AWS Lambda`, `AWS DynamoDB Streams`, `S3`, `SNS`, `SQS` | LocalStack row (Canonical Image Catalogue) |
| `AWS DynamoDB`, `DynamoDB` | DynamoDB Local (Known Vendor Emulators) |
| `Azure Cosmos DB`, `Cosmos DB`, `Cosmos` | Azure Cosmos DB Emulator (Known Vendor Emulators) |
| `Firebase`, `Firestore`, `Firebase Auth`, `Firebase Storage` | Firebase Local Emulator Suite (Known Vendor Emulators) |
| `Google Cloud Pub/Sub`, `Pub/Sub`, `GCP Pub/Sub` | Pub/Sub Emulator (Known Vendor Emulators) |
| `Azure Blob Storage`, `Azure Queue Storage`, `Azure Table Storage` | Azurite (add row to Canonical Image Catalogue) |
```

Append Azurite to the Canonical Image Catalogue: `mcr.microsoft.com/azure-storage/azurite:<stable-tag>`, cite `learn.microsoft.com`.

Update rule 3's "Step 3 provisional Alternative" text:

> Set Alternative to "Docker (offline)" if the service type appears in the [canonical image catalogue](#canonical-image-catalogue-seeds) **OR maps to a row via the [Vendor-Service → Emulator Index](#vendor-service--emulator-index)**; otherwise set Alternative to `—`.

**Archetypes helped.** AWS-heavy (S3/SNS/SQS/DynamoDB → LocalStack, DynamoDB Local), Azure-heavy (Cosmos → Emulator, Blob → Azurite), GCP (Pub/Sub/Firestore). Any polyglot cloud app.

**Risk / mitigation.** Risk: surfacing an emulator that doesn't cover the feature the project actually uses (LocalStack free tier gaps, Cosmos Emulator Windows-only). Mitigation: the existing tier-scope gate on LocalStack continues to guard pro-only usage; emulator rows keep their caveats. Risk: over-eagerly mapping a service to an emulator the user doesn't want. Mitigation: the existing Step 4 multi-select downgrade prompt already gives per-service opt-out — honor it for index-matched services too.

#### 4. Detect schema bootstrap via raw SQL scripts and seed files, not just ORM migrations

**Gap.** [Task 5](../../../skills/how-to-run/agents/project-environment-detector.md) detects `prisma/schema.prisma`, `alembic.ini`, `knexfile.*`, `ormconfig.*`, and migration directories — but a raw `DatabaseNew.sql`/`Database.sql`/`db/seeds.rb`/`priv/repo/seeds.exs` is invisible. The old ISA doc enumerated three bootstrap paths; the new doc dropped SQL-script bootstrap entirely. Hits any project that ships raw SQL init scripts or language-specific seed files.

**Files.**
- [skills/how-to-run/agents/project-environment-detector.md](../../../skills/how-to-run/agents/project-environment-detector.md) — add schema-bootstrap detection to Task 6.
- [skills/how-to-run/references/how-to-run-sections.md](../../../skills/how-to-run/references/how-to-run-sections.md) — extend the Installation template with a schema-bootstrap sub-block.

**Concrete change.** Add to Task 6:

> - **Schema bootstrap scripts:** glob for `*.sql` at repo root, under `db/`, `database/`, `scripts/sql/`, `data/`, `migrations/`, `bootstrap/` — report filenames, not contents. Glob for seed files: `db/seeds.rb` (Rails), `priv/repo/seeds.exs` (Phoenix), `fixtures/*.json`/`*.yaml` (Django), `seed.ts`/`seed.js`/`seed.mjs` at repo root or inside `prisma/`/`scripts/`. Cross-reference the External Services table: emit a `Schema bootstrap` row only when a SQL database service is detected AND any of these files exist. Cap file list at 5 entries; collapse the rest into "N+ more under `<dir>`".

Extend the Installation skeleton at §Installation to render — per Resolution #4 — an **unordered "Choose one:" block** (no prescribed priority):

```markdown
[If any of migration tooling, raw SQL bootstrap scripts, or seed files detected:]
Initialize database schema. Choose one:

- [If ORM migration tooling detected:] Apply migrations: `<migration command>`.
- [If raw SQL bootstrap scripts detected:] Execute `<SQL file>` against the database (via `sqlcmd`, `psql -f`, `mysql <`, or a GUI client).
- [If seed scripts detected:] Run the seed script: `<seed command>`.
```

**Archetypes helped.** Rails, Phoenix/Elixir, any project with a `.sql` file under `db/`, Node projects with hand-written `scripts/seed.js`, Python projects with fixtures but no Alembic, .NET projects with hand-written SQL.

**Risk / mitigation.** Risk: listing irrelevant `.sql` files (e.g., test fixtures). Mitigation: require a detected SQL database AND the file under a DB-shaped directory; cap at 5. Projects with only ORM migrations render a single bullet (the migration command) — no double-rendering.

#### 5. Consolidate clone commands into a single section

**Gap.** Two templates in [how-to-run-sections.md](../../../skills/how-to-run/references/how-to-run-sections.md) emit `git clone` — *Source Dependencies* (if submodules detected) and *Installation* (unconditionally). Affects any repo with submodules regardless of stack.

**Files.**
- [skills/how-to-run/references/how-to-run-sections.md](../../../skills/how-to-run/references/how-to-run-sections.md) — restructure both templates.

**Concrete change.** Rewrite *Source Dependencies* as fix-after-clone only:

```markdown
### Source Dependencies

[If .gitmodules detected:]
This repo uses git submodules. If you already cloned without `--recursive`, initialize them now:
\`\`\`bash
git submodule update --init --recursive
\`\`\`
(The `--recursive` form of the clone in the Installation section below handles submodules on a fresh clone.)

[If sibling repos detected — unchanged from current template]
```

Rewrite the *Installation* clone block:

```markdown
### Installation

Clone the repository[ with submodules]:
\`\`\`bash
git clone [--recursive ]<repo-url>
cd "<project-name>"
\`\`\`
```

Step 4 substitutes `--recursive` and the ` with submodules` phrase when `.gitmodules` is present; both collapse when absent.

**Archetypes helped.** Any project with submodules (Node, Python, Go, Rust, C/C++, game engines with submodule vendoring, multi-repo workspaces).

**Risk / mitigation.** None — template-layout edit only.

#### 6. Humanize caveat rendering in Step 4

**Gap.** Step 4's web-search recipe generates caveats like *"Port/volume taken from the skill's canonical catalogue because the vendor page did not expose them in structured form"*. Correct but reads like implementation notes.

**Files.**
- [skills/how-to-run/references/external-services-docker.md §Web-Search Recipe](../../../skills/how-to-run/references/external-services-docker.md) — rewrite the caution template.
- [skills/how-to-run/SKILL.md](../../../skills/how-to-run/SKILL.md) Step 4 — add a Content Principle.

**Concrete change.** Replace the current caveat wording:

> **Caveat rendering.** When the catalogue short-circuit fills in a field (port / volume only), append a single-line note to the snippet block as `> Note: <field> is the documented default for <service>.` Do not say "the vendor page did not expose the port in structured form" — that is a skill-internal detail, not guidance the developer needs.

Add to SKILL.md Step 4 §Content Principles:

> - **Humanize caveats.** Any caveat emitted from a Step-4 recipe (catalogue fallback, moving-tag rejection, LocalStack tier gate) must describe *what the reader should know or do*, not *why the skill decided something*. Example: "Port 6379 is the Redis default" is better than "The vendor page did not expose the port in structured form."

Per Resolution #5, this is editorial only — no Step 6 regex gate.

**Archetypes helped.** Every project that triggers the Docker web-search recipe.

**Risk / mitigation.** None. Text-only change.

### Lower-impact polish (ship together or not at all)

- **Make "Expected result:" mandatory in every Running-in-Development sub-template.** Sub-template (a) already suggests it; (b) and (c) imply it — require it in all three.
- **Detect dev-tool recommendations from READMEs.** Extend Task 0c to scan READMEs for: `Chrome`, `Chromium`, `Google Chrome`, `Firefox`, `Visual Studio`, `IntelliJ`, `PyCharm`, `GoLand`, `Rider`, `Rust Rover`, `VS Code`, `VSCode`, `SSMS`, `Azure Data Studio`, `DBeaver`, `pgAdmin`, `RedisInsight`, `Postman`, `Insomnia`, `ngrok`. Emit a *Recommended developer tools* row under Prerequisites.
- **Credential-request hint.** In the *Shared-cloud, no Docker alternative* template, replace `Obtain credentials from a teammate` with `Obtain credentials for <service-slug> from a teammate (typically: connection string, access key / secret, client secret)`.
- **Reject unverifiable exact counts.** SKILL.md Step 4 Content Principles: disallow numeric exact-counts unless Step 6 verification can re-derive them from the filesystem. Replace claims like "Isa360.sln consolidates 15 `.csproj` projects" with the verified count or "multiple".
- **Explain non-idiomatic wrapper commands.** When the detected dev command is a wrapper (e.g., `npm run serve` → `<SCSS export> && ng serve`), render a `> <wrapper-command> does: <expanded-form>` line under the command.

### Out-of-scope (rejected to avoid overfitting)

- ISA-specific "IIS Express port 51914 is in two files" note. Already surfaced generically by existing Common Issues heuristic for any dual-port-reference project.
- Dropping the "15 .csproj" fix into a .NET-only code path. Promoted to the general "reject unverifiable exact counts" principle above.
- Security-scanner warning on committed `appsettings.development.json` secrets. Out of scope for this skill.
- Audaces-private-GitLab submodule access. Already correctly handled by existing submodule detection + Common Issues.
- Explaining `npm run export-scss-vars` specifically. Generalized to "explain non-idiomatic wrapper commands".
- Rewriting HOW-TO-RUN.md for ISA as the deliverable. Explicitly out of scope — the skill is the target.
- Expanding the Docker web-search recipe to fetch changelogs / release notes for tag-pinning decisions. Orthogonal; would slow every skill run.

### Resolutions to the plan's open questions

1. **Candidate-service UX.** **Option (a) — auto-include with a `(candidate)` marker.** The user already reviews the Context Summary in Step 1 and can hit "Correct first" to drop anything wrong. Adding a per-service AskUserQuestion flow adds friction for config-heavy projects where 5–10 candidate services is normal. Silent inclusion (option c) is unsafe because the user can't tell what came from a grep-match vs. a confirmed compose service — so the marker is non-negotiable. Render candidates in both the Step 3 assessment table and the final HOW-TO-RUN.md with the `(candidate)` marker; trust the existing corrections path.

2. **Key-variable cap (item #2).** **Per-file, 25 names max.** A Spring Boot project with 6 profile files × 8 sections = 48 unique top-level sections total; a global cap at 25 would truncate real content. A per-file cap of 25 also bounds the output predictably (N files × 25 = the ceiling). When a single file exceeds 25, emit the first 25 alphabetically + a "See `<file>` for the full list" footnote. For duplicate section names across files (common in Spring profiles), dedupe by name within each top-level profile before truncating.

3. **Azurite and other emulator rows (item #3).** **Ship the high-signal set in the first pass; defer niche services to follow-up PRs.** The first pass covers: LocalStack (AWS S3/SNS/SQS/Lambda), DynamoDB Local, Azure Cosmos DB Emulator, Firebase Local Emulator Suite, Pub/Sub Emulator, Azurite (Blob/Queue/Table). Azure Service Bus, Event Hubs, AWS Kinesis, GCP Bigtable, Datadog/Sentry-style SaaS are explicitly *not* included — the Vendor-Service → Emulator Index must stay high-precision. Adding a row later is cheap; fielding false matches is costly. Document the add-a-row process inline in the reference file so maintainers can extend it without revisiting the skill design.

4. **Schema bootstrap precedence (item #4).** **Render as an unordered "Choose one:" list, no prescribed priority.** The skill cannot reliably rank migrations vs. SQL vs. seed scripts — different teams on the same stack choose differently. Listing them in detection order (migration tooling first, then SQL files, then seed scripts) is a deterministic rendering rule that is NOT a priority signal. The "Choose one:" phrasing tells the reader they pick, not the skill. This also sidesteps the ISA-shape vs. Rails-shape argument entirely.

5. **Caveat humanization surface (item #6).** **Purely editorial — no Step 6 regex gate.** The correct template lives in `external-services-docker.md §Web-Search Recipe`; Step 4 renders what the template says. A Step 6 gate enumerating forbidden phrases ("exposed in structured form", "canonical catalogue", "vendor page did not") is brittle: phrases drift, future caveats need different wording, and a regex-based gate would have to be updated in two places. Revisit enforcement only if drift reappears in a future skill run.

### Verification plan

1. **Re-run `/optimus:how-to-run` against ISA after each item lands.** Confirm:
   - Item #1: External Services table regains Firebase, OIDC, internal APIs with a `(candidate)` marker.
   - Item #2: Environment Setup lists 15–20 top-level sections of `appsettings.development.json`.
   - Item #3: AWS S3 renders with LocalStack as Docker alternative; Firebase renders with Firebase Local Emulator Suite.
   - Item #4: Installation lists `DatabaseNew.sql` as a schema-bootstrap path alongside `dotnet ef database update` in a "Choose one:" block.
   - Item #5: Only one `git clone` command in the doc, inside Installation.
   - Item #6: Redis caveat reads "Port 6379 is the Redis default" (or equivalent human-facing form).
2. **Archetype regression test.** Run the skill against three projects of differing shapes; verify no regressions:
   - A pure Node + compose project with `.env.example` (item #2 must not break dotenv flow).
   - A Go single-binary CLI with no services (External Services still cleanly empty).
   - A Python/Poetry FastAPI with `alembic.ini` (item #4 must not double-render migrations).
3. **Execute the generated HOW-TO-RUN.md top-down on a fresh clone** of ISA (simulated: delete `node_modules/`, `bin/`, `obj/`, reset `appsettings.development.json`). Backend and frontend must reach a running state with no unanswered questions.
4. **Run the plugin test suite:**
   ```bash
   bash scripts/validate.sh && bash scripts/test-hooks.sh && python -m pytest test/harness-common/ test/deep-mode-harness/ test/test-coverage-harness/
   ```

### Critical files to modify

- [skills/how-to-run/SKILL.md](../../../skills/how-to-run/SKILL.md) — Step 4 Content Principles (candidate rendering for item #1, humanize caveats for item #6; polish: reject exact counts, explain wrapper commands).
- [skills/how-to-run/agents/project-environment-detector.md](../../../skills/how-to-run/agents/project-environment-detector.md) — new Task 5b (app-config service detection), extended Task 6 (config-file-driven env vars, schema-bootstrap detection), extended Task 0c (dev-tool recommendations).
- [skills/how-to-run/references/how-to-run-sections.md](../../../skills/how-to-run/references/how-to-run-sections.md) — Installation template (clone consolidation + bootstrap sub-block), Source Dependencies template (submodule-only), Environment Setup template variant (config-file-driven), Running in Development (mandatory Expected result).
- [skills/how-to-run/references/external-services-docker.md](../../../skills/how-to-run/references/external-services-docker.md) — new Vendor-Service → Emulator Index, Service Classification Tables (`cloud-native-only` matcher), humanized caveat wording, Azurite catalogue row.
- [.claude-plugin/plugin.json](../../../.claude-plugin/plugin.json) + [README.md](../../../README.md) — version bump when the change lands.
