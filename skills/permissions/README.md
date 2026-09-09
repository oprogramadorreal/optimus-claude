# optimus:permissions

Claude Code's [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) provides OS-level isolation on macOS and Linux/WSL2 — but not on native Windows. `/optimus:permissions` installs a deterministic complement that works everywhere: **allow/deny rules** that eliminate routine prompts, plus a **PreToolUse hook** enforcing a tiered security model — writes outside the project require approval, deletes outside the project are blocked. Not OS-level isolation, but significantly safer than `--dangerously-skip-permissions`.

## Quick Start

Part of the [optimus](https://github.com/oprogramadorreal/optimus-claude) plugin — see the [main README](../../README.md) for installation. Then type `/optimus:permissions` in any project directory.

Claude Code only. In Codex, this skill stops without changing files; configure Codex's own sandbox and approval policy instead.

## Where This Fits

| Approach | Prompts | Safety | Native Windows | Autonomous loops |
|---|---|---|---|---|
| Default/manual mode | Permission-requiring actions; routine reads/searches generally do not prompt | Host permission checks | Yes | Prompts can block |
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

Installs a hook and merges settings, recording only file changes and settings additions actually made. Existing hooks/rules are preserved; extra git deny patterns are changed only after a concrete approved proposal. A modified or unrecorded hook can be merged, replaced, or kept after review.

| File | Purpose |
|---|---|
| `.claude/settings.json` | Allow/deny rules + PreToolUse hook registration |
| `.claude/hooks/restrict-paths.sh` | Path-restriction hook (tiered security logic) |
| `.claude/.optimus-managed.json` | Installed hashes, template/review refresh eligibility, and actual settings additions for safe refresh/reset; does not update init's version marker |

### Allow list

Auto-approves 14 built-in tools (`Bash`, `Read`, `Edit`, `Write`, `Agent` and its legacy alias `Task`, ...) so routine work is prompt-free. MCP servers found in `.mcp.json` are auto-added as `mcp__<server>` entries. Source of truth: [`templates/settings.json`](templates/settings.json).

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

Two out-of-project locations are exempt (writes and deletes allowed without prompts): Claude's per-project memory store (`~/.claude/projects/.../memory/`) and the session scratchpad (`<temp>/claude/<project>/<session>/scratchpad/`). Both are Claude's own low-stakes scratch space — neither is version-controlled, so a delete there is permanent (which is why `/optimus:dream` gates its deletions behind an explicit confirmation), but neither holds project files; the path matches are tightly scoped, `..`-traversal out of them is rejected, and the rest of `~/.claude` (notably `settings.json`) still prompts.

Creating a **new** file under the OS temp root but outside that scratchpad shape — an invented temp dir — still prompts you, and additionally tells *Claude* that the scratchpad exists and is the better place for scratch files. The two go to different places on purpose: for a PreToolUse `ask`, Claude Code shows `permissionDecisionReason` to **you** and passes `additionalContext` to **Claude**, so the prompt text stays a plain approval question and the reminder — the part only Claude can act on — rides `additionalContext`. (Only a `deny` sends its reason to the model, and this is never a deny: a temp path you asked for yourself, like `/tmp/report.csv`, must stay approvable.)

The hook deliberately does **not** name a scratchpad path: only the harness knows the real one, and it already gives it to Claude. A path synthesized here would point at a look-alike directory the harness never created and never cleans up. Existing files and `~/.claude` keep the plain prompt. Details in the header of [`templates/hooks/restrict-paths.sh`](templates/hooks/restrict-paths.sh).

The installed hook carries a `HOOK_VERSION`. Because `/optimus:permissions` *copies* it into your project, a plugin update never refreshes it on its own — so the plugin's SessionStart hook compares the two and suggests re-running the skill when your copy is behind.

For structured tools the hook validates the `file_path` field directly — it cannot be obfuscated, making this the most reliable layer. Bash parsing is best-effort and covers only `rm`/`rmdir`; other Bash writes (`cp`, `mv`, `echo >`) are not intercepted.

### Branch protection

History-modifying git operations (`commit`, `push`, `rebase`, `merge`, `restore`, `checkout --`, `branch -D`, ...) are allowed on feature branches but **blocked on protected branches** (default: master, main, develop, dev, development, staging, stage, prod, production, release). Creating new branches (`checkout -b`, `switch -c`) is always allowed — enabling a feature-branch + pull-request workflow. Customize the `PROTECTED_BRANCHES` array in `.claude/hooks/restrict-paths.sh`.

### Precious file protection (always on)

Well-known sensitive unversioned files are protected automatically: edits prompt, deletions are blocked. Categories: secrets (`.env*`, `credentials.*`, `local.settings.json`, ...), keys and certificates (`*.key`, `*.pem`, `*.pfx`, ...), databases (`*.sqlite`, `*.mdf`, ...), local config overrides (`docker-compose.override.yml`, ...), and IDE user settings. The `is_precious()` function in [`templates/hooks/restrict-paths.sh`](templates/hooks/restrict-paths.sh) is the single source of truth for the pattern list.

Backups and IDE scratch (`*.bak`, `*.suo`, `*.user`) are intentionally deletable: they prompt on edit but do not trigger the hook's delete block. This category is a policy choice, not proof that another copy exists. Backups of hard-precious files retain protection through backup/rotation suffixes; `.env.bak`, `id_rsa.pem.old`, `server.key.1`, `app.sqlite~`, and names also matching the hard list such as `.env.suo` stay protected. Ordinary rotated logs and merge leftovers are not added to that list.

Git-tracked files bypass this hook's precious-file gate; uncommitted edits are still not recoverable through checkout. Matching is by basename, the list is not exhaustive, and prompts may repeat. Do not stage secrets, keys, or databases merely to suppress prompts. For an intentional exception, review the specific installed-hook rule and its consequences; `/optimus:permissions` can preserve approved customizations on later updates.

## Trust Model and Assumptions

**Inside the project is trusted.** Any command not matching a deny pattern runs unprompted — including database operations (`psql -c "DROP TABLE ..."`), ordinary file deletion (`rm -rf uploads/`), network requests, and process management. The deny list is a blocklist, not an allowlist: it catches known-dangerous commands; everything else passes through.

> **Critical limitation — build command escalation:** allowing both file edits and Bash execution means any build system is arbitrary code execution (e.g., edit `package.json` to add a `preinstall` script, then run `npm install`). This is inherent to any permission model that allows both, and cannot be mitigated by deny patterns.

## Enforcement Reliability

Structured tools expose paths directly, while the hook's Bash parser covers a limited set of command shapes. [Issue #13371](https://github.com/anthropics/claude-code/issues/13371) reported chaining/option bypasses on Claude Code 2.0.34; current [permission documentation](https://code.claude.com/docs/en/permissions) describes independent checks of compound subcommands. The old report does not establish a current chaining bypass, and this plugin is still not a complete shell parser or an OS sandbox.

The hook deliberately **fails open** for some unresolved inputs, including unset `CLAUDE_PROJECT_DIR`, malformed JSON, or unavailable repository information. For OS-level isolation use [sandboxing](https://code.claude.com/docs/en/sandboxing) or [devcontainers](https://code.claude.com/docs/en/devcontainer); retain the hook as a complementary accidental-damage guard.

## Requirements

- Plugin-capable [Claude Code](https://code.claude.com/docs/en/plugins), Git, Bash 3.2 or newer (Windows: Git Bash; WSL is a separate environment). See the [supported hosts and versions](../../README.md#supported-hosts-and-versions) for tested surfaces.

## License

[MIT](../../LICENSE)
