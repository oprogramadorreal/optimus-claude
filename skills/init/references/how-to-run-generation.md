# HOW-TO-RUN.md Generation

Generate or audit a `HOW-TO-RUN.md` at the project root that takes a developer from fresh clone to running project. Read by init's optional add-on step; the Detection Results from init's analysis agent are the primary input.

**Write scope:** this step creates or modifies `HOW-TO-RUN.md` and nothing else. Other docs (README, CONTRIBUTING, docs/) are input only — init's doc-sync step handles corrections to them.

## Grounding rules

Everything in the file must be verifiable. These rules exist because plausible-but-wrong onboarding docs are worse than none:

- **Document only verified commands.** Every command must come from something actually read: a manifest script, lock file, build config, CI workflow, Makefile/Justfile target, or launch script. Never write a command from general knowledge alone — if a stack-standard command can't be confirmed in the project, verify it with a web search or leave it out.
- **Never guess ports, versions, paths, or counts.** Ports come from config or compose files that were read; versions from manifest constraint fields (`engines.node`, `requires-python`, `rust-version`, `environment.sdk`); paths must exist on disk. When a value is unknown, omit it or point at its source ("see `launchSettings.json` for the bound port") — never substitute a framework default.
- **Verify Docker images via web search** before recommending them: confirm the image name, pick a concrete version tag (not `latest`), and confirm the ports and required environment variables from the image's official page. If unverifiable, describe the service requirement without a docker snippet.
- **Mark the unverifiable.** Content worth carrying over from existing docs that can't be confirmed against the codebase gets an explicit attribution ("per README, unverified") — or is dropped. Never present an unverified claim as fact.
- **Never copy secrets.** Describe what each environment variable is for; use placeholders for values.

## Content

Include only sections the project gives evidence for, ordered as a new developer would execute them: prerequisites (OS constraints, required tools, runtime versions), install, external services, environment setup, build, run (with what output or URL to expect), tests. Direct, imperative instructions with the detected package-manager prefix on every command.

- **Monorepo:** one file at the repo root — workspace-level install, then how to run individual subprojects and the whole system.
- **Multi-repo workspace:** one file at the workspace root — how to clone all repos, shared prerequisites and services, how to run the full system. Tell the user this file is local-only (the workspace root has no repo to version it).

## Auditing an existing HOW-TO-RUN.md

When the file already exists, audit it against current project state instead of regenerating:

- Verify each documented command, version, path, and service against the grounding rules above.
- Propose corrections only where the codebase directly contradicts the doc; preserve accurate content and anything user-added that the codebase can neither confirm nor deny.
- Show the proposed changes and get approval before writing.

## Verify

After writing, re-read the file and confirm: every command uses the detected package manager, every referenced path exists, every version matches its manifest field, and every Docker image was web-verified. Fix anything that fails before reporting.
