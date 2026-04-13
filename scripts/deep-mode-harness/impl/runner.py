import subprocess

# Import shared run_tests and wrap to inject deep-mode prefix
from harness_common.digest import build_iteration_coaching, build_progress_digest
from harness_common.runner import build_claude_session_cmd
from harness_common.runner import run_tests as _shared_run_tests

from .constants import DEFAULT_TEST_TIMEOUT, PREFIX, VALID_FOCUS_MODES, normalize_path


def run_tests(test_command, cwd, timeout=DEFAULT_TEST_TIMEOUT):
    """Run the project's test command. Returns (passed: bool, output: str)."""
    return _shared_run_tests(test_command, cwd, timeout=timeout, prefix=PREFIX)


def _build_prompt(skill, max_iterations, scope_paths, focus=""):
    """Build the skill invocation prompt string."""
    prompt = (
        "/optimus:code-review deep"
        if skill == "code-review"
        else f"/optimus:refactor deep {max_iterations}"
    )
    # Focus modes only apply to refactor — code-review has no finding-cap priority
    if focus and skill != "code-review":
        if focus not in VALID_FOCUS_MODES:
            raise ValueError(f"Invalid focus mode: {focus!r}")
        prompt += f" {focus}"
    if scope_paths:
        paths_str = ", ".join(scope_paths[:20])
        prompt += f' "focus on: {paths_str}"'
    return prompt


def _build_harness_system(progress_path, iteration, max_iterations, progress=None):
    """Build the harness-mode system prompt injected into the claude session."""
    base = (
        f"HARNESS_MODE_ACTIVE: You are running inside the deep-mode harness. "
        f"Progress file: {progress_path}\n"
        f"This is iteration {iteration} of {max_iterations}. "
        f"Do NOT use AskUserQuestion. Do NOT loop. Do NOT run tests. "
        f"Read the progress file for accumulated findings and scope. "
        f"After applying fixes, output structured JSON in a "
        f"```json:harness-output block and stop."
    )
    if progress is not None:
        digest = build_progress_digest(progress, iteration)
        coaching = build_iteration_coaching(progress, iteration)
        base += f"\n\n--- Progress Digest ---\n{digest}\n\n--- Guidance ---\n{coaching}"
    return base


def run_skill_session(progress, args, resolved_progress_path, _run=subprocess.run):
    """
    Launch a fresh claude -p session for one iteration.
    Returns the raw stdout output.
    """
    iteration = progress["iteration"]["current"]
    max_iterations = progress["config"]["max_iterations"]
    # Use forward slashes for cross-platform compatibility in system prompt
    progress_path = normalize_path(str(resolved_progress_path))

    prompt = _build_prompt(
        progress["skill"],
        max_iterations,
        progress["scope_files"]["current"],
        focus=progress["config"].get("focus", ""),
    )
    harness_system = _build_harness_system(
        progress_path, iteration, max_iterations, progress
    )
    cmd = build_claude_session_cmd(
        prompt, harness_system, args.allowed_tools, args.max_turns
    )

    if args.verbose:
        print(f"{PREFIX} Command: {' '.join(cmd[:6])}...")

    result = _run(
        cmd,
        capture_output=True,
        text=True,
        cwd=progress["config"]["project_root"],
        timeout=args.timeout,
    )

    if args.verbose:
        print(f"{PREFIX} Exit code: {result.returncode}")
        if result.stderr:
            print(f"{PREFIX} Stderr: {result.stderr[:500]}")

    # claude exit codes: 0=success, 1=partial/warning, >1=fatal
    if result.returncode > 1:
        raise RuntimeError(
            f"claude exited with code {result.returncode}: {result.stderr[:200]}"
        )
    if result.returncode == 1:
        print(
            f"{PREFIX} WARNING: claude exited with code 1 (may indicate partial failure): {result.stderr[:200]}"
        )

    return result.stdout
