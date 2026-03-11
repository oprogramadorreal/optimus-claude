# Unsupported Stack Fallback

Shared procedure for handling tech stacks not in the built-in supported list. Each consuming skill applies its own policy after the common steps.

## Common Procedure

When a project's stack doesn't match any built-in row:

1. **Notify** — inform the user that the stack is not officially supported and the skill will proceed with best effort
2. **Research** — use web search to find the standard tooling for the detected language/stack. If search fails, is unavailable, or returns no results, skip to step 5
3. **Validate** — proposed commands must invoke a single well-known CLI tool with simple arguments (no shell operators, pipes, redirects, variable expansion, subshells, chained commands, or interpreter invocations). The tool name must be a bare command name with no path separators (`/`, `\`) — only tools resolvable via PATH. The command must be a single line of printable ASCII
4. **Approve** — present findings and exact commands to the user for approval before executing. If the user declines, treat it the same as a graceful skip — inform the user and skip the fallback step
5. **Graceful skip** — if reached (web search failed, no results, or user declined), inform the user and skip the fallback step. Do not block the rest of the skill

