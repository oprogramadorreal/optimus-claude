"""Pins the orchestrator ↔ base-skill ↔ CLI wiring contract.

These tests catch silent breakages that the unit-level CLI tests miss: a base
SKILL.md losing its `HARNESS_MODE_INLINE` router, the /optimus:deep orchestrator
stopping pointing at the loop reference, the harness-mode.md JSON schema
drifting from what `cli.py parse` actually accepts. Each assertion below
encodes one rung of the dispatch chain.

If one of these fails, the in-conversation deep-mode flow is silently broken —
the unit tests will pass but a real `/optimus:deep` invocation will either hang
the subagent or terminate the loop on the first iteration.
"""

import json
from pathlib import Path

import pytest
from harness_common import cli

PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path):
    return (PLUGIN_ROOT / rel_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Base SKILL.md must route HARNESS_MODE_INLINE to the right reference
# ---------------------------------------------------------------------------


BASE_SKILL_ROUTES = [
    # (base_skill, harness_reference)
    ("code-review", "references/harness-mode.md"),
    ("refactor", "references/harness-mode.md"),
    ("unit-test", "references/coverage-harness-mode.md"),
]


@pytest.mark.parametrize("base_skill,harness_ref", BASE_SKILL_ROUTES)
def test_base_skill_routes_harness_mode_inline(base_skill, harness_ref):
    """Each base SKILL.md must detect HARNESS_MODE_INLINE and route to the right reference.

    The orchestrator's subagent prompt injects `HARNESS_MODE_INLINE` and tells
    the subagent to read the base SKILL.md and execute its harness-mode
    protocol. If the SKILL.md's router goes away, the subagent runs interactive
    mode and hangs.
    """
    skill_md = _read(f"skills/{base_skill}/SKILL.md")
    assert (
        "HARNESS_MODE_INLINE" in skill_md
    ), f"skills/{base_skill}/SKILL.md must contain HARNESS_MODE_INLINE detection"
    assert (
        harness_ref in skill_md
    ), f"skills/{base_skill}/SKILL.md must route to {harness_ref}"


# ---------------------------------------------------------------------------
# The /optimus:deep orchestrator must reference the loop template + base skills
# ---------------------------------------------------------------------------


DEEP_SKILL = "skills/deep/SKILL.md"


def test_orchestrator_references_loop_template_and_base_skills():
    skill_md = _read(DEEP_SKILL)
    assert (
        "references/orchestrator-loop.md" in skill_md
    ), f"{DEEP_SKILL} must reference references/orchestrator-loop.md"
    for base in (
        "skills/code-review/SKILL.md",
        "skills/refactor/SKILL.md",
        "skills/unit-test/SKILL.md",
    ):
        assert base in skill_md, f"{DEEP_SKILL} must name its base skill {base}"


def test_orchestrator_disables_model_invocation():
    """The orchestrator must not be reachable via slash-command dispatch from a subagent.

    `disable-model-invocation: true` prevents recursive deep-mode runs (a
    subagent cannot accidentally invoke its own orchestrator via slash). The
    re-entry guard inside the SKILL.md is the second line of defense.
    """
    skill_md = _read(DEEP_SKILL)
    assert (
        "disable-model-invocation: true" in skill_md
    ), f"{DEEP_SKILL} must set disable-model-invocation: true"


def test_orchestrator_has_reentry_guard():
    skill_md = _read(DEEP_SKILL)
    assert (
        "Re-entry guard" in skill_md
    ), f"{DEEP_SKILL} must have a Re-entry guard step"
    # The guard's payload — looking for HARNESS_MODE_INLINE as the marker.
    assert "HARNESS_MODE_INLINE" in skill_md


def test_orchestrator_resolves_plugin_root():
    """The orchestrator must carry its own plugin-root resolution subsection.

    The resolution cannot live in a shared reference — reading that reference
    would itself need the very root it resolves.
    """
    skill_md = _read(DEEP_SKILL)
    assert (
        "### Plugin root" in skill_md
    ), f"{DEEP_SKILL} must carry a '### Plugin root' resolution subsection"


def test_orchestrator_passes_test_command_and_runs_baseline():
    """The orchestrator must pass --test-command to init and run the baseline gate.

    The CLI requires an explicit test command; passing the command the skill
    already captured avoids a spurious init failure. The baseline run
    establishes a green starting tree and calibrates the per-run test timeout
    before the loop starts.
    """
    skill_md = _read(DEEP_SKILL)
    assert (
        "--test-command" in skill_md
    ), f"{DEEP_SKILL} must pass --test-command to init"
    assert (
        "cli baseline" in skill_md
    ), f"{DEEP_SKILL} must run the baseline gate before the loop"


# ---------------------------------------------------------------------------
# The loop reference must inject HARNESS_MODE_INLINE and read base SKILL.md
# ---------------------------------------------------------------------------


LOOP_REF = "references/orchestrator-loop.md"


def test_loop_reference_dispatches_via_skill_md_read():
    """The loop ref must tell the subagent to read SKILL.md, not /optimus:slash-dispatch.

    The base SKILL.md files all carry `disable-model-invocation: true`, so a
    subagent prompt of `/optimus:code-review …` is not guaranteed to route.
    The orchestrator works around this by instructing the subagent to read
    the SKILL.md from disk and follow its harness-mode protocol.
    """
    ref = _read(LOOP_REF)
    assert (
        "HARNESS_MODE_INLINE" in ref
    ), f"{LOOP_REF} must inject HARNESS_MODE_INLINE in dispatch prompts"
    for path in (
        "skills/<base-skill>/SKILL.md",
        "references/harness-mode.md",
        "skills/unit-test/SKILL.md",
        "skills/refactor/SKILL.md",
        "references/coverage-harness-mode.md",
    ):
        assert path in ref, f"{LOOP_REF} must reference {path}"
    # Pin the dispatch *mechanism*, not just the path token. A future loop-ref
    # edit could keep the SKILL.md path string while dropping the "read from
    # disk" instruction in favour of an alternative (slash command, cache).
    assert (
        "Read the base SKILL.md" in ref
    ), f"{LOOP_REF} must instruct the subagent to read the base SKILL.md from disk"


# ---------------------------------------------------------------------------
# harness-mode.md JSON schema must parse via cli.py parse
# ---------------------------------------------------------------------------


def test_harness_mode_documented_schema_round_trips_through_cli_parse(tmp_path, capsys):
    """The JSON shape documented in references/harness-mode.md must parse via cli.py parse.

    Without this test, a docs edit that renames `no_new_findings` or `pre_edit_content`
    can leave the parser silently rejecting every subagent's output for some non-obvious
    reason — the orchestrator just terminates with parse-failure on every run.
    """
    # Construct a payload that exercises every field documented in
    # harness-mode.md step 8.
    payload = {
        "iteration": 3,
        "new_findings": [
            {
                "file": "src/app.js",
                "line": 42,
                "end_line": 42,
                "category": "bug",
                "guideline": "General: avoid null dereference",
                "summary": "Add null check before accessing property",
                "fix_description": "Added null guard",
                "severity": "Critical",
                "confidence": "High",
                "agent": "bug-detector",
                "pre_edit_content": "obj.value",
                "post_edit_content": "obj?.value",
            }
        ],
        "fixes_applied": [
            {
                "file": "src/app.js",
                "line": 42,
                "end_line": 42,
                "category": "bug",
                "guideline": "General: avoid null dereference",
                "summary": "Add null check before accessing property",
                "fix_description": "Added null guard",
                "severity": "Critical",
                "confidence": "High",
                "agent": "bug-detector",
                "pre_edit_content": "obj.value",
                "post_edit_content": "obj?.value",
            }
        ],
        "fixes_skipped_persistent": [],
        "no_new_findings": False,
        "no_actionable_fixes": False,
    }
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "preamble text\n"
        "```json:harness-output\n" + json.dumps(payload, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    exit_code = cli.main(["parse", "--input-file", str(raw)])
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    # Each top-level field documented in harness-mode.md must survive parsing.
    assert parsed["iteration"] == 3
    assert parsed["new_findings"][0]["pre_edit_content"] == "obj.value"
    assert parsed["fixes_applied"][0]["post_edit_content"] == "obj?.value"
    assert parsed["no_new_findings"] is False
    assert parsed["no_actionable_fixes"] is False


def test_orchestrator_documents_yes_and_resume_flags():
    """The orchestrator SKILL.md must document the --yes and --resume flags.

    --yes is the headless / CI entry point: if a future SKILL.md edit silently
    drops it, `claude -p "/optimus:deep …"` will hang on the confirmation
    AskUserQuestion with no test failure to flag the regression. --resume is
    the crash-recovery contract.
    """
    skill_md = _read(DEEP_SKILL)
    assert "`--yes`" in skill_md, f"{DEEP_SKILL} must document the --yes flag"
    assert "`--resume`" in skill_md, f"{DEEP_SKILL} must document the --resume flag"


def test_harness_mode_documents_all_termination_reasons():
    """The orchestrator dispatches to harness-mode.md for termination semantics.

    harness-mode.md's "Termination reasons" section must enumerate every reason
    cli.py's check-termination can emit — otherwise the docs lie about what
    the orchestrator might see.
    """
    ref = _read("references/harness-mode.md")
    for reason in (
        "convergence",
        "no-actionable",
        "all-reverted",
        "diminishing-returns",
        "cap",
        "parse-failure",
    ):
        assert (
            f"`{reason}`" in ref
        ), f"references/harness-mode.md must document termination reason '{reason}'"


def test_paired_loop_resnapshots_before_refactor_phase():
    """The paired loop must re-snapshot after the unit-test phase, before the
    refactor dispatch.

    The step-1 snapshot predates the unit tests written during the cycle; a
    refactor-phase combined-regression restore against that stale snapshot would
    discard them. The loop guards this by re-running `snapshot` between the
    unit-test commit and the refactor dispatch — pin it so the guard cannot
    silently regress.
    """
    ref = _read(LOOP_REF)
    _, _, refactor_region = ref.partition("Conditionally dispatch the refactor phase")
    assert refactor_region, "paired loop must have a refactor-phase dispatch step"
    assert "cli snapshot" in refactor_region, (
        "orchestrator-loop.md must re-snapshot before dispatching the "
        "refactor subagent so a refactor rollback does not discard the cycle's "
        "unit tests"
    )
