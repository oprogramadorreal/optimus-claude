# prime:permissions

Claude Code's [built-in sandboxing](https://code.claude.com/docs/en/sandboxing) provides OS-level isolation on macOS (Seatbelt) and Linux/WSL2 (bubblewrap) — but on native Windows, sandboxing is [not yet available](https://code.claude.com/docs/en/sandboxing#limitations). That leaves two options: constant permission prompts (safe but slow), or `--dangerously-skip-permissions` (fast but unsafe).

`/prime:permissions` provides a third path: **allow/deny rules** that eliminate routine prompts, plus a **PreToolUse hook** that enforces a tiered security model — writes outside the project require approval, deletes outside the project are blocked. Not OS-level isolation, but significantly safer than no guardrails at all.

## Quick Start

This skill is part of the [prime](https://github.com/oprogramadorreal/claude-code-prime) plugin. See the [main README](../../README.md) for installation instructions.

**Run:** Type `/prime:permissions` in any project directory.

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

`/prime:permissions` generates two files that work together to provide three layers of protection:

### 1. Allow List — Eliminate Routine Prompts

Auto-approves 13 built-in tools so Claude Code can work without interruption on standard operations:

`Bash`, `Read`, `Edit`, `MultiEdit`, `Write`, `NotebookEdit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Task`, `TodoWrite`, `Skill`

If your project uses [MCP servers](https://docs.anthropic.com/en/docs/claude-code/mcp) (`.mcp.json`), the skill auto-detects them and adds `mcp__<server>` entries to the allow list.

### 2. Deny List — Block Dangerous Patterns

Blocks 18 dangerous Bash patterns using Claude Code's [permission pattern matching](https://code.claude.com/docs/en/permissions), which operates on the tool invocation before execution:

| Category | Blocked Patterns |
|---|---|
| **Git destructive** | `git commit`, `git push`, `git push --force`, `git reset --hard`, `git rebase`, `git branch -D`, `git clean`, `git checkout --`, `git checkout .`, `git restore`, `git stash drop` |
| **System destructive** | `rm -rf /`, `rm -rf ~`, `sudo` |
| **Remote code execution** | `curl \| bash`, `curl \| sh`, `wget \| bash`, `wget \| sh` |

### 3. PreToolUse Hook — Tiered Path Enforcement

A [PreToolUse hook](https://code.claude.com/docs/en/hooks) that inspects every Edit, Write, MultiEdit, NotebookEdit, and Bash call at runtime:

| Operation | Inside Project | Outside Project |
|---|---|---|
| **Read / Search** | Allow (no prompt) | Allow (no prompt) |
| **Write / Edit** | Allow (no prompt) | **Ask user** permission |
| **Delete (rm/rmdir)** | Allow (no prompt) | **BLOCKED** (hard deny) |

For structured tools (Edit/Write/NotebookEdit), the hook validates the `file_path` parameter directly — this is a structured field that cannot be obfuscated, making this the most reliable enforcement layer.

For Bash `rm`/`rmdir`, the hook does best-effort command parsing. Other Bash write commands (`cp`, `mv`, `echo >`) are not intercepted.

## Enforcement Reliability

| Layer | Mechanism | Reliability | Why |
|---|---|---|---|
| **Allow list** | 13 tools auto-approved | High | Built-in [Claude Code feature](https://code.claude.com/docs/en/permissions) |
| **Deny list** | 18 Bash patterns blocked | Medium | Pattern matching can be bypassed via chaining ([#13371](https://github.com/anthropics/claude-code/issues/13371)) |
| **PreToolUse hook (Edit/Write)** | Writes outside project prompt user | **High** | Validates structured `file_path` — cannot be obfuscated |
| **PreToolUse hook (Bash rm/rmdir)** | Deletes outside project blocked | Medium | Best-effort command parsing |

This is **defense-in-depth**: multiple independent layers that each catch different classes of risk. No single layer is perfect, but together they cover the most common destructive operations.

## What Gets Generated

| File | Purpose |
|---|---|
| `.claude/settings.json` | Permission allow/deny rules + PreToolUse hook configuration |
| `.claude/hooks/restrict-paths.sh` | Path-restriction hook (tiered security logic) |

If `.claude/settings.json` already exists (e.g., from [`/prime:init`](https://github.com/oprogramadorreal/claude-code-prime)), the skill **merges** permissions into it — existing hooks, custom rules, and other configuration are preserved. Run either skill first; both share the same file safely.

## Complements /prime:init

This skill is designed as a companion to [`/prime:init`](https://github.com/oprogramadorreal/claude-code-prime), which handles documentation, formatter hooks, and code quality agents. The two skills share `.claude/settings.json`:

| Skill | Creates | Hook Type |
|---|---|---|
| `/prime:init` | PostToolUse hooks (auto-formatting after Edit/MultiEdit/Write) | PostToolUse |
| `/prime:permissions` | Permission rules + PreToolUse hook (path restriction) | PreToolUse |

Run either skill first — both merge safely into the same file.

## Skill Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition with step-by-step instructions |
| `templates/settings.json` | Base permission settings (allow/deny lists + PreToolUse hook) |
| `templates/hooks/restrict-paths.sh` | Path-restriction hook template |

## Customization

To understand or modify how the skill works, start with `SKILL.md`. Key customization points:

- **Allow list**: Edit `templates/settings.json` → `permissions.allow` to add or remove auto-approved tools
- **Deny list**: Edit `templates/settings.json` → `permissions.deny` to add more blocked patterns (e.g., `"Bash(docker *)"`) or remove overly-strict ones
- **Hook behavior**: Edit `templates/hooks/restrict-paths.sh` to change what operations are blocked, asked, or allowed
- **MCP servers**: If your project uses MCP servers (`.mcp.json`), the skill auto-detects them and adds `mcp__<server>` entries to the allow list

## Known Limitations

This skill provides **defense-in-depth**, not bulletproof isolation. Be aware of:

| Limitation | Details |
|---|---|
| **Hook bypass bug** | PreToolUse hooks may not reliably block in all cases ([#3514](https://github.com/anthropics/claude-code/issues/3514)) |
| **Pattern matching bypass** | Bash deny patterns can be bypassed via command chaining or option insertion ([#13371](https://github.com/anthropics/claude-code/issues/13371)) |
| **Bash writes not caught** | Only `rm`/`rmdir` is intercepted by the hook. Other Bash writes (`echo >`, `cp`, `mv`) are not blocked |
| **Build command escalation** | Allowing file edits + build commands enables arbitrary code execution (e.g., editing `package.json` scripts then running `npm run`) |
| **Not OS-level sandboxing** | For full isolation, use [sandboxing](https://code.claude.com/docs/en/sandboxing) or [devcontainers](https://code.claude.com/docs/en/devcontainer) |

Despite these limitations, this approach is **significantly safer** than `--dangerously-skip-permissions`:

1. **Structured tool validation is reliable** — Edit/Write `file_path` inputs cannot be obfuscated
2. **The deny list blocks the most common destructive patterns** — git push, rm -rf /, sudo, etc.
3. **Any write outside the project requires explicit user approval** — unknown operations default to asking, not allowing

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
