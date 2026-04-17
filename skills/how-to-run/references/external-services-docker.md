# External Services: Docker-vs-Local Decision

Per-service decision logic, web-search recipe, and snippet templates for the *External Services* section when no `docker-compose.yml` covers the project's infrastructure. Referenced by [`how-to-run-sections.md`](how-to-run-sections.md) and by Step 4 of [`SKILL.md`](../SKILL.md).

**Docker is never forced.** Local installs and shared-cloud endpoints remain first-class options. This file encodes how to *offer* Docker when it clearly helps a new developer get running faster.

## Contents

- [Decision Heuristics](#decision-heuristics)
- [Web-Search Recipe](#web-search-recipe)
- [Canonical Image Catalogue (seeds)](#canonical-image-catalogue-seeds)
- [Snippet Templates](#snippet-templates)
- [Citation Format](#citation-format)
- [Windows / Docker Desktop Caveats](#windows--docker-desktop-caveats)
- [Registry Allowlist](#registry-allowlist)

## Decision Heuristics

Input: each service from the detector's *External Services* table, plus its default endpoint read from the referenced config file.

Apply in order and stop at the first match:

1. **GUI client / IDE / CLI tool.** Service name matches `SSMS`, `Management Studio`, `Compass`, `Workbench`, `DBeaver`, `Azure Data Studio`, `Studio 3T`, `RedisInsight`, `pgAdmin`, any `CLI`, any `Desktop`. → **Local install only.** Do not search Docker.
2. **Cloud-native-only default endpoint.** The referenced config file's default endpoint hostname ends in `.amazonaws.com`, `.azure.com`, `.cosmos.azure.com`, `.windows.net`, `.googleapis.com`, `.firebaseio.com`, `.firestore.googleapis.com`, `.audaces.com`, or any FQDN that is clearly not `localhost` / `127.0.0.1` / an IP literal. → **Shared-cloud primary.** Add "Offline alternative: Docker" only if the service type appears in the [canonical image catalogue](#canonical-image-catalogue-seeds) AND a current image is found by the web-search recipe.
3. **Localhost / empty / unknown default endpoint** for a known server daemon (database, queue, cache, object store, identity provider). → **Docker-preferred.** Local install stays as alternative.
4. **Web-search recipe fails to find a canonical image.** → **Local install only.** Log a caution in Step 3: "A Docker option was considered for <service> but no vendor-maintained image was found — falling back to local install."
5. **Windows-host incompatibility** flagged in vendor docs. → render the snippet with the shared [Windows caveat note](#windows--docker-desktop-caveats) and prefer Docker only if the caveat is a one-liner ("Linux-container mode required"). If the caveat is deeper (kernel features, privileged mode), prefer local install.

Write the three-axis decision — `recommended`, `alternative`, `reason` — into the Step 3 assessment table so the user can override any row via the existing "Correct first" path. Do not emit a new `AskUserQuestion` prompt per service.

## Web-Search Recipe

Run this recipe in Step 4 for every service classified as **Docker-preferred** or **Docker-as-alternative**. No image name is ever taken from model memory. If any step fails, fall back to local-install-only and log a caution.

1. **Query Docker Hub first.** `WebSearch` for `"<service> docker official image site:hub.docker.com"`. Prefer results tagged *Docker Official Image* or *Verified Publisher* (vendor-maintained).
2. **For vendor-registry services, also search vendor docs.** Some vendors publish outside Docker Hub — SQL Server lives at `mcr.microsoft.com/mssql/server`, not on Docker Hub. Search `"<service> docker <vendor> quickstart"` (e.g., `learn.microsoft.com`) and prefer the vendor page as the canonical source.
3. **Fetch the canonical page** with `WebFetch`. Ask it to extract:
   - Image reference `<registry>/<name>:<tag>`.
   - Required env vars (credentials, licence acceptance like `ACCEPT_EULA=Y`).
   - Minimal `docker run` command.
   - Default port(s).
   - Volume mount path for persistence.
   - Supported architectures (`linux/amd64`, `linux/arm64`) — so ARM-only hosts get a `--platform` note when needed.
   - Any licence prompts or registration requirements.
4. **Validate the extracted image reference:**
   - Must match `^[A-Za-z0-9][A-Za-z0-9._/-]*:[A-Za-z0-9._-]+$`.
   - Registry host (if present) must appear in the [registry allowlist](#registry-allowlist).
   - Reject unknown registries — do not write the snippet; log a caution in Step 3.
5. **Prefer stable tags over `:latest`.** Use the newest documented version tag the vendor page recommends (e.g., `mcr.microsoft.com/mssql/server:2022-latest` over `:latest`). Reject bare `:latest` when a versioned tag is available.
6. **Cite the source URL** in the generated doc using the [citation format](#citation-format). The URL is the vendor/registry page, not the WebSearch result page.

## Canonical Image Catalogue (seeds)

**Not authoritative.** These are seed references discovered at plan time — **re-verify each one via the web-search recipe on every skill run.** Tags and registration requirements change; do not bake them in.

| Service | Image reference (seed) | Canonical source (seed) | Notes |
|---------|-----------------------|------------------------|-------|
| SQL Server | `mcr.microsoft.com/mssql/server:2022-latest` | [MS Learn — SQL Server Linux container quickstart](https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker) | Requires `ACCEPT_EULA=Y` and `MSSQL_SA_PASSWORD` meeting SQL Server password policy (≥8 chars, upper+lower+digit+symbol). Port 1433. Volume `/var/opt/mssql`. Windows: Docker Desktop in Linux-container mode. |
| MongoDB | `mongo:<stable-tag>` | [Docker Hub — mongo (Docker Official Image)](https://hub.docker.com/_/mongo) | Optional `MONGO_INITDB_ROOT_USERNAME` / `MONGO_INITDB_ROOT_PASSWORD`. Port 27017. Volume `/data/db`. |
| Redis | `redis:<stable-tag>` | [Docker Hub — redis (Docker Official Image)](https://hub.docker.com/_/redis) | Port 6379. Volume `/data` (if persistence enabled via `--appendonly yes`). Set a password with `--requirepass` when exposing beyond localhost. |
| PostgreSQL | `postgres:<stable-tag>` | [Docker Hub — postgres (Docker Official Image)](https://hub.docker.com/_/postgres) | Requires `POSTGRES_PASSWORD`. Port 5432. Volume `/var/lib/postgresql/data`. |
| MySQL / MariaDB | `mysql:<stable-tag>` or `mariadb:<stable-tag>` | [Docker Hub — mysql](https://hub.docker.com/_/mysql) / [Docker Hub — mariadb](https://hub.docker.com/_/mariadb) | Requires `MYSQL_ROOT_PASSWORD`. Port 3306. Volume `/var/lib/mysql`. |
| LocalStack (AWS S3/SNS/SQS/etc.) | `localstack/localstack:<stable-tag>` | [Docker Hub — localstack/localstack](https://hub.docker.com/r/localstack/localstack) | Set `SERVICES=s3,sns,sqs,...` to narrow scope. Recent releases require `LOCALSTACK_AUTH_TOKEN`; flag this in the snippet and cite the vendor doc. Port 4566. |

**Deliberately excluded from the seed catalogue:**

- **Firebase / Firestore** — no vendor-maintained Docker image. The Firebase Local Emulator Suite runs via `firebase emulators:start` (Node-based). When detected, render the [Local install only template](#3-local-install-only) pointing at the emulator docs.
- **Vendor-internal / proprietary APIs** (e.g., licence managers, in-house identity providers). These are cloud-shared-only; render as shared-cloud with no Docker alternative.

## Snippet Templates

Render **one** of these templates per service, chosen by the heuristics. Keep all service subsections under a single `## External Services` H2; each service is an H3.

### 1. Docker recommended

Use when the heuristic resolves to **Docker-preferred**.

````markdown
### <Service name>

**Recommended: Docker.** <One-sentence reason — e.g., "fastest path on a fresh machine, no installer required".>

```bash
docker run -d --name <project-slug>-<service-slug> \
  -e "<REQUIRED_ENV_VAR>=<placeholder>" \
  -p <host-port>:<container-port> \
  -v <project-slug>-<service-slug>-data:<container-volume-path> \
  <registry>/<image>:<stable-tag>
```

- Source: [<vendor page title>](<vendor page URL>).
- <Any required-env-var note — e.g., password policy, licence acceptance.>
- <Windows / ARM caveat if applicable — render from the shared Windows-caveats note when `<host-arch>` or `<host-os>` matches.>
- Connection details for <relevant config file / env var>: `<connection string template with the placeholder values>`.

**Alternative: local install.** <One-sentence reason to pick local — e.g., "if you already use <related GUI tool>" or "for Windows-auth connection strings".> Install from [<vendor page>](<vendor page URL>).
````

### 2. Shared-cloud primary, Docker optional

Use when the heuristic resolves to **Shared-cloud primary** AND the web-search recipe found a canonical image.

````markdown
### <Service name>

**Recommended: shared cloud.** This project's default configuration points at <cloud endpoint, e.g., "Azure Cosmos DB at port 10255">. Obtain credentials from a teammate — they are not published here.

**Offline alternative: Docker.** If you need to run without connectivity to the shared endpoint:

```bash
docker run -d --name <project-slug>-<service-slug> \
  -p <host-port>:<container-port> \
  <registry>/<image>:<stable-tag>
```

- Source: [<vendor page title>](<vendor page URL>).
- Update <config key> in <config file> to `<localhost connection string>` when running locally.
````

### 3. Local install only

Use when the heuristic resolves to **Local install only** (GUI tool, no official image, or web-search fallback).

```markdown
### <Service name>

<One-sentence reason Docker is not a fit — e.g., "<Service> is a Windows GUI; there is no server image.">

Install from [<vendor page>](<vendor page URL>).

[Optional: one-line note on a CLI alternative that ships inside a related container, or on the vendor's own local-emulator tool.]
```

## Citation Format

Every Docker image reference written to `HOW-TO-RUN.md` MUST be followed by a source citation, exactly:

```
- Source: [<Vendor page title>](<vendor page URL>).
```

The `- Source: [` prefix is what the Step 6 validator pattern-matches. The URL must point at one of:

- `hub.docker.com/_/<name>` or `hub.docker.com/r/<vendor>/<name>` — Docker Official / Verified Publisher pages.
- `learn.microsoft.com/...` — Microsoft Learn canonical docs.
- The vendor's own docs domain, limited to official documentation subdirectories (e.g., `docs.<vendor>.com`, `<vendor>.com/docs`).

Do not cite blog posts, Medium articles, or Stack Overflow answers — they are not authoritative.

## Windows / Docker Desktop Caveats

When the detector's OS evidence includes `Windows 10`, `Windows 11`, or `Windows`, render this note under any Docker snippet that involves a Linux-based image:

> Windows host: Docker Desktop must be running in Linux-container mode. If Docker Desktop is set to Windows containers, switch it via the system-tray menu → *Switch to Linux containers…*.

When the detected host architecture is ARM (M-series Macs, arm64 Linux) and the web-search step 3 reports the image does **not** ship `linux/arm64`, add `--platform linux/amd64` to the `docker run` command and include:

> ARM host: this image ships `linux/amd64` only. The `--platform linux/amd64` flag forces emulation via QEMU — expect a noticeable slowdown versus a native image.

## Registry Allowlist

Step 4 must reject any extracted image reference whose registry host is not in this list. Step 6 must re-validate against the same list before finalising the doc.

- `hub.docker.com` (Docker Official / Verified Publisher)
- `mcr.microsoft.com` (Microsoft Container Registry)
- `quay.io` (Red Hat)
- `gcr.io` (Google Container Registry)
- `ghcr.io` (GitHub Container Registry)
- `public.ecr.aws` (AWS Public Elastic Container Registry)

Bare image names with no registry host (`mongo`, `redis`, `postgres`) implicitly resolve to `hub.docker.com/_/<name>` (Docker Official Images) and are accepted.

If a legitimate vendor image lives outside this list, the user can add the registry to this file — do **not** bypass the check at run time.
