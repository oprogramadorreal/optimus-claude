# Body-File Temp File Pattern

Used by `pr`, `tdd`, and `code-review` to materialize a body/description on disk for `gh pr create --body-file` / `gh pr comment --body-file` / `glab mr create --description-file` / `glab api -F body=@…`.

## Canonical pattern

Substitute `<stem>` (e.g., `pr-body`, `review-summary`) per call site. The body is fed via a quoted heredoc so its content is never re-evaluated by the shell — backticks, `$(...)`, and `$VAR` inside the body are written verbatim. Run as one chained bash invocation so the `trap` covers every step:

```bash
TMPFILE=$(mktemp ./.<stem>-XXXXXX.md) && trap 'rm -f "$TMPFILE"' EXIT INT TERM && cat > "$TMPFILE" <<'OPTIMUS_BODY_EOF' && <gh-or-glab-command-using "$TMPFILE">
<body>
OPTIMUS_BODY_EOF
```

The `&& <gh-or-glab-command>` on the same line as the heredoc opener is valid bash — the heredoc body (between the marker lines) is `cat`'s stdin, and the `&&` chains the next command after `cat` succeeds.

## Why this exact shape

1. **Path in CWD** — Windows-native `gh.exe` / `glab.exe` cannot resolve Git Bash's `/tmp` mount; using a `/tmp` path silently submits an empty body / comment. A `./…` relative path is identical for the POSIX shell and the Windows binary.
2. **Quoted heredoc (`<<'OPTIMUS_BODY_EOF'`)** — disables shell expansion of the body content. PR descriptions, commit messages, and review summaries can contain `$(...)`, backticks, or `$` from diff snippets; without the quoted delimiter those would execute on the developer's machine when the chained command runs.
3. **Dot-prefixed filename** — orphan files left after an interruption are excluded from `git add *.md` (bash `dotglob` off by default). Note: `git add .` and `git add -A` *do* stage dotfiles — the dot-prefix only mitigates the glob form. If the trap fails (SIGKILL, power loss), an orphan can still be picked up by `git add .`; call sites that handle sensitive bodies should ensure `.<stem>-*.md` is gitignored.
4. **`trap … EXIT INT TERM`** — guarantees cleanup even if the `gh`/`glab` step is Ctrl-C'd or errors out. Without it, the temp file persists in the working tree.
5. **`--tmpdir` is not used** — it's a GNU coreutils extension that BSD `mktemp` on macOS rejects.

## Validator contract

`scripts/validate.sh` forbids non-portable mktemp invocations in `skills/*/SKILL.md` (`/tmp/`, `${TMPDIR:-/tmp}`, `--tmpdir`, `-p`, `-t`) and pins consumer references to this file so a silent revert is caught.
