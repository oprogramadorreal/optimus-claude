# Guided Walkthrough

Loaded by `SKILL.md` Step 3a when the user picks **Walk through it** instead of regenerating `HOW-TO-RUN.md`. The walkthrough is interactive: read the existing doc, present each step, optionally execute commands per-step under explicit user approval. Self-contained — do not load other reference files from here.

## Contents

- [Pre-flight](#pre-flight)
- [Per-step loop](#per-step-loop)
- [Per-step AskUserQuestion](#per-step-askuserquestion)
- [Override rules](#override-rules)
- [Cross-platform detection](#cross-platform-detection)
- [What this walkthrough never modifies](#what-this-walkthrough-never-modifies)
- [Heavy-staleness handling](#heavy-staleness-handling)
- [Completion summary](#completion-summary)

## Pre-flight

1. Read `HOW-TO-RUN.md` from the project / workspace root in full.
2. Detect the running shell once (see [Cross-platform detection](#cross-platform-detection)). Tag as `posix` or `windows` for the rest of the walkthrough.
3. Pull the per-aspect verdicts from the Step 2 audit (`Found & accurate` / `Found but outdated` / `Partial` / `Missing` / `Documented but unverifiable`). Map each command in `HOW-TO-RUN.md` to the aspect's verdict so it can be cited per step. If a command does not map to a tracked aspect, omit the verdict for that step.
4. Apply [Heavy-staleness handling](#heavy-staleness-handling) before starting the loop.

## Per-step loop

Walk the steps in document order. A step is one fenced code block, or one numbered/bulleted instruction containing a command. Combine adjacent commands in the same fence into a single step only when the doc itself groups them as one logical action.

For each step:

1. Print the source section heading (so the user has context — e.g., "From *Installation*").
2. Print the command in a fenced block, verbatim from `HOW-TO-RUN.md`.
3. Print one short sentence explaining what the command does. Assume the user reads code; do not over-explain.
4. If the step maps to a tracked aspect, print the audit verdict prefixed `Audit:` (e.g., `Audit: Found & accurate`). Omit the line otherwise.
5. Ask the per-step `AskUserQuestion` (next section), applying any matching [Override rules](#override-rules).
6. Act on the answer:
   - **Run it** — invoke the command via Bash (POSIX) or PowerShell (Windows). Capture stdout, stderr, and exit code. Print: command run, exit code, last ~20 lines of output. Append `{step_number, command, status, notes}` to an in-memory `walkthrough-log` list.
   - **I'll run it** — wait. After the user reports back, ask one follow-up question: did it succeed or fail? Record their answer in the log.
   - **Skip** — record `skipped` in the log and move on.
7. If **Run it** failed (non-zero exit), do not auto-retry. Show the error and ask the user how to proceed: **Try again** / **I'll fix it manually** / **Skip and continue** / **Stop the walkthrough**.

## Per-step AskUserQuestion

Default form (no override matched):

```
header: "Step <n>"
question: "Run `<short command preview>`? (Section: <section heading>; Audit: <verdict>)"

options:
  - "Run it"      → "I'll execute it and report stdout/stderr + exit code."
  - "I'll run it" → "I'll wait while you run it locally; tell me how it went."
  - "Skip"        → "Move to the next step."
```

`<short command preview>` is the first ~60 characters of the command, with newlines collapsed to `; `. Drop the `Audit: <verdict>` clause from the question text when no verdict applies.

## Override rules

These change the option set, not just the question text. Apply them in order; the first matching override wins. They are non-overridable safety gates — the user does not get to disable them.

| Trigger | How to detect | Override |
|---|---|---|
| **Long-running service** | Command matches any of: `npm run dev`, `yarn dev`, `pnpm dev`, `*serve*`, `docker[- ]compose up` (without `-d`), `rails s`, `rails server`, `flask run`, `gradle bootRun`, `dotnet run`, `python manage.py runserver`, `next dev`, `vite`, `nodemon`, `iex -S mix phx.server`. | Drop `"Run it"`. Show only `"I'll run it"` and `"Skip"`. Append to question text: _"This starts a long-running process; I won't run it for you."_ |
| **Destructive verb** | Command contains any of: `rm -rf`, `rm -fr`, ` DROP `, ` TRUNCATE `, `--force`, `git reset --hard`, `git clean -f`, `docker system prune`, `docker volume rm`, `kubectl delete`. | Keep all options but rename `"Run it"` to `"Run it (destructive)"`. Prepend to question text: _"Destructive command. Read it carefully before approving."_ Always re-ask, even if a prior step was approved without warning. |
| **Platform mismatch** | Command uses POSIX-only constructs (`export FOO=bar`, leading `./` invocation, `chmod`, `cp -r`, heredoc `<<EOF`) and detected shell is `windows`; or PowerShell-only constructs (`$env:FOO=`, `Set-Location`, `Get-ChildItem`) and detected shell is `posix`. | Drop `"Run it"`. Show only `"I'll run it"` and `"Skip"`. Append to question text: _"This command is `<other-platform>`-only; the current shell is `<current-platform>`. I won't auto-translate."_ |
| **Audit verdict is `Found but outdated` or `Documented but unverifiable`** | The aspect's verdict from Step 2. | Keep all options. Prepend to question text: _"Audit flagged this step as `<verdict>` — verify before running."_ |

**Never batch.** No `"Run all remaining"` option. No `"Always allow"`. Each command is asked, every time. A user who approved step 3 has not approved step 4.

## Cross-platform detection

Detect the shell once, before the loop:

- If `$env:OS` equals `Windows_NT` (PowerShell variable) or the OS platform is `win32`, tag `windows`.
- Otherwise tag `posix` (covers Linux, macOS, WSL).

Do not attempt translation between shells. The Platform-mismatch override above is the entire policy.

## What this walkthrough never modifies

- Never edits `HOW-TO-RUN.md`. If a step fails because the doc itself is wrong, note it in the [Completion summary](#completion-summary) and recommend re-running `/optimus:how-to-run` and selecting **Regenerate** — do not auto-regenerate-then-resume.
- Never writes any other file in the user project from skill code. Files written by user-invoked commands (e.g., `npm install` populating `node_modules/`) are the user's chosen action, not the skill's.
- Never bypasses an `AskUserQuestion` because the user previously approved a similar step.

## Heavy-staleness handling

After Pre-flight, if more than half of the audit's 10 aspects have a verdict of `Found but outdated` or `Missing`, print **one** message before starting the loop:

> _Audit shows the doc is heavily out of date. Consider running `/optimus:how-to-run` again and selecting **Regenerate** before walking through it. Continuing anyway._

Do not refuse — the user already chose this path. The per-step `Audit:` line and the verdict-based override give them per-command signal.

## Completion summary

When the loop exits (all steps walked or user chose **Stop the walkthrough**), print:

```
Walkthrough summary
- Steps walked: <n_total>
- Ran (succeeded): <n_succeeded>
- Ran (failed): <n_failed>
- User-run: <n_user_ran>
- Skipped: <n_skipped>
```

Then list each failed step with its command and the last line of output. If any failure looked doc-related (`command not found`, missing path, version mismatch against the audit), recommend `/optimus:how-to-run` → **Regenerate** for the next session.

Hand off per the SKILL's Step 6 *Recommend next skill* block — do not invent a separate handoff here.
