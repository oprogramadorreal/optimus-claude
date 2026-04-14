"""Lightweight stdlib-only schema validation for harness output JSON.

Validates and normalises the structured JSON that skills emit inside
``json:harness-output`` blocks.  Returns ``(normalised_data, warnings)``
so callers can log contract violations without crashing.
"""


def _check_list(data, key, warnings):
    val = data.get(key)
    if val is None:
        data[key] = []
        return
    if not isinstance(val, list):
        warnings.append(f"'{key}' should be a list, got {type(val).__name__}")
        data[key] = []


def _check_bool(data, key, default, warnings):
    val = data.get(key)
    if val is None:
        data[key] = default
        return
    if not isinstance(val, bool):
        warnings.append(f"'{key}' should be bool, got {type(val).__name__}")
        data[key] = default


def _validate_finding(item, index, warnings):
    """Validate a single finding/fix dict."""
    if not isinstance(item, dict):
        warnings.append(f"Finding [{index}] is not a dict")
        return
    for field in ("file", "category"):
        if not item.get(field):
            warnings.append(f"Finding [{index}] missing required field '{field}'")
    line = item.get("line")
    if line is not None and not isinstance(line, int):
        if isinstance(line, float) and not line.is_integer():
            warnings.append(f"Finding [{index}] 'line' is not an integer: {line!r}")
            item["line"] = None
        else:
            try:
                item["line"] = int(line)
            except (ValueError, TypeError):
                warnings.append(f"Finding [{index}] 'line' is not an integer: {line!r}")
                item["line"] = None


def validate_deep_mode_output(data):
    """Validate and normalise deep-mode harness output.

    Returns ``(normalised_data, warnings)``.
    """
    warnings = []
    if not isinstance(data, dict):
        return data, [f"Expected dict, got {type(data).__name__}"]

    _check_list(data, "new_findings", warnings)
    _check_list(data, "fixes_applied", warnings)
    _check_bool(data, "no_new_findings", False, warnings)
    _check_bool(data, "no_actionable_fixes", False, warnings)

    for i, item in enumerate(data.get("new_findings", [])):
        _validate_finding(item, i, warnings)
    for i, item in enumerate(data.get("fixes_applied", [])):
        _validate_finding(item, i, warnings)

    return data, warnings


def validate_coverage_unit_test_output(data):
    """Validate and normalise coverage unit-test phase output."""
    warnings = []
    if not isinstance(data, dict):
        return data, [f"Expected dict, got {type(data).__name__}"]

    _check_list(data, "tests_written", warnings)
    _check_bool(data, "no_new_tests", False, warnings)
    _check_bool(data, "no_untestable_code", False, warnings)
    _check_bool(data, "no_coverage_gained", False, warnings)

    # Normalise coverage sub-object
    coverage = data.get("coverage")
    if coverage is None:
        data["coverage"] = {"before": None, "after": None, "delta": None}
    elif isinstance(coverage, dict):
        for field in ("before", "after", "delta"):
            coverage.setdefault(field, None)
    else:
        warnings.append(f"'coverage' should be dict, got {type(coverage).__name__}")
        data["coverage"] = {"before": None, "after": None, "delta": None}

    return data, warnings


def validate_harness_output(data, harness_type, phase=None):
    """Dispatch to the appropriate validator based on harness type and phase."""
    if harness_type == "deep-mode":
        return validate_deep_mode_output(data)
    if harness_type == "test-coverage":
        if phase == "unit-test":
            return validate_coverage_unit_test_output(data)
        return validate_deep_mode_output(data)
    # Unknown harness type — no validation
    return data, []
