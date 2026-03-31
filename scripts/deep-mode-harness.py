#!/usr/bin/env python3
"""
Deep-mode harness — external orchestrator for iterative code review / refactor.

Launches fresh `claude -p` sessions per iteration, passing state through a JSON
progress file. Each session gets a clean context window, eliminating the context
bloat that limits in-conversation deep mode to ~3 effective iterations.

Requirements:
  - claude CLI installed and authenticated (Max subscription or API key)
  - Python 3.8+ (stdlib only — no pip dependencies)

Usage:
  /optimus:code-review deep harness            # invoke from within a conversation
  /optimus:refactor deep harness 8 "backend"   # with iteration cap and scope

  python scripts/deep-mode-harness.py --skill code-review
  python scripts/deep-mode-harness.py --skill code-review --scope "src/auth"
  python scripts/deep-mode-harness.py --skill refactor --max-iterations 8 --scope "src/api"
  python scripts/deep-mode-harness.py --skill code-review --resume

Security: By default, each claude -p session runs with --dangerously-skip-permissions
because the harness is headless — there is no terminal to approve tool prompts. This
bypasses allow/deny lists and PreToolUse hooks. For a safer alternative, use
--allowed-tools to restrict sessions to a specific tool whitelist via --allowedTools.
For OS-level isolation, use Claude Code's built-in sandboxing (macOS/Linux) or
devcontainers.

The test command is extracted from .claude/CLAUDE.md or --test-command and executed
via shell=True. Treat cloned repos as untrusted — review .claude/CLAUDE.md before
running the harness on unfamiliar codebases.
"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_ITERATIONS = 8
MAX_ITERATIONS_HARD_CAP = 20
DEFAULT_MAX_TURNS = 30
SESSION_TIMEOUT = 600  # 10 minutes per iteration
PROGRESS_FILE_NAME = ".claude/deep-mode-progress.json"
BACKUP_SUFFIX = ".bak"

PREFIX = "[deep-mode]"

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def make_initial_progress(skill, scope, max_iterations, test_command, project_root):
    """Create the initial progress file structure."""
    base_commit = git_rev_parse_head(project_root)
    return {
        "schema_version": 1,
        "skill": skill,
        "started_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "max_iterations": max_iterations,
            "test_command": test_command,
            "scope": {
                "mode": "local-changes" if not scope else "directory",
                "paths": [scope] if scope else [],
                "base_ref": None,
            },
            "project_root": str(project_root).replace("\\", "/"),
            "base_commit": base_commit,
        },
        "iteration": {"current": 1, "completed": 0},
        "findings": [],
        "scope_files": {"current": [scope] if scope else []},
        "test_results": {"last_full_run": None, "last_run_output_summary": None},
        "iteration_history": [],
        "termination": {"reason": None, "message": None},
    }


def generate_finding_id(progress):
    """Generate the next finding ID (f-001, f-002, ...)."""
    existing_ids = [f["id"] for f in progress["findings"] if "id" in f]
    max_num = 0
    for fid in existing_ids:
        match = re.match(r"f-(\d+)", fid)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"f-{max_num + 1:03d}"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def git_rev_parse_head(cwd):
    """Get the current HEAD commit SHA."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_restore_to(commit, cwd):
    """Restore working tree to match a commit (tracked + untracked files)."""
    result = subprocess.run(
        ["git", "checkout", commit, "--", "."],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git checkout {commit} failed: {result.stderr}")
    # Remove untracked files/dirs left by the failed iteration
    subprocess.run(
        ["git", "clean", "-fd"], cwd=str(cwd), capture_output=True, text=True
    )


def git_stash_snapshot(cwd):
    """Create a stash snapshot of current working tree without modifying it.

    Returns a stash commit SHA that can be restored later, or None if no changes.
    Uses 'git stash create' which creates a commit object without modifying the
    working tree, index, or stash reflog. The commit is then registered in the
    stash reflog so that 'git stash apply' processes the untracked-files tree.
    """
    result = subprocess.run(
        ["git", "stash", "create", "--include-untracked"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    sha = result.stdout.strip()
    if not sha:
        return None
    # Register in stash reflog so 'git stash apply' handles untracked files
    subprocess.run(
        ["git", "stash", "store", "-m", "deep-mode snapshot", sha],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    return sha


def git_restore_snapshot(snapshot_sha, cwd):
    """Restore working tree from a stash snapshot created by git_stash_snapshot."""
    # First reset to HEAD to clean working tree (tracked files)
    subprocess.run(
        ["git", "checkout", "."], cwd=str(cwd), capture_output=True, text=True
    )
    # Remove untracked files/dirs left by the failed iteration
    subprocess.run(
        ["git", "clean", "-fd"], cwd=str(cwd), capture_output=True, text=True
    )
    # Then apply the snapshot (includes untracked files if --include-untracked was used)
    result = subprocess.run(
        ["git", "stash", "apply", snapshot_sha],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{PREFIX} WARNING: Could not restore snapshot: {result.stderr[:200]}")
        return False
    return True


def git_diff_has_changes(cwd):
    """Check if there are any uncommitted changes (staged, unstaged, or untracked)."""
    unstaged = subprocess.run(
        ["git", "diff", "--quiet"], cwd=str(cwd), capture_output=True
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=str(cwd), capture_output=True
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(cwd), capture_output=True, text=True,
    )
    return (unstaged.returncode != 0 or staged.returncode != 0
            or bool(untracked.stdout.strip()))


def _build_commit_body(progress, iteration, max_entries=10):
    """Build commit body listing per-fix details for this iteration."""
    findings = progress.get("findings", [])
    iter_findings = [
        f for f in findings if f.get("iteration_last_attempted") == iteration
    ]
    if not iter_findings:
        return ""

    fixed = [f for f in iter_findings if f.get("status") == "fixed"]
    reverted = [
        f for f in iter_findings
        if f.get("status", "").startswith("reverted")
    ]

    lines = ["Harness checkpoint — automated fixes applied and tested.", ""]

    def _fmt(f):
        loc = f"{f['file']}:{f.get('line', '?')}"
        cat = f.get("category", "unknown")
        summary = f.get("summary", "").replace("\n", " ").replace("\r", "")
        # Truncate long summaries for readability
        if len(summary) > 72:
            summary = summary[:69] + "..."
        return f"- {loc} [{cat}] {summary}"

    if fixed:
        lines.append("Fixed:")
        shown = fixed[:max_entries]
        for f in shown:
            lines.append(_fmt(f))
        overflow = len(fixed) - max_entries
        if overflow > 0:
            lines.append(f"- ... and {overflow} more")
        lines.append("")

    if reverted:
        lines.append("Reverted (test failure):")
        shown = reverted[:max_entries]
        for f in shown:
            lines.append(_fmt(f))
        overflow = len(reverted) - max_entries
        if overflow > 0:
            lines.append(f"- ... and {overflow} more")
        lines.append("")

    return "\n".join(lines)


def git_commit_checkpoint(progress, iteration, cwd):
    """Create a checkpoint commit for this iteration. Returns True on success."""
    skill = progress["skill"]
    hist = progress["iteration_history"]
    latest = hist[-1] if hist else {}
    fixed = latest.get("fixed", 0)
    reverted = latest.get("reverted", 0)

    title = (
        f"deep-harness({skill}): iteration {iteration} — "
        f"{fixed} fixed, {reverted} reverted"
    )
    body = _build_commit_body(progress, iteration)
    msg = f"{title}\n\n{body}" if body else title

    add_result = subprocess.run(
        ["git", "add", "-A"], cwd=str(cwd), capture_output=True, text=True
    )
    if add_result.returncode != 0:
        print(f"{PREFIX} WARNING: git add -A failed: {add_result.stderr[:200]}")
        return False
    # Un-stage harness state files from checkpoint commits
    for pattern in [PROGRESS_FILE_NAME, PROGRESS_FILE_NAME + BACKUP_SUFFIX]:
        subprocess.run(
            ["git", "reset", "HEAD", "--", pattern],
            cwd=str(cwd), capture_output=True, text=True,
        )
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")
        return False
    return True


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def write_progress(path, progress):
    """Write the progress file with a backup."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(str(path), str(path) + BACKUP_SUFFIX)
    path.write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")


def read_progress(path):
    """Read the progress file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test execution (harness-side)
# ---------------------------------------------------------------------------


def _find_bash():
    """Return the path to a usable bash executable, preferring Git Bash on Windows."""
    if sys.platform != "win32":
        return "bash"

    # shutil.which respects PATH order — check if it resolves to WSL's bash
    candidate = shutil.which("bash")
    if candidate:
        normalized = candidate.replace("\\", "/").lower()
        if "system32" not in normalized:
            return candidate  # Not WSL — use it (likely Git Bash already on PATH)

    # WSL bash or no bash on PATH — look for Git Bash explicitly
    # Method 1: use git --exec-path to find Git's installation
    try:
        result = subprocess.run(
            ["git", "--exec-path"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            # e.g. "C:/Program Files/Git/mingw64/libexec/git-core"
            git_exec = Path(result.stdout.strip())
            git_root = git_exec.parent.parent.parent  # up from mingw64/libexec/git-core
            git_bash = git_root / "bin" / "bash.exe"
            if git_bash.exists():
                return str(git_bash)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Method 2: check common installation paths
    for path in [
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/bin/bash.exe"),
    ]:
        if path.exists():
            return str(path)

    # Fallback: return bare "bash" and let it fail with a clear error downstream
    return "bash"


def run_tests(test_command, cwd):
    """Run the project's test command. Returns (passed: bool, output: str)."""
    print(f"{PREFIX} Running tests: {test_command}")
    # On Windows, shell=True uses cmd.exe which doesn't support bash operators
    # like && or ||. Wrap with bash -c if the command uses them.
    effective_command = test_command
    use_shell = True
    if sys.platform == "win32":
        # On Windows, shell=True uses cmd.exe which misparses bash operators
        # (&&, ||), subshells ($(...)), env vars ($VAR), and redirections (2>).
        # Always route through bash for consistent behavior.
        effective_command = [_find_bash(), "-c", test_command]
        use_shell = False
    try:
        result = subprocess.run(
            effective_command,
            shell=use_shell,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=300,  # 5 min for tests
        )
    except subprocess.TimeoutExpired:
        print(f"{PREFIX} Tests timed out after 300s")
        return False, "Test command timed out after 300s"
    passed = result.returncode == 0
    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    # Truncate output for summary
    summary_lines = output.split("\n")[-5:]
    summary = "\n".join(summary_lines)
    status = "PASS" if passed else "FAIL"
    print(f"{PREFIX} Tests: {status}")
    return passed, summary


# ---------------------------------------------------------------------------
# Bisection — mechanical apply/revert using pre/post content
# ---------------------------------------------------------------------------


def _is_path_within(filepath, root):
    """Check if filepath is within root (Python 3.8 compatible)."""
    try:
        filepath.relative_to(root)
        return True
    except ValueError:
        return False


def _swap_content(fix, cwd, find_key, replace_key):
    """Swap one content string for another in a file."""
    # Normalize path separators for cross-platform compatibility
    fix_file = fix["file"].replace("\\", "/")
    filepath = (Path(cwd) / fix_file).resolve()
    if not _is_path_within(filepath, Path(cwd).resolve()):
        return False
    # Block writes to sensitive paths
    try:
        rel = filepath.relative_to(Path(cwd).resolve())
        if any(part == ".git" for part in rel.parts):
            return False
    except ValueError:
        return False
    if not filepath.exists():
        return False
    content = filepath.read_text(encoding="utf-8")
    find = fix.get(find_key, "")
    replace = fix.get(replace_key, "")
    if not find:
        # Empty find string — cannot locate target in file content.
        # This happens when reverting a deletion fix (empty post_edit_content):
        # the revert needs to re-insert pre_edit_content but has no position info.
        return False
    if find not in content:
        return False
    if content.count(find) != 1:
        return False  # Ambiguous match — refuse to apply/revert
    filepath.write_text(content.replace(find, replace, 1), encoding="utf-8")
    return True


def apply_single_fix(fix, cwd):
    """Apply a single fix by replacing pre_edit_content with post_edit_content."""
    return _swap_content(fix, cwd, "pre_edit_content", "post_edit_content")


def revert_single_fix(fix, cwd):
    """Revert a single fix by replacing post_edit_content with pre_edit_content."""
    return _swap_content(fix, cwd, "post_edit_content", "pre_edit_content")


def bisect_fixes(fixes, test_command, cwd, progress):
    """
    Incremental bisection: revert all fixes, then re-apply one by one,
    keeping passing fixes applied so subsequent fixes can depend on them.
    After the first pass, retry reverted fixes (they may depend on fixes
    that were applied later in the first pass).
    Returns (fixed_count, reverted_count).
    """
    print(f"{PREFIX} Bisecting {len(fixes)} fixes...")
    # Revert all this iteration's fixes mechanically (preserves prior uncommitted work)
    revert_failures = set()
    for i in range(len(fixes) - 1, -1, -1):
        if not revert_single_fix(fixes[i], cwd):
            revert_failures.add(i)
            print(f"{PREFIX} WARNING: Could not mechanically revert fix for {fixes[i].get('file')}")

    fixed_count = 0
    reverted_count = 0
    reverted_indices = []

    # First pass: apply incrementally, keeping passing fixes
    for i, fix in enumerate(fixes):
        if i in revert_failures:
            mark_finding_status(progress, fix, "retained — revert failed",
                                "Could not mechanically revert during bisection — fix retained untested")
            fixed_count += 1  # counts toward applied (fix is in codebase)
            continue
        applied = apply_single_fix(fix, cwd)
        if not applied:
            reverted_indices.append(i)
            continue

        ok, _ = run_tests(test_command, cwd)
        if ok:
            mark_finding_status(progress, fix, "fixed", None)
            fixed_count += 1
        else:
            if not revert_single_fix(fix, cwd):
                print(f"{PREFIX} WARNING: Could not revert failing fix for {fix.get('file')} — retaining fix")
                mark_finding_status(progress, fix, "fixed",
                                    "Revert failed after test failure — fix retained")
                fixed_count += 1
            else:
                reverted_indices.append(i)

    # Second pass: retry reverted fixes — they may depend on fixes that
    # were applied later in the first pass (e.g., fix A uses an import
    # that fix B added, but B had a higher index)
    if reverted_indices and fixed_count > 0:
        print(f"{PREFIX} Retrying {len(reverted_indices)} reverted fixes...")
        for i in reverted_indices:
            fix = fixes[i]
            applied = apply_single_fix(fix, cwd)
            if not applied:
                mark_finding_status(progress, fix, "reverted — test failure",
                                    "Could not mechanically re-apply fix")
                reverted_count += 1
                continue

            ok, _ = run_tests(test_command, cwd)
            if ok:
                mark_finding_status(progress, fix, "fixed", "Passed on retry (dependency resolved)")
                fixed_count += 1
            else:
                if not revert_single_fix(fix, cwd):
                    print(f"{PREFIX} WARNING: Could not revert failing fix for {fix.get('file')} — retaining fix")
                    mark_finding_status(progress, fix, "fixed",
                                        "Revert failed after test failure — fix retained")
                    fixed_count += 1
                else:
                    mark_finding_status(progress, fix, "reverted — test failure", "Test failure during bisection")
                    reverted_count += 1
    else:
        # No retry needed — mark remaining reverted fixes
        for i in reverted_indices:
            mark_finding_status(progress, fixes[i], "reverted — test failure",
                                "Test failure during bisection")
            reverted_count += 1

    return fixed_count, reverted_count


# ---------------------------------------------------------------------------
# Finding status management
# ---------------------------------------------------------------------------


def mark_finding_status(progress, fix, status, detail):
    """Update a finding's status in the progress file."""
    # Try to find existing finding by file+line+category match
    for f in progress["findings"]:
        if (f["file"] == fix.get("file", "") and f.get("line") == fix.get("line")
                and f.get("category") == fix.get("category")):
            old_status = f["status"]
            # Promote reverted -> attempt 2 -> persistent
            if status == "reverted — test failure" and old_status == "reverted — test failure":
                status = "reverted — attempt 2"
            elif status == "reverted — test failure" and old_status == "reverted — attempt 2":
                status = "persistent — fix failed"

            f["status"] = status
            f["iteration_last_attempted"] = progress["iteration"]["current"]
            f.setdefault("status_history", []).append({
                "iteration": progress["iteration"]["current"],
                "status": status,
                "detail": detail,
            })
            return

    # Not found — add as new finding
    new_finding = {
        "id": generate_finding_id(progress),
        "file": fix.get("file", ""),
        "line": fix.get("line", 0),
        "end_line": fix.get("end_line", fix.get("line", 0)),
        "category": fix.get("category", ""),
        "guideline": fix.get("guideline", ""),
        "summary": fix.get("summary", ""),
        "fix_description": fix.get("fix_description", ""),
        "iteration_discovered": progress["iteration"]["current"],
        "iteration_last_attempted": progress["iteration"]["current"],
        "status": status,
        "status_history": [
            {
                "iteration": progress["iteration"]["current"],
                "status": status,
                "detail": detail,
            }
        ],
        "agent": fix.get("agent", ""),
        "confidence": fix.get("confidence", ""),
        "severity": fix.get("severity", ""),
        "pre_edit_content": fix.get("pre_edit_content", ""),
        "post_edit_content": fix.get("post_edit_content", ""),
    }
    progress["findings"].append(new_finding)


def mark_all_fixed(progress, fixes):
    """Mark all fixes as fixed after tests passed."""
    for fix in fixes:
        mark_finding_status(progress, fix, "fixed", None)


# ---------------------------------------------------------------------------
# Scope management
# ---------------------------------------------------------------------------


def update_scope(progress, result):
    """
    Update scope_files for the next iteration.
    code-review: narrow to files with findings + newly modified files.
    refactor: keep the same scope (no narrowing).
    """
    if progress["skill"] == "refactor":
        return  # refactor keeps constant scope

    # code-review: narrow scope
    finding_files = set()
    for f in progress["findings"]:
        if f["status"] != "persistent — fix failed":
            finding_files.add(f["file"])
    for f in result.get("fixes_applied", []):
        finding_files.add(f["file"])

    # Merge with existing scope
    current = set(progress["scope_files"]["current"])
    current.update(finding_files)
    progress["scope_files"]["current"] = sorted(current)


# ---------------------------------------------------------------------------
# Claude session
# ---------------------------------------------------------------------------


def run_skill_session(progress, args, resolved_progress_path):
    """
    Launch a fresh claude -p session for one iteration.
    Returns the raw stdout output.
    """
    skill = progress["skill"]
    iteration = progress["iteration"]["current"]
    max_iter = progress["config"]["max_iterations"]
    # Use forward slashes for cross-platform compatibility in system prompt
    progress_path = str(resolved_progress_path).replace("\\", "/")

    # Build the skill invocation prompt (skill is validated by argparse choices)
    if skill == "code-review":
        prompt = "/optimus:code-review deep"
    else:
        prompt = f"/optimus:refactor deep {max_iter}"

    # Add scope hint
    scope_paths = progress["scope_files"]["current"]
    if scope_paths:
        paths_str = ", ".join(scope_paths[:20])
        prompt += f' "focus on: {paths_str}"'

    # Harness-mode system prompt
    harness_system = (
        f"HARNESS_MODE_ACTIVE: You are running inside the deep-mode harness. "
        f"Progress file: {progress_path}\n"
        f"This is iteration {iteration} of {max_iter}. "
        f"Do NOT use AskUserQuestion. Do NOT loop. Do NOT run tests. "
        f"Read the progress file for accumulated findings and scope. "
        f"After applying fixes, output structured JSON in a "
        f"```json:harness-output block and stop."
    )

    cmd = [
        "claude",
        "-p",
        prompt,
        "--append-system-prompt",
        harness_system,
    ]

    # Permission handling: --allowedTools (safer) or --dangerously-skip-permissions (default)
    if getattr(args, "allowed_tools", None):
        cmd.extend(["--allowedTools", args.allowed_tools])
    else:
        cmd.append("--dangerously-skip-permissions")

    cmd.extend([
        "--max-turns",
        str(args.max_turns),
        "--output-format",
        "json",
    ])

    if args.verbose:
        print(f"{PREFIX} Command: {' '.join(cmd[:6])}...")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=progress["config"]["project_root"],
        timeout=SESSION_TIMEOUT,
    )

    if args.verbose:
        print(f"{PREFIX} Exit code: {result.returncode}")
        if result.stderr:
            print(f"{PREFIX} Stderr: {result.stderr[:500]}")

    if result.returncode == 1:
        print(f"{PREFIX} WARNING: claude exited with code 1 (may indicate partial failure): {result.stderr[:200]}")
    elif result.returncode > 1:
        raise RuntimeError(
            f"claude exited with code {result.returncode}: {result.stderr[:200]}"
        )

    return result.stdout


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------


def parse_harness_output(raw_output):
    """
    Extract the json:harness-output block from claude's response.
    With --output-format json, the output is a JSON object with a 'result' field.
    """
    if not raw_output:
        return None

    # Try to parse as --output-format json envelope
    text = raw_output
    try:
        envelope = json.loads(raw_output)
        if isinstance(envelope, dict) and "result" in envelope:
            text = envelope["result"]
    except (json.JSONDecodeError, TypeError):
        pass

    if not isinstance(text, str):
        return None

    # Extract json:harness-output block
    pattern = r"```json:harness-output\s*\n(.*?)\n\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def print_report(progress):
    """Print the consolidated cumulative report."""
    findings = progress["findings"]
    total_fixed = sum(1 for f in findings if f["status"] in ("fixed", "retained — revert failed"))
    total_reverted = sum(
        1
        for f in findings
        if f["status"] in ("reverted — test failure", "reverted — attempt 2")
    )
    total_persistent = sum(
        1 for f in findings if f["status"] == "persistent — fix failed"
    )
    iterations = progress["iteration"]["completed"]

    last_test = progress["test_results"]["last_full_run"] or "not available"

    print(f"\n{PREFIX}")
    print(f"{PREFIX} {'=' * 50}")
    print(f"{PREFIX}   Cumulative Report")
    print(f"{PREFIX} {'=' * 50}")
    print(f"{PREFIX}   Skill:         {progress['skill']}")
    print(f"{PREFIX}   Iterations:    {iterations}")
    print(f"{PREFIX}   Fixed:         {total_fixed}")
    print(f"{PREFIX}   Reverted:      {total_reverted}")
    print(f"{PREFIX}   Persistent:    {total_persistent}")
    print(f"{PREFIX}   Final tests:   {last_test}")

    term = progress["termination"]
    if term["reason"]:
        print(f"{PREFIX}   Stopped:       {term['reason']} — {term.get('message', '')}")

    print(f"{PREFIX} {'=' * 50}")

    if findings:
        print(f"{PREFIX}")
        print(
            f"{PREFIX}   {'#':<4} {'Iter':<5} {'File':<40} {'Category':<15} {'Summary':<40} {'Status'}"
        )
        print(f"{PREFIX}   {'-'*4} {'-'*5} {'-'*40} {'-'*15} {'-'*40} {'-'*20}")
        for i, f in enumerate(findings, 1):
            file_loc = f"{f['file']}:{f.get('line', '?')}"
            if len(file_loc) > 40:
                file_loc = "..." + file_loc[-37:]
            summary = f["summary"][:40]
            iter_num = f.get("iteration_discovered", "?")
            print(
                f"{PREFIX}   {i:<4} {iter_num:<5} {file_loc:<40} "
                f"{f['category']:<15} {summary:<40} {f['status']}"
            )

    print(f"{PREFIX}")
    base = progress["config"].get("base_commit") or "?"

    if total_fixed > 0:
        print(
            f"{PREFIX} To squash checkpoint commits: git rebase -i {base[:8]}"
        )
        print(
            f"{PREFIX} To rollback everything:       git reset --hard {base[:8]}"
        )
        # Suggest push if on a feature branch (not main/master)
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=progress["config"]["project_root"],
            capture_output=True, text=True,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
        if branch and branch not in ("main", "master"):
            print(
                f"{PREFIX} To push checkpoint branch:    git push -u origin {branch}"
            )
        print(f"{PREFIX}")
        print(f"{PREFIX} Next: run /optimus:commit to commit the fixes.")
        print(
            f"{PREFIX} Tip: start a fresh conversation for the next skill "
            f"— each skill gathers its own context from scratch."
        )
    elif term["reason"] in ("parse-failure", "crash"):
        print(f"{PREFIX} No fixes were retained. Check the test output above for details.")
        print(f"{PREFIX} To rollback everything: git reset --hard {base[:8]}")
        print(
            f"{PREFIX} Tip: start a fresh conversation for the next skill "
            f"— each skill gathers its own context from scratch."
        )
    else:
        print(f"{PREFIX} No issues found — the codebase looks clean for this skill.")
        print(
            f"{PREFIX} Tip: start a fresh conversation for the next skill "
            f"— each skill gathers its own context from scratch."
        )


# ---------------------------------------------------------------------------
# Test command detection
# ---------------------------------------------------------------------------


def detect_test_command(project_root):
    """
    Try to extract the test command from .claude/CLAUDE.md.
    Looks for common patterns like 'test command: ...' or code blocks with test commands.
    """
    claude_md = Path(project_root) / ".claude" / "CLAUDE.md"
    if not claude_md.exists():
        return None

    content = claude_md.read_text(encoding="utf-8")

    # Look for explicit test command patterns
    patterns = [
        r"(?:test|tests)\s*(?:command|cmd)\s*[:=]\s*`([^`]+)`",
        r"```\s*(?:bash|sh)?\s*\n\s*(.+?(?:test|spec|jest|pytest|cargo test|go test|dotnet test).*)\s*\n\s*```",
        r"(?:run\s+tests?|testing)\s*[:]\s*`([^`]+)`",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            cmd = match.group(1).strip()
            # Remove trailing shell comments (e.g. "npm test  # Run tests")
            cmd = re.sub(r"\s+#\s.*$", "", cmd)
            return cmd

    return None


# ---------------------------------------------------------------------------
# Safe-exit helper (convergence / no-actionable)
# ---------------------------------------------------------------------------


def handle_safe_exit(progress, progress_path, args, reason, message, log_message,
                     new_count, pre_snapshot, pre_hash):
    """Handle convergence or no-actionable-fixes exit with test verification."""
    iteration = progress["iteration"]["current"]
    project_root = progress["config"]["project_root"]
    test_command = progress["config"]["test_command"]
    test_passed = True
    if git_diff_has_changes(project_root):
        print(f"{PREFIX} {log_message} but working tree has changes — verifying tests")
        ok, summary = run_tests(test_command, project_root)
        test_passed = ok
        progress["test_results"]["last_full_run"] = "pass" if ok else "fail"
        progress["test_results"]["last_run_output_summary"] = summary
        if not ok:
            print(f"{PREFIX} Tests failed — reverting unexpected changes")
            if pre_snapshot:
                if not git_restore_snapshot(pre_snapshot, project_root):
                    git_restore_to(pre_hash, project_root)
            else:
                git_restore_to(pre_hash, project_root)
    progress["termination"] = {"reason": reason, "message": message}
    progress["iteration"]["completed"] = iteration
    progress["iteration_history"].append({
        "iteration": iteration,
        "new_findings": new_count,
        "fixed": 0,
        "reverted": 0,
        "persistent": 0,
        "test_passed": test_passed,
    })
    write_progress(progress_path, progress)
    if not args.no_commit and test_passed and git_diff_has_changes(project_root):
        git_commit_checkpoint(progress, iteration, project_root)
    return test_passed


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Deep-mode harness — iterative code review/refactor with fresh context per iteration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/deep-mode-harness.py --skill code-review
  python scripts/deep-mode-harness.py --skill refactor --max-iterations 8 --scope "src/api"
  python scripts/deep-mode-harness.py --skill code-review --resume
        """,
    )
    parser.add_argument(
        "--skill",
        required=True,
        choices=["code-review", "refactor"],
        help="Which skill to run in deep mode",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help=f"Iteration cap (default: {DEFAULT_MAX_ITERATIONS}, max: {MAX_ITERATIONS_HARD_CAP})",
    )
    parser.add_argument(
        "--scope",
        default="",
        help="Path filter or scope hint (e.g., 'src/auth')",
    )
    parser.add_argument(
        "--progress-file",
        default=PROGRESS_FILE_NAME,
        help=f"Path to progress file (default: {PROGRESS_FILE_NAME})",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=DEFAULT_MAX_TURNS,
        help=f"Per-session turn limit for claude -p (default: {DEFAULT_MAX_TURNS})",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing progress file",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Skip checkpoint commits after each iteration",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed skill session output",
    )
    parser.add_argument(
        "--test-command",
        default="",
        help="Override the test command (default: auto-detect from .claude/CLAUDE.md)",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Target project directory (default: current directory)",
    )
    parser.add_argument(
        "--allowed-tools",
        default="",
        help=(
            "Use --allowedTools instead of --dangerously-skip-permissions. "
            "Comma-separated list of tools to allow "
            "(default when flag is given without value: "
            "Read,Edit,Write,MultiEdit,Glob,Grep,Bash,Agent)"
        ),
        nargs="?",
        const="Read,Edit,Write,MultiEdit,Glob,Grep,Bash,Agent",
    )

    args = parser.parse_args()

    # Clamp iterations
    if args.max_iterations > MAX_ITERATIONS_HARD_CAP:
        print(f"{PREFIX} Iteration cap clamped to {MAX_ITERATIONS_HARD_CAP} (maximum).")
        args.max_iterations = MAX_ITERATIONS_HARD_CAP
    if args.max_iterations < 1:
        print(f"{PREFIX} Iteration cap clamped to 1 (minimum).")
        args.max_iterations = 1

    project_root = Path(args.project_dir).resolve()

    # Check claude CLI
    try:
        claude_check = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True
        )
    except FileNotFoundError:
        claude_check = None
    if claude_check is None or claude_check.returncode != 0:
        print(f"{PREFIX} ERROR: claude CLI not found. Install and authenticate first.")
        sys.exit(1)

    # Detect test command
    test_command = args.test_command or detect_test_command(project_root)
    if not test_command:
        print(f"{PREFIX} ERROR: No test command found in .claude/CLAUDE.md.")
        print(f"{PREFIX} Deep mode requires a test command for safe auto-apply.")
        print(f"{PREFIX} Run /optimus:init to set up test infrastructure, or pass --test-command.")
        sys.exit(1)

    # Initialize or resume
    progress_path = Path(args.progress_file)
    if not progress_path.is_absolute():
        progress_path = project_root / progress_path

    if args.resume:
        if not progress_path.exists():
            # Try backup
            backup = Path(str(progress_path) + BACKUP_SUFFIX)
            if backup.exists():
                print(f"{PREFIX} Progress file not found, restoring from backup...")
                shutil.copy2(str(backup), str(progress_path))
            else:
                print(f"{PREFIX} ERROR: No progress file to resume from: {progress_path}")
                sys.exit(1)
        progress = read_progress(progress_path)
        # Validate progress file structure
        required_keys = ["skill", "iteration", "config", "findings"]
        for key in required_keys:
            if key not in progress:
                print(f"{PREFIX} ERROR: Progress file missing required field '{key}'")
                sys.exit(1)
        if progress["skill"] != args.skill:
            print(
                f"{PREFIX} ERROR: Progress file skill '{progress['skill']}' "
                f"does not match --skill '{args.skill}'"
            )
            sys.exit(1)
        saved_root_str = progress["config"].get("project_root")
        if not saved_root_str:
            print(f"{PREFIX} ERROR: Progress file missing project_root")
            sys.exit(1)
        saved_root = Path(saved_root_str).resolve()
        if saved_root != project_root:
            print(
                f"{PREFIX} ERROR: Progress file project_root '{saved_root}' "
                f"does not match --project-dir '{project_root}'"
            )
            sys.exit(1)
        # Allow extending the iteration cap on resume
        if args.max_iterations != DEFAULT_MAX_ITERATIONS:
            progress["config"]["max_iterations"] = args.max_iterations
        print(f"{PREFIX} Resuming from iteration {progress['iteration']['current']}")
    else:
        if progress_path.exists():
            print(f"{PREFIX} WARNING: Overwriting existing progress file: {progress_path}")
        progress = make_initial_progress(
            args.skill, args.scope, args.max_iterations, test_command, project_root
        )

    # Validate base commit
    if not progress["config"]["base_commit"]:
        print(f"{PREFIX} ERROR: Cannot determine HEAD commit. Is this a git repository?")
        sys.exit(1)

    # Refuse to start with uncommitted changes (fresh runs only)
    if not args.resume and not args.no_commit and git_diff_has_changes(project_root):
        print(f"{PREFIX} ERROR: Uncommitted changes detected.")
        print(f"{PREFIX} The harness creates checkpoint commits per iteration,")
        print(f"{PREFIX} which would include your existing changes in the first commit.")
        print(f"{PREFIX}")
        print(f"{PREFIX} Commit your changes first:  git add -A && git commit -m \"wip\"")
        print(f"{PREFIX} Or stash them:              git stash push -m \"pre-harness\"")
        sys.exit(1)

    # Print startup info
    max_iter = progress["config"]["max_iterations"]
    # 7 agents for code-review, 4 for refactor; +1 per iteration for harness overhead
    remaining = max_iter - progress["iteration"]["current"] + 1
    agents = 7 if args.skill == "code-review" else 4
    estimated_messages = remaining * agents + remaining
    print(f"{PREFIX} Starting {args.skill} harness (max {max_iter} iterations)")
    print(f"{PREFIX} Test command: {test_command}")
    print(f"{PREFIX} Base commit: {progress['config']['base_commit'][:8]}")
    print(f"{PREFIX} Estimated messages: ~{estimated_messages} (check rate limits)")
    print(f"{PREFIX} Press Ctrl+C to stop — progress is saved. Resume with --resume.")
    print(f"{PREFIX}")

    # Main iteration loop
    try:
        _run_iteration_loop(args, progress, progress_path, project_root,
                            test_command, max_iter)
    except KeyboardInterrupt:
        print(f"\n{PREFIX} Interrupted.")
        if not args.no_commit and git_diff_has_changes(project_root):
            print(f"{PREFIX} Committing completed work from current iteration...")
            git_commit_checkpoint(progress, progress["iteration"]["current"],
                                 project_root)
        progress["termination"] = {
            "reason": "interrupted",
            "message": "User pressed Ctrl+C",
        }
        write_progress(progress_path, progress)
        print(f"{PREFIX} Progress saved. Resume with --resume flag.")
        print_report(progress)
        return

    # Final report
    print_report(progress)

    # Archive progress file and clean up backup
    done_path = progress_path.with_suffix(".done.json")
    if done_path.exists():
        done_path.unlink()
    shutil.move(str(progress_path), str(done_path))
    Path(str(progress_path) + BACKUP_SUFFIX).unlink(missing_ok=True)
    print(f"{PREFIX} Progress archived to {done_path.name}")


def _run_iteration_loop(args, progress, progress_path, project_root,
                        test_command, max_iter):
    """Inner iteration loop, extracted to allow KeyboardInterrupt wrapping."""
    while True:
        iteration = progress["iteration"]["current"]
        print(f"{PREFIX} === Iteration {iteration}/{max_iter} ===")
        t_start = time.time()

        # Snapshot git state before this iteration
        pre_hash = git_rev_parse_head(project_root)
        if not pre_hash:
            print(f"{PREFIX} ERROR: Cannot determine HEAD commit before iteration {iteration}.")
            sys.exit(1)

        # When --no-commit, prior iterations leave uncommitted changes.
        # Snapshot them so we can restore on failure without losing that work.
        pre_snapshot = git_stash_snapshot(project_root) if args.no_commit else None

        # Write progress file for skill to read
        write_progress(progress_path, progress)

        # Launch fresh claude -p session (with 1 retry)
        output = None
        for attempt in range(2):
            try:
                output = run_skill_session(progress, args, progress_path)
                break
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                if isinstance(e, subprocess.TimeoutExpired):
                    print(f"{PREFIX} Session timed out after {SESSION_TIMEOUT}s")
                else:
                    print(f"{PREFIX} Session error: {e}")
                if pre_snapshot:
                    if not git_restore_snapshot(pre_snapshot, project_root):
                        git_restore_to(pre_hash, project_root)
                else:
                    git_restore_to(pre_hash, project_root)
                if attempt == 0:
                    write_progress(progress_path, progress)
                    print(f"{PREFIX} Retrying iteration {iteration}...")
                else:
                    print(f"{PREFIX} Iteration {iteration} failed after retry. Stopping.")
                    progress["termination"] = {
                        "reason": "crash",
                        "message": f"Session failed twice on iteration {iteration}: {e}",
                    }
                    write_progress(progress_path, progress)
                    print_report(progress)
                    sys.exit(1)

        # Parse structured output
        result = parse_harness_output(output)
        elapsed = int(time.time() - t_start)

        if result is None:
            # No parseable output — check if fixes were applied via git
            if git_diff_has_changes(project_root):
                print(f"{PREFIX} No JSON output but git shows changes — proceeding to test")
                if output and len(output) < 50:
                    print(f"{PREFIX}   Hint: session output was very short — may have hit max-turns limit")
                elif not output:
                    print(f"{PREFIX}   Hint: session produced no output (likely timed out)")
                # Can't do per-fix bisection without pre/post content
                # Run tests on the whole batch
                test_ok, test_summary = run_tests(test_command, project_root)
                if test_ok:
                    progress["test_results"]["last_full_run"] = "pass"
                    progress["test_results"]["last_run_output_summary"] = test_summary
                    # Changes passed tests but are untracked — stop to avoid silent drift
                    result = {
                        "no_new_findings": False,
                        "no_actionable_fixes": True,
                        "fixes_applied": [],
                        "new_findings": [],
                    }
                else:
                    print(f"{PREFIX} Tests failed with unparseable output — reverting iteration")
                    if test_summary:
                        for line in test_summary.split("\n"):
                            print(f"{PREFIX}   {line}")
                    if pre_snapshot:
                        if not git_restore_snapshot(pre_snapshot, project_root):
                            git_restore_to(pre_hash, project_root)
                    else:
                        git_restore_to(pre_hash, project_root)
                    progress["test_results"]["last_full_run"] = "fail"
                    progress["test_results"]["last_run_output_summary"] = test_summary
                    progress["termination"] = {
                        "reason": "parse-failure",
                        "message": "Could not parse skill output and tests failed",
                    }
                    write_progress(progress_path, progress)
                    print_report(progress)
                    sys.exit(1)
            else:
                print(f"{PREFIX} No output and no changes — treating as convergence")
                result = {
                    "no_new_findings": True,
                    "no_actionable_fixes": False,
                    "fixes_applied": [],
                    "new_findings": [],
                }

        # Report iteration output
        new_count = len(result.get("new_findings", []))
        applied_count = len(result.get("fixes_applied", []))
        print(
            f"{PREFIX} Skill session complete — "
            f"{new_count} new findings, {applied_count} fixes applied ({elapsed}s)"
        )

        # Check convergence
        if result.get("no_new_findings", False):
            handle_safe_exit(
                progress, progress_path, args,
                reason="convergence",
                message=f"Zero new findings on iteration {iteration}",
                log_message="Convergence",
                new_count=0,
                pre_snapshot=pre_snapshot, pre_hash=pre_hash,
            )
            print(f"{PREFIX} Converged: no new findings.")
            break

        # Check no actionable fixes
        if result.get("no_actionable_fixes", False):
            handle_safe_exit(
                progress, progress_path, args,
                reason="no-actionable",
                message="Findings exist but none had actionable code edits",
                log_message="No actionable fixes",
                new_count=new_count,
                pre_snapshot=pre_snapshot, pre_hash=pre_hash,
            )
            print(f"{PREFIX} No actionable fixes — remaining findings need manual review.")
            break

        # Merge new findings into progress
        fixes = result.get("fixes_applied", [])
        applied_keys = {(f.get("file"), f.get("line"), f.get("category")) for f in fixes}
        for fix in fixes:
            mark_finding_status(progress, fix, "applied-pending-test", None)
        # Also record discovered-but-not-applied findings (prevents re-reporting)
        for nf in result.get("new_findings", []):
            key = (nf.get("file"), nf.get("line"), nf.get("category"))
            if key not in applied_keys:
                mark_finding_status(progress, nf, "discovered", None)

        # Run tests (HARNESS-SIDE)
        if fixes:
            test_ok, test_summary = run_tests(test_command, project_root)
            progress["test_results"]["last_full_run"] = "pass" if test_ok else "fail"
            progress["test_results"]["last_run_output_summary"] = test_summary

            if test_ok:
                # All fixes passed
                mark_all_fixed(progress, fixes)
                fixed_count = len(fixes)
                reverted_count = 0
                all_reverted = False
                print(f"{PREFIX} Results: {fixed_count} fixed, 0 reverted")
            else:
                # Bisect: revert all, re-apply one-by-one
                fixed_count, reverted_count = bisect_fixes(
                    fixes, test_command, project_root, progress
                )
                print(
                    f"{PREFIX} Results: {fixed_count} fixed, "
                    f"{reverted_count} reverted (bisection)"
                )

                # Update test status after bisection
                if fixed_count > 0:
                    test_ok, test_summary = run_tests(test_command, project_root)
                    progress["test_results"]["last_full_run"] = "pass" if test_ok else "fail"
                    progress["test_results"]["last_run_output_summary"] = test_summary
                    if not test_ok:
                        print(f"{PREFIX} WARNING: Combined fixes fail tests — interaction bug, reverting all")
                        if pre_snapshot:
                            if not git_restore_snapshot(pre_snapshot, project_root):
                                git_restore_to(pre_hash, project_root)
                        else:
                            git_restore_to(pre_hash, project_root)
                        # Re-mark fixes that bisection had marked as "fixed" —
                        # already-reverted ones retain their original status.
                        interaction_reverted = 0
                        for fix in fixes:
                            for f in progress["findings"]:
                                if (f["file"] == fix.get("file")
                                        and f.get("line") == fix.get("line")
                                        and f.get("category") == fix.get("category")
                                        and f.get("status") in ("fixed", "retained — revert failed")):
                                    mark_finding_status(progress, fix,
                                                        "reverted — test failure",
                                                        "Interaction bug — combined fixes failed")
                                    interaction_reverted += 1
                                    break
                        reverted_count += interaction_reverted
                        fixed_count -= interaction_reverted

                # Check all-reverted
                all_reverted = fixed_count == 0 and reverted_count > 0
        else:
            fixed_count = 0
            reverted_count = 0
            test_ok = True
            all_reverted = False

        # Record iteration history
        persistent_count = sum(
            1
            for f in progress["findings"]
            if f["status"] == "persistent — fix failed"
            and f.get("iteration_last_attempted") == iteration
        )
        hist_entry = {
            "iteration": iteration,
            "new_findings": new_count,
            "fixed": fixed_count,
            "reverted": reverted_count,
            "persistent": persistent_count,
            "test_passed": test_ok,
        }
        progress["iteration_history"].append(hist_entry)
        progress["iteration"]["completed"] = iteration

        if all_reverted:
            progress["termination"] = {
                "reason": "all-reverted",
                "message": f"All {reverted_count} fixes in iteration {iteration} caused test failures",
            }
            write_progress(progress_path, progress)
            print(f"{PREFIX} All fixes reverted — stopping.")
            break

        # Update scope for next iteration
        update_scope(progress, result)

        # Checkpoint commit (skip if post-bisection tests failed — interaction bug)
        if not args.no_commit and test_ok and (fixed_count > 0 or git_diff_has_changes(project_root)):
            if git_commit_checkpoint(progress, iteration, project_root):
                print(f"{PREFIX} Checkpoint: deep-harness({args.skill}): iteration {iteration}")
            else:
                print(f"{PREFIX} WARNING: Checkpoint failed — switching to --no-commit for remaining iterations")
                args.no_commit = True

        # Check iteration cap
        if iteration >= max_iter:
            progress["termination"] = {
                "reason": "cap",
                "message": f"Reached iteration cap ({max_iter})",
            }
            write_progress(progress_path, progress)
            print(f"{PREFIX} Iteration cap reached ({max_iter}).")
            break

        # Next iteration
        progress["iteration"]["current"] += 1
        write_progress(progress_path, progress)


if __name__ == "__main__":
    main()
