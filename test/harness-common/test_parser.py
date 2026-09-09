import json
from pathlib import Path

import pytest
from harness_common.parser import parse_harness_output, validate_harness_output


def _valid(coverage=False):
    name = "coverage-harness-output" if coverage else "harness-output"
    return json.loads(
        (Path(__file__).parent / "fixtures" / f"{name}.golden.json").read_text(
            encoding="utf-8"
        )
    )


def _block(value):
    return "```json:harness-output\n" + json.dumps(value) + "\n```"


@pytest.mark.parametrize(
    "raw", [None, "", "random text", "```json:harness-output\n{invalid}\n```"]
)
def test_missing_or_invalid_block(raw):
    assert parse_harness_output(raw) is None


@pytest.mark.parametrize("coverage", [False, True])
def test_complete_documented_output(coverage):
    value = _valid(coverage)
    assert parse_harness_output("Analysis\n" + _block(value) + "\nDone") == value


@pytest.mark.parametrize("bad", [{}, [], "text", {"iteration": 1}])
def test_incomplete_output_rejected(bad):
    assert parse_harness_output(_block(bad)) is None


def test_refactor_phase_output_with_cycle_key_is_deep_variant():
    value = dict(_valid(), cycle=2)
    assert parse_harness_output(_block(value)) == value


@pytest.mark.parametrize("spelling", [1, 0, "1", "yes", "no"])
def test_flag_spellings_read_flag_accepts_are_not_rejected(spelling):
    value = dict(_valid(), no_new_findings=spelling)
    assert parse_harness_output(_block(value)) == value


def test_missing_flag_is_rejected():
    value = _valid()
    del value["no_new_findings"]
    assert parse_harness_output(_block(value)) is None


def test_last_complete_block_wins_after_echoed_template():
    first, last = _valid(), _valid()
    first["iteration"], last["iteration"] = 1, 2
    raw = (
        _block(first)
        + "\n```json:harness-output\n{<template>}\n```\n"
        + _block(last)
        + _block([])
    )
    assert parse_harness_output(raw) == last


@pytest.mark.parametrize(
    "field,value",
    [
        ("iteration", True),
        ("iteration", 0),
        ("fixes_applied", {}),
        ("new_findings", ["not an object"]),
        ("no_new_findings", "maybe"),
    ],
)
def test_wrong_types_rejected_before_step(field, value):
    output = _valid()
    output[field] = value
    with pytest.raises(ValueError):
        validate_harness_output(output, "deep")


@pytest.mark.parametrize("coverage", [False, True])
def test_missing_required_envelope_field_rejected(coverage):
    output = _valid(coverage)
    required = (
        (
            "cycle",
            "phase",
            "coverage",
            "tests_written",
            "untestable_code",
            "bugs_discovered",
            "no_new_tests",
            "no_untestable_code",
            "no_coverage_gained",
            "blocked",
        )
        if coverage
        else (
            "iteration",
            "new_findings",
            "fixes_applied",
            "fixes_skipped_persistent",
            "no_new_findings",
            "no_actionable_fixes",
        )
    )
    for field in required:
        candidate = {k: v for k, v in output.items() if k != field}
        with pytest.raises(ValueError, match="requires|invalid"):
            validate_harness_output(candidate, "coverage" if coverage else "deep")
