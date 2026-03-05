# optimus:permissions

Claude Code's [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) provides OS-level isolation on macOS (Seatbelt) and Linux/WSL2 (bubblewrap) — but on native Windows, sandboxing is [not yet available](https://code.claude.com/docs/en/sandboxing#limitations). That leaves two options: constant permission prompts (safe but slow), or `--dangerously-skip-permissions` (fast but unsafe).

`/optimus:permissions` provides a third path: **allow/deny rules** that eliminate routine prompts, plus a **PreToolUse hook** that enforces a tiered security model — writes outside the project require approval, deletes outside the project are blocked. Not OS-level isolation, but significantly safer than no guardrails at all.

## Quick Start

This skill is part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Type `/optimus:permissions` in any project directory.

## Where This Fits

Claude Code has multiple layers for managing agent autonomy. The right choice depends on your platform and risk tolerance:

| Approach | Prompts | Safety | macOS | Linux / WSL2 | Native Windows | Setup | Autonomous Loops |
|---|---|---|---|---|---|---|---|
| **Default mode** | Every tool call | Safe | Yes | Yes | Yes | None | No (blocks) |
| **`--dangerously-skip-permissions`** | None | **Unsafe** — no guardrails | Yes | Yes | Yes | None | Yes (no guardrails) |
| **[Built-in sandboxing](https://code.claude.com/docs/en/sandboxing)** | None (sandboxed) | **OS-level isolation** | Yes | Yes | **[Planned](https://code.claude.com/docs/en/sandboxing#limitations)** | Minimal | Yes |
| **[Devcontainers](https://code.claude.com/docs/en/devcontainer)** | None (sandboxed) | **Container-level isolation** | Yes | Yes | Yes | Moderate | Yes |
| **This skill** | Minimal | **Defense-in-depth** — tiered rules + hook | Yes | Yes | Yes | Minimal | **No** (prompts block) |

**Gold standard:** [Built-in sandboxing](https://code.claude.com/docs/en/sandboxing) or [devcontainers](https://code.claude.com/docs/en/devcontainer) provide true isolation. Use them when you can.

**Where this skill shines:**

- **Native Windows** — where sandboxing is not yet available and devcontainers add complexity
- **Lightweight setups** — when you want fewer prompts without the overhead of containers
- **Complementary layer** — even with sandboxing or devcontainers, permission rules reduce noise from non-destructive operations

> **Recommended for Windows users:** For full isolation, run Claude Code inside [WSL2](https://code.claude.com/docs/en/sandboxing) (which supports bubblewrap sandboxing) or a [devcontainer](https://code.claude.com/docs/en/devcontainer). This skill is for when those options are not practical.

> **Not for unattended autonomous loops:** This skill is **not suitable** for [ralph-wiggum](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum)-style autonomous loops (where Claude runs unattended in a `while true` loop). Permission prompts ("ask user") would block the loop, and without OS-level isolation an unattended agent could cause damage. For autonomous loops, use [devcontainers](https://code.claude.com/docs/en/devcontainer) or [built-in sandboxing](https://code.claude.com/docs/en/sandboxing).

## What It Does

`/optimus:permissions` generates two files that work together to provide four layers of protection:

### 1. Allow List — Eliminate Routine Prompts

Auto-approves 13 built-in tools so Claude Code can work without interruption on standard operations:

`Bash`, `Read`, `Edit`, `MultiEdit`, `Write`, `NotebookEdit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Task`, `TodoWrite`, `Skill`

If your project uses [MCP servers](https://docs.anthropic.com/en/docs/claude-code/mcp) (`.mcp.json`), the skill auto-detects them and adds `mcp__<server>` entries to the allow list.

### 2. Deny List — Block Dangerous Patterns

Blocks 30 dangerous Bash patterns using Claude Code's [permission pattern matching](https://code.claude.com/docs/en/permissions), which operates on the tool invocation before execution:

| Category | Blocked Patterns |
|---|---|
| **Git (always blocked)** | `git push --all`, `git push --mirror`, `git clean`, `git stash drop`, `*git push --force*`, `*git push -f *`, `*git push -f`, `*git reset --hard*` |
| **System destructive** | `rm -rf /`, `rm -rf ~`, `sudo` |
| **Remote code execution** | `curl \| bash`, `curl \| sh`, `wget \| bash`, `wget \| sh` |
| **Infrastructure destructive** | `docker system prune`, `docker compose down -v`, `kubectl delete` |
| **Package publishing** | `npm publish`, `cargo publish`, `twine upload`, `gem push`, `dotnet nuget push`, `mvn deploy`, `mvnw deploy`, `./mvnw deploy`, `gradle publish`, `./gradlew publish`, `npx npm-cli-login` |
| **Data exfiltration (limited)** | `curl -d @file` (best-effort; trivially bypassable via alternative syntax) |

### 3. PreToolUse Hook — Tiered Path Enforcement

A [PreToolUse hook](https://code.claude.com/docs/en/hooks) that inspects every Edit, Write, MultiEdit, NotebookEdit, and Bash call at runtime:

| Operation | Inside Project | Outside Project |
|---|---|---|
| **Read / Search** | Allow (no prompt) | Allow (no prompt) |
| **Write / Edit** | Allow (no prompt) | **Ask user** permission |
| **Write / Edit precious unversioned file** | **Ask user** permission | **Ask user** permission |
| **Delete (rm/rmdir)** | Allow (no prompt) | **BLOCKED** (hard deny) |
| **Delete precious unversioned file** | **BLOCKED** (hard deny) | **BLOCKED** (hard deny) |

For structured tools (Edit/Write/NotebookEdit), the hook validates the `file_path` parameter directly — this is a structured field that cannot be obfuscated, making this the most reliable enforcement layer.

For Bash `rm`/`rmdir`, the hook does best-effort command parsing. Other Bash write commands (`cp`, `mv`, `echo >`) are not intercepted.

### 4. Branch Protection — Git Operations on Protected Branches

The hook enforces branch-aware git protection: operations that modify branch history are **allowed on feature branches** but **blocked on protected branches** (master, main, develop, dev, development, staging, stage, prod, production, release).

| Git Operation | Feature Branch | Protected Branch |
|---|---|---|
| `git commit` | Allow | **BLOCKED** |
| `git push` | Allow | **BLOCKED** |
| `git push --force` | **BLOCKED** (deny list) | **BLOCKED** (deny list + hook) |
| `git reset --hard` | **BLOCKED** (deny list) | **BLOCKED** (deny list + hook) |
| `git rebase` | Allow | **BLOCKED** |
| `git merge` | Allow | **BLOCKED** |
| `git checkout --` / `git checkout .` | Allow | **BLOCKED** |
| `git restore` | Allow | **BLOCKED** |
| `git branch -D <branch>` | Allow (non-protected) | **BLOCKED** (protected name) |
| `git checkout -b` / `git switch -c` | Allow | Allow (creates new branch) |
| `git checkout -B` / `git switch -C` | Allow (non-protected) | **BLOCKED** (protected name) |
| `git push --all` / `git push --mirror` | **BLOCKED** | **BLOCKED** |

This enables a feature-branch workflow: Claude Code creates branches, commits, and pushes freely — but cannot modify protected branches directly. Use pull requests for code review before merging.

**Customization:** Edit the `PROTECTED_BRANCHES` array in `.claude/hooks/restrict-paths.sh` to add or remove protected branch names.

## Trust Model and Assumptions

This skill operates on the principle that **operations inside the project directory are trusted**. Before using it, understand what this means in practice.

### What runs WITHOUT prompts inside the project

Any Bash command that does not match the 30 deny patterns executes without asking, including:

- **Database operations** — `psql -c "DROP TABLE users"`, `redis-cli FLUSHALL`, `sqlite3 db.sqlite "DELETE FROM orders"`
- **File deletion** — `rm data.csv`, `rm -rf uploads/`, `rm database.sqlite` (only `rm -rf /` and `rm -rf ~` are in the deny list)
- **Docker operations** — `docker stop`, `docker rm` (only `docker system prune` and `docker compose down -v` are denied)
- **Network requests** — `curl`, `wget`, HTTP calls to any endpoint
- **Process management** — `kill`, `pkill`, service restarts

### Precious unversioned files are protected automatically

Well-known sensitive files (`.env`, `*.key`, `*.sqlite`, etc.) that are not tracked by git are automatically protected: edits prompt for approval, deletions are blocked. See [Precious File Protection](#precious-file-protection-always-on) for the full list.

Other unversioned files (build output, `node_modules/`, data exports) are **not** protected — deletion is permanent and unprompted. If your project has non-standard sensitive files, add patterns to the `is_precious()` function in the hook script or re-run `/optimus:permissions` to scan for project-specific files.

### The deny list is a blocklist, not an allowlist

The 30 blocked patterns catch common destructive operations, but **anything not on the list passes through**. The deny list is a safety net for known-dangerous commands, not a comprehensive policy. Branch-specific git commands (commit, push, rebase, etc.) are enforced by the hook's branch protection layer instead — see [Branch Protection](#4-branch-protection--git-operations-on-protected-branches). You can add project-specific patterns (e.g., `"Bash(docker *)"`) — see [Customization](#customization).

> **Critical limitation — build command escalation:** Allowing both file edits and Bash execution means any build system can be used for arbitrary code execution. Example: Claude edits `package.json` to add a `"preinstall"` script, then runs `npm install` — the script executes with full user permissions. This is inherent to any permission model that allows both edits and shell access, and cannot be mitigated by deny patterns alone.

## Enforcement Reliability

| Layer | Mechanism | Reliability | Why |
|---|---|---|---|
| **Allow list** | 13 tools auto-approved | High | Built-in [Claude Code feature](https://code.claude.com/docs/en/permissions) |
| **Deny list** | 30 Bash patterns blocked | Medium | Pattern matching can be bypassed via chaining ([#13371](https://github.com/anthropics/claude-code/issues/13371)) |
| **Branch protection (hook)** | Git ops blocked on protected branches | Medium | Best-effort command parsing; `git checkout -b` always allowed |
| **PreToolUse hook (Edit/Write)** | Writes outside project prompt user | **High** | Validates structured `file_path` — cannot be obfuscated |
| **PreToolUse hook (Bash rm/rmdir)** | Deletes outside project blocked | Medium | Best-effort command parsing |

This is **defense-in-depth**: multiple independent layers that each catch different classes of risk. No single layer is perfect, but together they cover the most common destructive operations. The branch protection layer enables a feature-branch workflow — Claude Code can commit, push, and work freely on feature branches while protected branches require pull requests.

### Hook Fail-Open Behavior

The path-restriction hook is designed to **fail open** (allow the operation) when it cannot determine safety:

| Condition | Behavior | Why |
|---|---|---|
| `CLAUDE_PROJECT_DIR` not set | Allow | Cannot determine project root; blocking would break all operations |
| JSON input parsing fails | Allow | Malformed input should not block legitimate tool use |
| `file_path` extraction fails | Allow | Some tool invocations may have unexpected structure |
| Not a git repo (precious file protection) | Allow | `git ls-files` unavailable; assumes tracked |

This is a deliberate design choice: a fail-closed hook would block legitimate operations whenever Claude Code changes its JSON format.

## What Gets Generated

| File | Purpose |
|---|---|
| `.claude/settings.json` | Permission allow/deny rules + PreToolUse hook configuration |
| `.claude/hooks/restrict-paths.sh` | Path-restriction hook (tiered security logic) |

If `.claude/settings.json` already exists (e.g., from [`/optimus:init`](https://github.com/oprogramadorreal/optimus-claude)), the skill **merges** permissions into it — existing hooks, custom rules, and other configuration are preserved. The hook script (`.claude/hooks/restrict-paths.sh`) is always replaced with the latest template version. Run either skill first; both share the same file safely.

## Complements /optimus:init

This skill is designed as a companion to [`/optimus:init`](https://github.com/oprogramadorreal/optimus-claude), which handles documentation, formatter hooks, and code quality agents. The two skills share `.claude/settings.json`:

| Skill | Creates | Hook Type |
|---|---|---|
| `/optimus:init` | PostToolUse hooks (auto-formatting after Edit/MultiEdit/Write) | PostToolUse |
| `/optimus:permissions` | Permission rules + PreToolUse hook (path restriction) | PreToolUse |

Run either skill first — both merge safely into the same file.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step instructions |
| `templates/settings.json` | Base permission settings (allow/deny lists + PreToolUse hook) |
| `templates/hooks/restrict-paths.sh` | Path-restriction hook template |

## Precious File Protection (always-on)

The hook automatically protects well-known sensitive and irreplaceable files that are not tracked by git. No configuration needed.

### Protected patterns

| Pattern | Category |
|---------|----------|
| `.env`, `.env.*` | Secrets |
| `appsettings.*.json` (not `appsettings.json`) | Secrets |
| `local.settings.json` | Secrets |
| `credentials.*`, `secrets.*` | Secrets |
| `docker-compose.override.yml` | Local Docker config |
| `*.key`, `*.pem`, `*.pfx`, `*.p12`, `*.cert`, `*.crt`, `*.jks` | Certificates / Keys |
| `*.sqlite`, `*.sqlite3`, `*.db` | Database files |
| `*.db-shm`, `*.db-wal`, `*.db-journal` | SQLite companion files (WAL/journal) |
| `*.mdf`, `*.ldf`, `*.ndf` | Database files (SQL Server) |
| `*.bak`, `*.dump`, `*.sql.gz` | Database backups |
| `*.suo`, `*.user` | IDE user settings |

### Behavior

| Operation | Git-tracked? | Precious? | Behavior |
|-----------|-------------|-----------|----------|
| Edit/Write | Yes | Any | Allow (recoverable via git) |
| Edit/Write | No | Yes | **Ask** (changes may be permanent) |
| Edit/Write | No | No | Allow |
| rm/rmdir | Yes | Any | Allow (recoverable via git) |
| rm/rmdir | No | Yes | **BLOCKED** (deletion denied) |
| rm/rmdir | No | No | Allow |

### Why always-on?

Unlike the previous `OPTIMUS_PROTECT_UNVERSIONED` approach, precious file protection targets only files that are known to be sensitive or irreplaceable. This avoids false positives on regenerable files like `node_modules/` or `dist/` — only well-known precious patterns trigger protection.

### Extending with custom patterns

Re-run `/optimus:permissions` to scan for project-specific precious files. The skill will detect unversioned files that look sensitive and offer to add custom patterns to `is_precious()` in `.claude/hooks/restrict-paths.sh`. You can also edit the function directly.

**Note:** Re-running the skill replaces the hook with the latest template version. If you've added custom patterns to `is_precious()`, they will be overwritten. For persistent customizations, edit the template in the plugin source or re-add patterns after updating.

### Limitations

- **Basename matching only** — the hook matches the file's name, not its path. A file named `secrets.txt` in any directory will be protected.
- **Not exhaustive** — the list covers common patterns but cannot anticipate every project's sensitive files.
- **Prompts on every edit** — Hooks fire on every tool call with no caching. Editing `.env` five times produces five prompts. Consider running `git add` on frequently-edited unversioned files to suppress prompts.
- **Fails open** — If the project is not a git repository or `git` is unavailable, the check is skipped and all operations are allowed.

## Customization

To understand or modify how the skill works, start with `SKILL.md`. Key customization points:

- **Allow list**: Edit `templates/settings.json` → `permissions.allow` to add or remove auto-approved tools
- **Deny list**: Edit `templates/settings.json` → `permissions.deny` to add more blocked patterns (e.g., `"Bash(docker *)"`) or remove overly-strict ones
- **Protected branches**: Edit the `PROTECTED_BRANCHES` array in `templates/hooks/restrict-paths.sh` to add or remove protected branch names (default: master, main, develop, dev, development, staging, stage, prod, production, release)
- **Hook behavior**: Edit `templates/hooks/restrict-paths.sh` to change what operations are blocked, asked, or allowed
- **MCP servers**: If your project uses MCP servers (`.mcp.json`), the skill auto-detects them and adds `mcp__<server>` entries to the allow list
- **Precious patterns**: Edit `is_precious()` in `templates/hooks/restrict-paths.sh` to add or remove protected file patterns, or re-run `/optimus:permissions` to scan for project-specific files

## Known Limitations

This skill provides **defense-in-depth**, not bulletproof isolation. Be aware of:

| Limitation | Details |
|---|---|
| **Inside project = fully trusted** | All operations inside the project run without prompts unless they match a deny pattern. See [Trust Model and Assumptions](#trust-model-and-assumptions) for what this means in practice |
| **Pattern matching bypass** | Bash deny patterns can be bypassed via command chaining or option insertion ([#13371](https://github.com/anthropics/claude-code/issues/13371)) |
| **Bash writes not caught** | Only `rm`/`rmdir` is intercepted by the hook. Other Bash writes (`echo >`, `cp`, `mv`) outside the project are not blocked |
| **Build command escalation** | File edits + build commands = arbitrary code execution. See the [critical limitation callout](#trust-model-and-assumptions) above |
| **Data exfiltration** | Network commands like `curl -X POST` can upload data to external servers. The deny list blocks `curl -d @file` but this is trivially bypassable |
| **Deny list is a blocklist** | Only 30 specific patterns are blocked. Database commands, service management, and many other destructive operations are not covered |
| **Not OS-level sandboxing** | For full isolation, use [sandboxing](https://code.claude.com/docs/en/sandboxing) or [devcontainers](https://code.claude.com/docs/en/devcontainer) |

Despite these limitations, this approach is **significantly safer** than `--dangerously-skip-permissions`:

1. **Structured tool validation is reliable** — Edit/Write `file_path` inputs cannot be obfuscated
2. **The deny list and branch protection block the most common destructive patterns** — rm -rf /, sudo, npm publish, plus git operations on protected branches
3. **Any write outside the project requires explicit user approval** — unknown operations default to asking, not allowing
4. **Precious files are always protected** — well-known sensitive files (.env, *.key, *.sqlite, etc.) are automatically guarded when not tracked by git

## References

Official documentation and resources that informed this skill's design:

- **Anthropic** — [Claude Code Permissions](https://code.claude.com/docs/en/permissions): allow/deny rules, permission patterns, settings.json format
- **Anthropic** — [Claude Code Hooks](https://code.claude.com/docs/en/hooks): PreToolUse/PostToolUse hook system, matchers, JSON protocol
- **Anthropic** — [Hooks Guide](https://code.claude.com/docs/en/hooks-guide): practical examples of hook implementations
- **Anthropic** — [Sandboxing](https://code.claude.com/docs/en/sandboxing): OS-level isolation via Seatbelt (macOS) and bubblewrap (Linux/WSL2), platform support matrix
- **Anthropic** — [Claude Code Sandboxing (Engineering Blog)](https://www.anthropic.com/engineering/claude-code-sandboxing): design philosophy behind sandboxing
- **Anthropic** — [Development Containers](https://code.claude.com/docs/en/devcontainer): container-based isolation that works on all platforms
- **Anthropic** — [Best Practices](https://code.claude.com/docs/en/best-practices): recommended patterns for Claude Code usage
- **Anthropic** — [Reference Devcontainer](https://github.com/anthropics/claude-code/tree/main/.devcontainer): official devcontainer configuration
- **Anthropic** — [Ralph Wiggum Plugin](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum): autonomous loop plugin (requires true isolation, not this skill)
- **Trail of Bits** — [Claude Code Devcontainer](https://github.com/trailofbits/claude-code-devcontainer): security-hardened devcontainer for audits and untrusted code review

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support)
- Git
- Bash (available by default on macOS/Linux; on Windows via Git Bash or WSL)

## License

[MIT](../../LICENSE)
