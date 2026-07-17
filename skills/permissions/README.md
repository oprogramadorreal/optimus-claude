# optimus:permissions

Claude Code's [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) provides OS-level isolation on macOS and Linux/WSL2 — but not on native Windows. `/optimus:permissions` installs a deterministic complement that works everywhere: **allow/deny rules** that eliminate routine prompts, plus a **PreToolUse hook** enforcing a tiered security model — writes outside the project require approval, deletes outside the project are blocked. Not OS-level isolation, but significantly safer than `--dangerously-skip-permissions`.

## Quick Start

Part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin — see the [main README](../../README.md) for installation. Then type `/optimus:permissions` in any project directory.

## Where This Fits

| Approach | Prompts | Safety | Native Windows | Autonomous loops |
|---|---|---|---|---|
| Default mode | Every tool call | Safe | Yes | No (blocks) |
| `--dangerously-skip-permissions` | None | **Unsafe** — no guardrails | Yes | Yes, no guardrails |
| [Auto mode](https://code.claude.com/docs/en/auto-mode-config) | Minimal | Classifier-based — probabilistic research preview, model/provider/admin-gated | Yes | Partial |
| [Built-in sandboxing](https://code.claude.com/docs/en/sandboxing) | None | OS-level isolation | [Planned](https://code.claude.com/docs/en/sandboxing#limitations) | Yes |
| [Devcontainers](https://code.claude.com/docs/en/devcontainer) | None | Container isolation | Yes | Yes |
| **This skill** | Minimal | Defense-in-depth | Yes | **No** (prompts block) |

Use sandboxing or devcontainers when you can — they are the gold standard (on Windows, WSL2 or a devcontainer gets you there). This skill shines on native Windows, in lightweight setups, and as a complementary layer under any of the above. It is **not** suitable for unattended autonomous loops: "ask user" prompts block them, and without OS isolation an unattended agent could cause damage.

## Relationship with auto mode

[Auto mode](https://code.claude.com/docs/en/auto-mode-config)'s server-side classifier and this skill are complementary layers, not alternatives:

- **Deny rules run first.** `permissions.deny` is evaluated before the classifier and works on every model and provider, so the deny list stays the hardest boundary even in auto mode.
- **Hooks run in every permission mode.** Branch and precious-file protection keep working under auto mode — and the hook is deterministic where the classifier is probabilistic.
- **The allow list matters most outside auto mode.** On entering auto mode, Claude Code drops broad execution-granting allow rules (the template's `Bash` and `Task` entries) and lets the classifier govern those calls, restoring the rules when you leave.

This skill does not enable or configure auto mode; an `autoMode` block is ignored in the checked-in `.claude/settings.json` it manages. Enable auto mode with `Shift+Tab`, `claude --permission-mode auto`, or your user settings.

## Interaction with Claude Code's native protected paths

Independently of this skill, Claude Code [protects a fixed set of paths](https://code.claude.com/docs/en/permission-modes#protected-paths) — the in-project `.claude/` directory, `.git/`, `.mcp.json`, and similar config files — prompting on writes in every mode except `bypassPermissions`; allow rules and hooks cannot suppress it. That prompt comes from Claude Code, not from `restrict-paths.sh`, and it covers exactly the surface this skill's hook deliberately trusts (in-project writes, including the settings file that registers the hook itself), so the agent cannot silently rewrite its own permissions.

## What It Does

Generates two files. If `.claude/settings.json` already exists (e.g., from `/optimus:init`), the skill merges into it and preserves existing hooks and rules — the one exception is extra git deny patterns, which the skill asks before replacing. The hook script is always replaced with the latest template; local edits are detected and offered for re-apply.

| File | Purpose |
|---|---|
| `.claude/settings.json` | Allow/deny rules + PreToolUse hook registration |
| `.claude/hooks/restrict-paths.sh` | Path-restriction hook (tiered security logic) |

### Allow list

Auto-approves 13 built-in tools (`Bash`, `Read`, `Edit`, `Write`, `Task`, ...) so routine work is prompt-free. MCP servers found in `.mcp.json` are auto-added as `mcp__<server>` entries. Source of truth: [`templates/settings.json`](templates/settings.json).

### Deny list

Blocks 30 dangerous Bash patterns across six categories: git history rewriting (`push --force`, `reset --hard`, `clean`, ...), system destruction (`rm -rf /`, `sudo`), piped remote code execution (`curl | bash`, ...), infrastructure destruction (`docker system prune`, `kubectl delete`, ...), package publishing (`npm publish`, `twine upload`, ...), and best-effort data exfiltration (`curl -d @file` — trivially bypassable). The exact pattern list lives in [`templates/settings.json`](templates/settings.json) — that file, not this README, is the source of truth.

### PreToolUse Hook

`restrict-paths.sh` inspects every Edit, Write, MultiEdit, NotebookEdit, and Bash call:

| Operation | Inside project | Outside project |
|---|---|---|
| Read / Search | Allow | Allow |
| Write / Edit | Allow | **Ask** |
| Write / Edit precious unversioned file | **Ask** | **Ask** |
| Delete (`rm`/`rmdir`) | Allow | **BLOCKED** |
| Delete precious unversioned file | **BLOCKED** | **BLOCKED** |

Two out-of-project locations are exempt (writes and deletes allowed without prompts): Claude's per-project memory store (`~/.claude/projects/.../memory/`) and the session scratchpad (`<temp>/claude/<project>/<session>/scratchpad/`). Both are Claude's own recoverable scratch space; the path matches are tightly scoped, `..`-traversal out of them is rejected, and the rest of `~/.claude` (notably `settings.json`) still prompts. Details in the header of [`templates/hooks/restrict-paths.sh`](templates/hooks/restrict-paths.sh).

For structured tools the hook validates the `file_path` field directly — it cannot be obfuscated, making this the most reliable layer. Bash parsing is best-effort and covers only `rm`/`rmdir`; other Bash writes (`cp`, `mv`, `echo >`) are not intercepted.

### Branch protection

History-modifying git operations (`commit`, `push`, `rebase`, `merge`, `restore`, `checkout --`, `branch -D`, ...) are allowed on feature branches but **blocked on protected branches** (default: master, main, develop, dev, development, staging, stage, prod, production, release). Creating new branches (`checkout -b`, `switch -c`) is always allowed — enabling a feature-branch + pull-request workflow. Customize the `PROTECTED_BRANCHES` array in `.claude/hooks/restrict-paths.sh`.

### Precious file protection (always on)

Well-known sensitive unversioned files are protected automatically: edits prompt, deletions are blocked. Categories: secrets (`.env*`, `credentials.*`, `local.settings.json`, ...), keys and certificates (`*.key`, `*.pem`, `*.pfx`, ...), databases and backups (`*.sqlite`, `*.mdf`, `*.bak`, ...), local config overrides (`docker-compose.override.yml`, ...), and IDE user settings. The `is_precious()` function in [`templates/hooks/restrict-paths.sh`](templates/hooks/restrict-paths.sh) is the single source of truth for the pattern list. Git-tracked files are never gated (recoverable via git). Matching is by basename only, the list is not exhaustive, and prompts repeat on every edit — `git add` a frequently-edited unversioned file to silence them. Re-run `/optimus:permissions` to scan for project-specific files and add custom patterns (persistent customizations belong in the plugin-source template).

## Trust Model and Assumptions

**Inside the project is trusted.** Any command not matching a deny pattern runs unprompted — including database operations (`psql -c "DROP TABLE ..."`), ordinary file deletion (`rm -rf uploads/`), network requests, and process management. The deny list is a blocklist, not an allowlist: it catches known-dangerous commands; everything else passes through.

> **Critical limitation — build command escalation:** allowing both file edits and Bash execution means any build system is arbitrary code execution (e.g., edit `package.json` to add a `preinstall` script, then run `npm install`). This is inherent to any permission model that allows both, and cannot be mitigated by deny patterns.

## Enforcement Reliability

Structured-tool path validation is high-reliability; Bash deny patterns and the hook's command parsing are medium — bypassable via chaining or option insertion ([#13371](https://github.com/anthropics/claude-code/issues/13371)). The hook deliberately **fails open** when it cannot determine safety (unset `CLAUDE_PROJECT_DIR`, malformed JSON input, no git repo at the file's location) — a fail-closed hook would break legitimate operations whenever the tool-input format shifts. This is defense-in-depth: independent layers each catching different classes of risk, together far safer than no guardrails — but not OS-level sandboxing. For true isolation use [sandboxing](https://code.claude.com/docs/en/sandboxing) or [devcontainers](https://code.claude.com/docs/en/devcontainer).

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+ (plugin support), Git, Bash (macOS/Linux native; Windows via Git Bash or WSL)

## License

[MIT](../../LICENSE)
