"""Lightweight schema validation for harness output JSON.

Validates the structured JSON that skills emit in ``json:harness-output``
blocks against expected schemas.  Uses only the stdlib (no jsonschema
dependency) and returns normalized data with defaults filled in plus a
list of human-readable warnings for contract violations.
"""


def _check_type(data, key, expected_type, warnings, default=None):
    """Check a field's type, fill default if missing, and log warnings."""
    value = data.get(key)
    if value is None:
        if default is not None:
            data[key] = default
        warnings.append(f"Missing field '{key}', defaulting to {default!r}")
        return
    if not isinstance(value, expected_type):
        warnings.append(
            f"Field '{key}' expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
        data[key] = default


def _validate_finding(finding, index, warnings):
    """Validate a single finding/fix entry."""
    required_str_fields = ("file", "category")
    for field in required_str_fields:
        if not finding.get(field):
            warnings.append(f"Finding [{index}]: missing or empty '{field}'")

    if not isinstance(finding.get("line", 0), int):
        warnings.append(f"Finding [{index}]: 'line' should be int")

    # pre_edit_content and post_edit_content are required for mechanical bisection
    if "pre_edit_content" not in finding:
        warnings.append(f"Finding [{index}]: missing 'pre_edit_content'")
    # post_edit_content can be empty string (deletion fix) but should be present
    if "post_edit_content" not in finding:
        warnings.append(f"Finding [{index}]: missing 'post_edit_content'")


def validate_deep_mode_output(data):
    """Validate deep-mode harness output JSON.

    Returns (normalized_data, warnings).  The normalized data has defaults
    filled in for any missing fields so downstream code can safely access them.
    """
    if not isinstance(data, dict):
        return data, ["Harness output is not a JSON object"]

    warnings = []

    _check_type(data, "new_findings", list, warnings, default=[])
    _check_type(data, "fixes_applied", list, warnings, default=[])
    _check_type(data, "no_new_findings", bool, warnings, default=False)
    _check_type(data, "no_actionable_fixes", bool, warnings, default=False)

    for i, finding in enumerate(data.get("new_findings", [])):
        _validate_finding(finding, i, warnings)

    for i, fix in enumerate(data.get("fixes_applied", [])):
        _validate_finding(fix, i, warnings)

    return data, warnings


def validate_coverage_unit_test_output(data):
    """Validate test-coverage harness unit-test phase output JSON.

    Returns (normalized_data, warnings).
    """
    if not isinstance(data, dict):
        return data, ["Harness output is not a JSON object"]

    warnings = []

    _check_type(data, "tests_written", list, warnings, default=[])
    _check_type(data, "coverage", dict, warnings, default={})
    _check_type(data, "no_new_tests", bool, warnings, default=False)
    _check_type(data, "no_untestable_code", bool, warnings, default=True)
    _check_type(data, "no_coverage_gained", bool, warnings, default=False)

    # Validate coverage sub-fields
    coverage = data.get("coverage", {})
    if isinstance(coverage, dict):
        for field in ("before", "after", "delta"):
            if field not in coverage:
                warnings.append(f"coverage.{field} missing")

    return data, warnings


def validate_coverage_refactor_output(data):
    """Validate test-coverage harness refactor phase output JSON.

    Same schema as deep-mode output (findings + fixes).
    Returns (normalized_data, warnings).
    """
    return validate_deep_mode_output(data)


def validate_harness_output(data, harness_type, phase=None):
    """Dispatch to the appropriate validator based on harness type.

    Args:
        data: Parsed JSON dict from the harness output block.
        harness_type: One of "deep-mode", "coverage".
        phase: For coverage harness, one of "unit-test", "refactor".

    Returns:
        (normalized_data, warnings) tuple.
    """
    if harness_type == "deep-mode":
        return validate_deep_mode_output(data)
    if harness_type == "coverage":
        if phase == "unit-test":
            return validate_coverage_unit_test_output(data)
        return validate_coverage_refactor_output(data)
    return data, [f"Unknown harness type: {harness_type}"]
