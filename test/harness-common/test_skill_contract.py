"""Pins the orchestrator ↔ base-skill ↔ CLI wiring contract.

These tests catch silent breakages that the unit-level CLI tests miss: a base
SKILL.md losing its `HARNESS_MODE_INLINE` router, the deep orchestrator
stopping pointing at a loop reference, the harness-mode.md JSON schema
drifting from what `cli.py parse` actually accepts. Each assertion below
encodes one rung of the dispatch chain.

If one of these fails, the in-conversation deep-mode flow is silently broken —
the unit tests will pass but a real `/optimus:deep` invocation will either
hang the subagent or terminate the loop on the first iteration.
"""

import json
from pathlib import Path

import pytest
from harness_common import cli

PLUGIN_ROOT = Path(__file__).resolve().parents[2]

DEEP_SKILL = "skills/deep/SKILL.md"


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
# The deep orchestrator must wire all three targets to the CLI and loop refs
# ---------------------------------------------------------------------------


TARGET_LOOP_REFS = [
    # (target, the loop reference its Targets-table row must name)
    ("review", "references/orchestrator-loop-single.md"),
    ("refactor", "references/orchestrator-loop-single.md"),
    ("coverage", "references/orchestrator-loop-paired.md"),
]


def _targets_table_row(skill_md, target):
    """Return the Targets-table row for `target`, or None if absent."""
    for line in skill_md.splitlines():
        if line.startswith(f"| `{target}` |"):
            return line
    return None


def _section(skill_md, heading):
    """Return the body under `heading`, up to the next same-or-higher heading.

    Assertions about one section must be scoped to it: a whole-file substring
    check passes on an incidental mention elsewhere in the document.
    """
    start = skill_md.find(heading)
    if start == -1:
        return ""
    rest = skill_md[start + len(heading) :]
    ends = [i for i in (rest.find("\n### "), rest.find("\n## ")) if i != -1]
    return rest[: min(ends)] if ends else rest


def test_deep_references_harness_init_resume():
    skill_md = _read(DEEP_SKILL)
    assert (
        "references/harness-init-resume.md" in skill_md
    ), f"{DEEP_SKILL} must reference references/harness-init-resume.md"


@pytest.mark.parametrize("target,loop_ref", TARGET_LOOP_REFS)
def test_deep_pins_loop_reference_per_target(target, loop_ref):
    """Each target must be wired to its own loop reference.

    Asserting only that both loop filenames appear somewhere in the file lets a
    target be rewired to the wrong loop with the whole suite green: `coverage`
    on the single loop silently loses its paired unit-test+refactor cycle and
    its re-snapshot guard. Pin the mapping at the Targets-table row instead.
    """
    skill_md = _read(DEEP_SKILL)
    row = _targets_table_row(skill_md, target)
    assert row is not None, f"{DEEP_SKILL} Targets table must have a `{target}` row"
    assert loop_ref in row, f"{DEEP_SKILL} target `{target}` must use {loop_ref}"
    wrong_ref = (
        "references/orchestrator-loop-paired.md"
        if "loop-single" in loop_ref
        else "references/orchestrator-loop-single.md"
    )
    assert (
        wrong_ref not in row
    ), f"{DEEP_SKILL} target `{target}` must not also name {wrong_ref}"


def test_deep_pins_progress_file_paths():
    """The per-target progress files are CLI defaults and git.py glob anchors.

    Renaming them silently escapes the `.claude/*-deep-progress.json` un-stage
    and cleanup globs, so the orchestrator must name them exactly. Sourced from
    cli.DEFAULT_PROGRESS_FILES rather than frozen literals: with a private copy
    the CLI could be renamed to a path the orchestrator never names and this
    test would still pass, which is the exact drift it exists to catch.
    """
    skill_md = _read(DEEP_SKILL)
    assert cli.DEFAULT_PROGRESS_FILES, "CLI must define default progress paths"
    for base_skill, progress in cli.DEFAULT_PROGRESS_FILES.items():
        assert (
            progress in skill_md
        ), f"{DEEP_SKILL} must pin progress file {progress} (--skill {base_skill})"


def test_deep_disables_model_invocation():
    """The orchestrator must not be reachable via slash-command dispatch from a
    subagent — `disable-model-invocation: true` prevents recursive deep-mode
    runs; the re-entry guard inside the SKILL.md is the second line of defense.
    """
    skill_md = _read(DEEP_SKILL)
    assert "disable-model-invocation: true" in skill_md


def test_deep_has_reentry_guard():
    skill_md = _read(DEEP_SKILL)
    assert "Re-entry guard" in skill_md, f"{DEEP_SKILL} must have a Re-entry guard step"
    assert "HARNESS_MODE_INLINE" in skill_md


def test_deep_has_plugin_root_resolution():
    """The plugin-root resolution cannot live in a shared reference — reading
    that reference would itself need the very root it resolves — so the deep
    SKILL.md must carry it inline and validate the candidate root by locating
    scripts/harness_common.
    """
    skill_md = _read(DEEP_SKILL)
    assert "### Plugin root" in skill_md
    # Scoped to the section: asserting against the whole file would pass on any
    # incidental "scripts/harness_common" mention (every CLI invocation carries
    # one), so the resolution step could lose its `test -d` guard and stay green.
    section = _section(skill_md, "### Plugin root")
    assert "scripts/harness_common" in section, (
        f"{DEEP_SKILL} '### Plugin root' must validate the candidate root by "
        "locating scripts/harness_common"
    )


def test_deep_passes_test_command_and_runs_baseline():
    """The orchestrator must pass --test-command to init and run the baseline gate.

    The CLI's CLAUDE.md parser is stricter than a human read; passing the
    command the skill already captured avoids a spurious init failure. The
    baseline run establishes a green starting tree and calibrates the per-run
    test timeout before the loop starts.
    """
    skill_md = _read(DEEP_SKILL)
    assert "--test-command" in skill_md
    assert "cli baseline" in skill_md


def test_deep_documents_yes_flag():
    """The --yes flag is the headless / CI entry point. If a future SKILL.md
    edit silently drops it, `claude -p "/optimus:deep …"` will hang on the
    confirmation AskUserQuestion with no test failure to flag the regression.
    """
    skill_md = _read(DEEP_SKILL)
    assert "`--yes`" in skill_md
    assert (
        "Skip this step entirely when `--resume` is given, or when `--yes` is given"
        in skill_md
    )


# ---------------------------------------------------------------------------
# Loop references must inject HARNESS_MODE_INLINE and read base SKILL.md
# ---------------------------------------------------------------------------


LOOP_REFS_AND_DISPATCHED_BASE_PATHS = [
    (
        "references/orchestrator-loop-single.md",
        ["skills/<base-skill>/SKILL.md", "references/harness-mode.md"],
    ),
    (
        "references/orchestrator-loop-paired.md",
        [
            "skills/unit-test/SKILL.md",
            "skills/refactor/SKILL.md",
            "references/coverage-harness-mode.md",
            "references/harness-mode.md",
        ],
    ),
]


@pytest.mark.parametrize("loop_ref,expected_paths", LOOP_REFS_AND_DISPATCHED_BASE_PATHS)
def test_loop_reference_dispatches_via_skill_md_read(loop_ref, expected_paths):
    """Loop refs must tell the subagent to read SKILL.md, not /optimus:slash-dispatch.

    The base SKILL.md files all carry `disable-model-invocation: true`, so a
    subagent prompt of `/optimus:code-review …` is not guaranteed to route.
    The orchestrator works around this by instructing the subagent to read
    the SKILL.md from disk and follow its harness-mode protocol.
    """
    ref = _read(loop_ref)
    assert (
        "HARNESS_MODE_INLINE" in ref
    ), f"{loop_ref} must inject HARNESS_MODE_INLINE in dispatch prompts"
    for path in expected_paths:
        assert path in ref, f"{loop_ref} must reference {path}"
    assert (
        "Read the base SKILL.md" in ref
    ), f"{loop_ref} must instruct the subagent to read the base SKILL.md from disk"


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


def test_harness_mode_documents_all_termination_reasons():
    """harness-mode.md's "Termination reasons" section must enumerate every
    reason cli.py's check-termination can emit — otherwise the docs lie about
    what the orchestrator might see.
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
    ref = _read("references/orchestrator-loop-paired.md")
    _, _, refactor_region = ref.partition("Conditionally dispatch the refactor phase")
    assert refactor_region, "paired loop must have a refactor-phase dispatch step"
    assert "cli snapshot" in refactor_region, (
        "orchestrator-loop-paired.md must re-snapshot before dispatching the "
        "refactor subagent so a refactor rollback does not discard the cycle's "
        "unit tests"
    )
