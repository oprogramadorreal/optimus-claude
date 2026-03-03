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

`/optimus:permissions` generates two files that work together to provide three layers of protection:

### 1. Allow List — Eliminate Routine Prompts

Auto-approves 13 built-in tools so Claude Code can work without interruption on standard operations:

`Bash`, `Read`, `Edit`, `MultiEdit`, `Write`, `NotebookEdit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Task`, `TodoWrite`, `Skill`

If your project uses [MCP servers](https://docs.anthropic.com/en/docs/claude-code/mcp) (`.mcp.json`), the skill auto-detects them and adds `mcp__<server>` entries to the allow list.

### 2. Deny List — Block Dangerous Patterns

Blocks 27 dangerous Bash patterns using Claude Code's [permission pattern matching](https://code.claude.com/docs/en/permissions), which operates on the tool invocation before execution:

| Category | Blocked Patterns |
|---|---|
| **Git destructive** | `git commit`, `git push`, `git push --force`, `git reset --hard`, `git rebase`, `git branch -D`, `git clean`, `git checkout --`, `git checkout .`, `git restore`, `git stash drop` |
| **System destructive** | `rm -rf /`, `rm -rf ~`, `sudo` |
| **Remote code execution** | `curl \| bash`, `curl \| sh`, `wget \| bash`, `wget \| sh` |
| **Infrastructure destructive** | `docker system prune`, `docker compose down -v`, `kubectl delete` |
| **Package publishing** | `npm publish`, `cargo publish`, `twine upload`, `gem push`, `npx npm-cli-login` |
| **Data exfiltration (limited)** | `curl -d @file` (best-effort; trivially bypassable via alternative syntax) |

### 3. PreToolUse Hook — Tiered Path Enforcement

A [PreToolUse hook](https://code.claude.com/docs/en/hooks) that inspects every Edit, Write, MultiEdit, NotebookEdit, and Bash call at runtime:

| Operation | Inside Project | Outside Project |
|---|---|---|
| **Read / Search** | Allow (no prompt) | Allow (no prompt) |
| **Write / Edit** | Allow (no prompt) | **Ask user** permission |
| **Delete (rm/rmdir)** | Allow (no prompt) | **BLOCKED** (hard deny) |

For structured tools (Edit/Write/NotebookEdit), the hook validates the `file_path` parameter directly — this is a structured field that cannot be obfuscated, making this the most reliable enforcement layer.

For Bash `rm`/`rmdir`, the hook does best-effort command parsing. Other Bash write commands (`cp`, `mv`, `echo >`) are not intercepted.

### 4. Precious File Protection

Protects non-regenerable gitignored files from accidental modification or deletion. During setup, the skill scans for files matching common precious patterns (e.g., `appsettings.*.json`, `.env`, `*.mdf`) and configures the hook to prompt before touching them.

**How it works:** The `OPTIMUS_PRECIOUS_PATTERNS` env var holds a comma-separated list of glob patterns. When a file matches any pattern AND is not tracked by git, the hook prompts for confirmation. Unlike `OPTIMUS_PROTECT_UNVERSIONED`, this approach does not trigger on regenerable files like `node_modules/` or `dist/`.

**Multi-repo workspace support:** The hook detects the git root for each file individually by walking up the directory tree. This means precious file protection works correctly in multi-repo workspaces (where the project root has no `.git/` and each sub-repo has its own).

## Trust Model and Assumptions

This skill operates on the principle that **operations inside the project directory are trusted**. Before using it, understand what this means in practice.

### What runs WITHOUT prompts inside the project

Any Bash command that does not match the 27 deny patterns executes without asking, including:

- **Database operations** — `psql -c "DROP TABLE users"`, `redis-cli FLUSHALL`, `sqlite3 db.sqlite "DELETE FROM orders"`
- **File deletion** — `rm data.csv`, `rm -rf uploads/`, `rm database.sqlite` (only `rm -rf /` and `rm -rf ~` are in the deny list)
- **Docker operations** — `docker stop`, `docker rm` (only `docker system prune` and `docker compose down -v` are denied)
- **Network requests** — `curl`, `wget`, HTTP calls to any endpoint
- **Process management** — `kill`, `pkill`, service restarts

### Unversioned files have no safety net (by default)

Git-tracked files can be recovered with `git checkout` or `git stash`. **Unversioned files cannot.** If your project contains files not tracked by git — uploaded files, local databases, data exports, build artifacts with local state — deletion is permanent and unprompted.

To mitigate this, use **precious file protection** (recommended) or the legacy `OPTIMUS_PROTECT_UNVERSIONED=1` flag. See [Precious File Protection](#precious-file-protection) and [Unversioned File Protection](#unversioned-file-protection-opt-in-legacy) for details.

### The deny list is a blocklist, not an allowlist

The 27 blocked patterns catch common destructive operations, but **anything not on the list passes through**. The deny list is a safety net for known-dangerous commands, not a comprehensive policy. You can add project-specific patterns (e.g., `"Bash(docker *)"`) — see [Customization](#customization).

> **Critical limitation — build command escalation:** Allowing both file edits and Bash execution means any build system can be used for arbitrary code execution. Example: Claude edits `package.json` to add a `"preinstall"` script, then runs `npm install` — the script executes with full user permissions. This is inherent to any permission model that allows both edits and shell access, and cannot be mitigated by deny patterns alone.

## Enforcement Reliability

| Layer | Mechanism | Reliability | Why |
|---|---|---|---|
| **Allow list** | 13 tools auto-approved | High | Built-in [Claude Code feature](https://code.claude.com/docs/en/permissions) |
| **Deny list** | 27 Bash patterns blocked | Medium | Pattern matching can be bypassed via chaining ([#13371](https://github.com/anthropics/claude-code/issues/13371)) |
| **PreToolUse hook (Edit/Write)** | Writes outside project prompt user | **High** | Validates structured `file_path` — cannot be obfuscated |
| **PreToolUse hook (Bash rm/rmdir)** | Deletes outside project blocked | Medium | Best-effort command parsing |

This is **defense-in-depth**: multiple independent layers that each catch different classes of risk. No single layer is perfect, but together they cover the most common destructive operations.

### Hook Fail-Open Behavior

The path-restriction hook is designed to **fail open** (allow the operation) when it cannot determine safety:

| Condition | Behavior | Why |
|---|---|---|
| `CLAUDE_PROJECT_DIR` not set | Allow | Cannot determine project root; blocking would break all operations |
| JSON input parsing fails | Allow | Malformed input should not block legitimate tool use |
| `file_path` extraction fails | Allow | Some tool invocations may have unexpected structure |
| No git root found for file | Allow | `git ls-files` unavailable; assumes tracked |

This is a deliberate design choice: a fail-closed hook would block legitimate operations whenever Claude Code changes its JSON format.

## What Gets Generated

| File | Purpose |
|---|---|
| `.claude/settings.json` | Permission allow/deny rules + PreToolUse hook configuration |
| `.claude/hooks/restrict-paths.sh` | Path-restriction hook (tiered security logic) |

If `.claude/settings.json` already exists (e.g., from [`/optimus:init`](https://github.com/oprogramadorreal/optimus-claude)), the skill **merges** permissions into it — existing hooks, custom rules, and other configuration are preserved. Run either skill first; both share the same file safely.

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

## Precious File Protection

During setup, the skill scans for non-regenerable gitignored files and configures targeted protection via the `OPTIMUS_PRECIOUS_PATTERNS` env var. Default patterns:

```
appsettings.*.json, .env, .env.*, *.mdf, *.ldf, *.sqlite, *.db, *.pfx, *.key, *.pem, credentials.*, secrets.*
```

When a file matches any pattern AND is not tracked by git, the hook prompts for confirmation before modifying or deleting it. New file creation is not affected.

| Operation | Matches precious pattern? | Git-tracked? | Behavior |
|---|---|---|---|
| Edit/Write existing file | Yes | No | **Ask** (changes permanent) |
| Edit/Write existing file | Yes | Yes | Allow (recoverable via git) |
| Edit/Write existing file | No | Any | Allow |
| rm/rmdir | Yes | No | **Ask** (deletion permanent) |
| rm/rmdir | No | Any | Allow |

### Multi-repo workspace support

The hook detects the git root for each file individually by walking up the directory tree, rather than assuming a single `.git/` at the project root. This is essential for multi-repo workspaces where each sub-repo has its own `.git/`:

```
workspace/              ← project root (no .git/)
├── backend/            ← sub-repo (.git/)
│   └── appsettings.development.json  ← precious, protected
├── frontend/           ← sub-repo (.git/)
│   └── .env            ← precious, protected
└── .claude/settings.json
```

### Customizing patterns

Edit the `OPTIMUS_PRECIOUS_PATTERNS` value in `.claude/settings.json` to add or remove patterns:

```json
"command": "OPTIMUS_PRECIOUS_PATTERNS=\"appsettings.*.json,.env,.env.*,*.sqlite\" bash ..."
```

Patterns match against the file's basename using bash glob syntax.

## Unversioned File Protection (opt-in, legacy)

> **Precious file protection is recommended instead.** It targets only non-regenerable files, avoiding false positives on `node_modules/`, `dist/`, etc.

Set `OPTIMUS_PROTECT_UNVERSIONED=1` before starting Claude Code to prompt before modifying or deleting ANY unversioned file:

```bash
OPTIMUS_PROTECT_UNVERSIONED=1 claude
```

Both precious patterns and unversioned protection can be used together — precious patterns are checked first.

### Known limitations of this feature

- **False positives on regenerable files** — `node_modules/`, `dist/`, `build/` are unversioned but easily recreated. The hook cannot distinguish "gitignored because regenerable" from "gitignored because sensitive." This is why precious patterns is preferred.
- **Prompts on every edit** — Hooks fire on every tool call with no caching. Editing `.env` five times produces five prompts. Consider running `git add` on frequently-edited unversioned files to suppress prompts.
- **Fails open** — If no git root is found for a file, the check is skipped and the operation is allowed.

## Customization

To understand or modify how the skill works, start with `SKILL.md`. Key customization points:

- **Allow list**: Edit `templates/settings.json` → `permissions.allow` to add or remove auto-approved tools
- **Deny list**: Edit `templates/settings.json` → `permissions.deny` to add more blocked patterns (e.g., `"Bash(docker *)"`) or remove overly-strict ones
- **Hook behavior**: Edit `templates/hooks/restrict-paths.sh` to change what operations are blocked, asked, or allowed
- **MCP servers**: If your project uses MCP servers (`.mcp.json`), the skill auto-detects them and adds `mcp__<server>` entries to the allow list
- **Precious file patterns**: Edit `OPTIMUS_PRECIOUS_PATTERNS` in the hook command to customize which gitignored files are protected. See [Precious File Protection](#precious-file-protection)
- **Legacy unversioned protection**: Set `OPTIMUS_PROTECT_UNVERSIONED=1` to prompt before modifying ALL unversioned files. See [Unversioned File Protection](#unversioned-file-protection-opt-in-legacy)

## Known Limitations

This skill provides **defense-in-depth**, not bulletproof isolation. Be aware of:

| Limitation | Details |
|---|---|
| **Inside project = fully trusted** | All operations inside the project run without prompts unless they match a deny pattern. See [Trust Model and Assumptions](#trust-model-and-assumptions) for what this means in practice |
| **Pattern matching bypass** | Bash deny patterns can be bypassed via command chaining or option insertion ([#13371](https://github.com/anthropics/claude-code/issues/13371)) |
| **Bash writes not caught** | Only `rm`/`rmdir` is intercepted by the hook. Other Bash writes (`echo >`, `cp`, `mv`) outside the project are not blocked |
| **Build command escalation** | File edits + build commands = arbitrary code execution. See the [critical limitation callout](#trust-model-and-assumptions) above |
| **Data exfiltration** | Network commands like `curl -X POST` can upload data to external servers. The deny list blocks `curl -d @file` but this is trivially bypassable |
| **Deny list is a blocklist** | Only 27 specific patterns are blocked. Database commands, service management, and many other destructive operations are not covered |
| **Not OS-level sandboxing** | For full isolation, use [sandboxing](https://code.claude.com/docs/en/sandboxing) or [devcontainers](https://code.claude.com/docs/en/devcontainer) |

Despite these limitations, this approach is **significantly safer** than `--dangerously-skip-permissions`:

1. **Structured tool validation is reliable** — Edit/Write `file_path` inputs cannot be obfuscated
2. **The deny list blocks the most common destructive patterns** — git push, rm -rf /, sudo, npm publish, etc.
3. **Any write outside the project requires explicit user approval** — unknown operations default to asking, not allowing
4. **Precious file protection is built-in** — non-regenerable gitignored files (config, secrets, databases) are protected by default
5. **Multi-repo workspace support** — git root detection per-file, not per-project

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
