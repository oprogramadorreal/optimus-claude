# Shared Constraints

Constraints that apply to both dev-setup agents. These agents analyze the project to detect context and audit existing development instructions.

## Agent Constraints (All Agents)

- **Read-only analysis.** Do NOT modify any files, create any files, or run any commands that change state. You are analyzing the project, not changing it.
- **Your results will be independently validated.** The main context verifies your output against the actual project before presenting it to the user for confirmation. Speculation or low-confidence guesses will be caught and discarded. Only report what you are confident about.
