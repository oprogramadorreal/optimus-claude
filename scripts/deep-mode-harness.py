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
  python scripts/deep-mode-harness.py --skill code-review
  python scripts/deep-mode-harness.py --skill code-review --scope "src/auth"
  python scripts/deep-mode-harness.py --skill refactor --max-iterations 8 --scope "src/api"
  python scripts/deep-mode-harness.py --skill code-review --resume

Security: Each claude -p session runs with --dangerously-skip-permissions because the
harness is headless — there is no terminal to approve tool permission prompts. This
bypasses allow/deny lists and PreToolUse hooks (including /optimus:permissions).
For safer operation, use Claude Code's built-in sandboxing (macOS/Linux) or
devcontainers, which provide OS-level isolation even with --dangerously-skip-permissions.

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

DEFAULT_MAX_ITERATIONS = 5
MAX_ITERATIONS_HARD_CAP = 20
DEFAULT_MAX_TURNS = 30
SESSION_TIMEOUT = 600  # 10 minutes per iteration
PROGRESS_FILE_NAME = "deep-mode-progress.json"
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
            "project_root": str(project_root),
            "base_commit": base_commit,
        },
        "iteration": {"current": 1, "completed": 0},
        "findings": [],
        "scope_files": {"current": [], "newly_modified_this_iteration": []},
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
    working tree, index, or stash reflog.
    """
    result = subprocess.run(
        ["git", "stash", "create", "--include-untracked"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    sha = result.stdout.strip()
    return sha if sha else None


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


def git_commit_checkpoint(progress, iteration, cwd):
    """Create a checkpoint commit for this iteration."""
    skill = progress["skill"]
    hist = progress["iteration_history"]
    latest = hist[-1] if hist else {}
    fixed = latest.get("fixed", 0)
    reverted = latest.get("reverted", 0)

    msg = (
        f"deep-mode({skill}): iteration {iteration} — "
        f"{fixed} fixed, {reverted} reverted"
    )

    add_result = subprocess.run(
        ["git", "add", "-A"], cwd=str(cwd), capture_output=True, text=True
    )
    if add_result.returncode != 0:
        print(f"{PREFIX} WARNING: git add -A failed: {add_result.stderr[:200]}")
        return
    result = subprocess.run(
        ["git", "commit", "-m", msg, "--allow-empty"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{PREFIX} WARNING: checkpoint commit failed: {result.stderr[:200]}")


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def write_progress(path, progress):
    """Write the progress file with a backup."""
    path = Path(path)
    if path.exists():
        shutil.copy2(str(path), str(path) + BACKUP_SUFFIX)
    path.write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")


def read_progress(path):
    """Read the progress file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test execution (harness-side)
# ---------------------------------------------------------------------------


def run_tests(test_command, cwd):
    """Run the project's test command. Returns (passed: bool, output: str)."""
    print(f"{PREFIX} Running tests: {test_command}")
    try:
        result = subprocess.run(
            test_command,
            shell=True,
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
    filepath = (Path(cwd) / fix["file"]).resolve()
    if not _is_path_within(filepath, Path(cwd).resolve()):
        return False
    if not filepath.exists():
        return False
    content = filepath.read_text(encoding="utf-8")
    find = fix.get(find_key, "")
    replace = fix.get(replace_key, "")
    if not find or find not in content:
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
            mark_finding_status(progress, fix, "fixed",
                                "Revert failed during bisection — fix retained")
            fixed_count += 1
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
                                "Could not mechanically re-apply fix" if i not in revert_failures
                                else "Test failure during bisection")
            reverted_count += 1

    return fixed_count, reverted_count


# ---------------------------------------------------------------------------
# Finding status management
# ---------------------------------------------------------------------------


def mark_finding_status(progress, fix, status, detail):
    """Update a finding's status in the progress file."""
    # Try to find existing finding by file+line+category match
    for f in progress["findings"]:
        if (f["file"] == fix["file"] and f.get("line") == fix.get("line")
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
    progress_path = str(resolved_progress_path)

    # Build the skill invocation prompt
    if skill == "code-review":
        prompt = "/optimus:code-review deep"
    elif skill == "refactor":
        prompt = f"/optimus:refactor deep {max_iter}"
    else:
        raise ValueError(f"Unsupported skill: {skill}")

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
        "--dangerously-skip-permissions",
        "--max-turns",
        str(args.max_turns),
        "--output-format",
        "json",
    ]

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
    total_fixed = sum(1 for f in findings if f["status"] == "fixed")
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
    print(
        f"{PREFIX} To squash checkpoint commits: git rebase -i {base[:8]}"
    )
    print(
        f"{PREFIX} To rollback everything:       git reset --hard {base[:8]}"
    )
    print(f"{PREFIX}")
    print(f"{PREFIX} Next: run /optimus:commit to commit the fixes.")
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
            return match.group(1).strip()

    return None


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
    claude_check = subprocess.run(
        ["claude", "--version"], capture_output=True, text=True
    )
    if claude_check.returncode != 0:
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
        saved_root = Path(progress["config"].get("project_root", "")).resolve()
        if saved_root != project_root:
            print(
                f"{PREFIX} ERROR: Progress file project_root '{saved_root}' "
                f"does not match --project-dir '{project_root}'"
            )
            sys.exit(1)
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

    # Print startup info
    max_iter = progress["config"]["max_iterations"]
    # 7 agents for code-review, 4 for refactor; +1 per iteration for harness overhead
    estimated_messages = max_iter * (7 if args.skill == "code-review" else 4) + max_iter
    print(f"{PREFIX} Starting {args.skill} harness (max {max_iter} iterations)")
    print(f"{PREFIX} Test command: {test_command}")
    print(f"{PREFIX} Base commit: {progress['config']['base_commit'][:8]}")
    print(f"{PREFIX} Estimated messages: ~{estimated_messages} (check rate limits)")
    print(f"{PREFIX}")

    # Main iteration loop
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
                print(f"{PREFIX} Session error: {e}")
                if pre_snapshot:
                    git_restore_snapshot(pre_snapshot, project_root)
                else:
                    git_restore_to(pre_hash, project_root)
                if attempt == 0:
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
                    if pre_snapshot:
                        git_restore_snapshot(pre_snapshot, project_root)
                    else:
                        git_restore_to(pre_hash, project_root)
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
            # Safety check: if skill unexpectedly left changes, verify tests
            conv_test_passed = True
            if git_diff_has_changes(project_root):
                print(f"{PREFIX} Convergence but working tree has changes — verifying tests")
                conv_ok, conv_summary = run_tests(test_command, project_root)
                conv_test_passed = conv_ok
                progress["test_results"]["last_full_run"] = "pass" if conv_ok else "fail"
                progress["test_results"]["last_run_output_summary"] = conv_summary
                if not conv_ok:
                    print(f"{PREFIX} Tests failed on convergence — reverting unexpected changes")
                    if pre_snapshot:
                        git_restore_snapshot(pre_snapshot, project_root)
                    else:
                        git_restore_to(pre_hash, project_root)
            progress["termination"] = {
                "reason": "convergence",
                "message": f"Zero new findings on iteration {iteration}",
            }
            progress["iteration"]["completed"] = iteration
            progress["iteration_history"].append({
                "iteration": iteration,
                "new_findings": 0,
                "fixed": 0,
                "reverted": 0,
                "persistent": 0,
                "test_passed": conv_test_passed,
            })
            write_progress(progress_path, progress)
            if not args.no_commit and conv_test_passed and git_diff_has_changes(project_root):
                git_commit_checkpoint(progress, iteration, project_root)
            print(f"{PREFIX} Converged: no new findings.")
            break

        # Check no actionable fixes
        if result.get("no_actionable_fixes", False):
            # Safety check: if skill unexpectedly left changes, verify tests
            noact_test_passed = True
            if git_diff_has_changes(project_root):
                print(f"{PREFIX} No actionable fixes but working tree has changes — verifying tests")
                noact_ok, noact_summary = run_tests(test_command, project_root)
                noact_test_passed = noact_ok
                progress["test_results"]["last_full_run"] = "pass" if noact_ok else "fail"
                progress["test_results"]["last_run_output_summary"] = noact_summary
                if not noact_ok:
                    print(f"{PREFIX} Tests failed — reverting unexpected changes")
                    if pre_snapshot:
                        git_restore_snapshot(pre_snapshot, project_root)
                    else:
                        git_restore_to(pre_hash, project_root)
            progress["termination"] = {
                "reason": "no-actionable",
                "message": "Findings exist but none had actionable code edits",
            }
            progress["iteration"]["completed"] = iteration
            progress["iteration_history"].append({
                "iteration": iteration,
                "new_findings": new_count,
                "fixed": 0,
                "reverted": 0,
                "persistent": 0,
                "test_passed": noact_test_passed,
            })
            write_progress(progress_path, progress)
            if not args.no_commit and noact_test_passed and git_diff_has_changes(project_root):
                git_commit_checkpoint(progress, iteration, project_root)
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
                            git_restore_snapshot(pre_snapshot, project_root)
                        else:
                            git_restore_to(pre_hash, project_root)
                        # Only re-mark fixes that bisection had marked as "fixed" —
                        # already-reverted ones retain their original status
                        interaction_reverted = 0
                        for fix in fixes:
                            for f in progress["findings"]:
                                if (f["file"] == fix.get("file")
                                        and f.get("line") == fix.get("line")
                                        and f.get("category") == fix.get("category")
                                        and f.get("status") == "fixed"):
                                    mark_finding_status(progress, fix, "reverted — test failure",
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
            git_commit_checkpoint(progress, iteration, project_root)
            print(f"{PREFIX} Checkpoint: deep-mode({args.skill}): iteration {iteration}")

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

    # Final report
    print_report(progress)

    # Archive progress file on convergence (leave it for other termination types)
    if progress["termination"]["reason"] == "convergence":
        done_path = progress_path.with_suffix(".done.json")
        shutil.move(str(progress_path), str(done_path))
        backup = Path(str(progress_path) + BACKUP_SUFFIX)
        backup.unlink(missing_ok=True)
        print(f"{PREFIX} Progress archived to {done_path.name}")


if __name__ == "__main__":
    main()
