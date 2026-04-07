import subprocess

from harness_common.constants import DEFAULT_TEST_TIMEOUT, normalize_path
from harness_common.runner import run_tests as _shared_run_tests

from .constants import DEFAULT_SESSION_TIMEOUT, PREFIX


def run_tests(test_command, cwd, timeout=DEFAULT_TEST_TIMEOUT):
    """Run the project's test command. Returns (passed: bool, output: str).

    Defaults to the per-test-run timeout (DEFAULT_TEST_TIMEOUT), not the
    much-longer per-session timeout. The session timeout governs the
    claude -p call, not pytest invocations.
    """
    return _shared_run_tests(test_command, cwd, timeout=timeout, prefix=PREFIX)


def _build_unit_test_prompt(max_cycles, scope):
    """Build the unit-test skill invocation prompt."""
    # Omit "harness" keyword — HARNESS_MODE_ACTIVE is injected via --append-system-prompt,
    # which triggers the harness code path in the skill's Step 1 detection.
    prompt = f"/optimus:unit-test deep {max_cycles}"
    if scope:
        prompt += f' "{scope}"'
    return prompt


def _build_refactor_prompt(max_cycles, untestable_items):
    """Build the refactor skill invocation prompt scoped to untestable code."""
    prompt = f"/optimus:refactor deep {max_cycles} testability"
    if untestable_items:
        # Build scope from untestable code files
        files = sorted(
            set(item.get("file", "") for item in untestable_items if item.get("file"))
        )
        if files:
            paths_str = ", ".join(files[:20])
            prompt += f' "focus on: {paths_str}"'
    return prompt


def _build_harness_system(progress_path, cycle, max_cycles, phase):
    """Build the harness-mode system prompt for the coverage harness."""
    return (
        f"HARNESS_MODE_ACTIVE: You are running inside the test-coverage harness. "
        f"Progress file: {progress_path}\n"
        f"This is cycle {cycle} of {max_cycles}, phase: {phase}. "
        f"Do NOT use AskUserQuestion. Do NOT loop. "
        + (
            "Do NOT run tests. "
            "Read the progress file for untestable code items to address. "
            "Focus exclusively on testability barriers. "
            if phase == "refactor"
            else "Read the progress file for prior coverage data and untestable code items. "
            "Write tests, measure coverage, report untestable code. "
        )
        + "Output structured JSON in a ```json:harness-output block and stop."
    )


def _build_cmd(prompt, harness_system, allowed_tools, max_turns):
    """Assemble the claude CLI argument list."""
    cmd = [
        "claude",
        "-p",
        prompt,
        "--append-system-prompt",
        harness_system,
    ]
    if allowed_tools:
        cmd.extend(["--allowedTools", allowed_tools])
    else:
        cmd.append("--dangerously-skip-permissions")
    cmd.extend(
        [
            "--max-turns",
            str(max_turns),
            "--output-format",
            "json",
        ]
    )
    return cmd


def run_coverage_session(
    progress, args, resolved_progress_path, phase, _run=subprocess.run
):
    """
    Launch a fresh claude -p session for one phase of a cycle.
    Returns the raw stdout output.
    """
    cycle = progress["cycle"]["current"]
    max_cycles = progress["config"]["max_cycles"]
    progress_path = normalize_path(str(resolved_progress_path))

    if phase == "unit-test":
        prompt = _build_unit_test_prompt(max_cycles, progress["config"]["scope"])
    else:
        prompt = _build_refactor_prompt(max_cycles, progress.get("untestable_code", []))

    harness_system = _build_harness_system(progress_path, cycle, max_cycles, phase)
    cmd = _build_cmd(prompt, harness_system, args.allowed_tools, args.max_turns)

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
