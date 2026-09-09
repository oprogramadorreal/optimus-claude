import json
import re


def validate_harness_output(value, variant=None):
    """Validate the safety-critical envelope, retaining legacy scalar coercion.

    The published schemas describe the full authoring contract. Runtime checks
    reject missing/wrong containers before callers iterate them; coverage values
    and finding line numbers still use the established normalization in the CLI.
    """
    if not isinstance(value, dict):
        raise ValueError("harness output must be an object")
    coverage = variant == "coverage" or (variant is None and "cycle" in value)
    counter = "cycle" if coverage else "iteration"
    if type(value.get(counter)) is not int or value[counter] < 1:
        raise ValueError(f"harness output requires a positive integer {counter}")
    arrays = (
        ("tests_written", "untestable_code", "bugs_discovered")
        if coverage
        else ("new_findings", "fixes_applied", "fixes_skipped_persistent")
    )
    flags = (
        ("no_new_tests", "no_untestable_code", "no_coverage_gained")
        if coverage
        else ("no_new_findings", "no_actionable_fixes")
    )
    for field in arrays:
        if not isinstance(value.get(field), list):
            raise ValueError(f"harness output requires an array: {field}")
        item_type = str if field == "fixes_skipped_persistent" else dict
        if any(not isinstance(item, item_type) for item in value[field]):
            raise ValueError(f"invalid item in {field}")
    for field in flags:
        flag = value.get(field)
        # read_flag historically accepts these exact string forms too.
        if type(flag) is not bool and flag not in ("true", "false", "True", "False"):
            raise ValueError(f"harness output requires a boolean: {field}")
    if coverage:
        if value.get("phase") != "unit-test" or not isinstance(
            value.get("coverage"), dict
        ):
            raise ValueError(
                "coverage output requires phase unit-test and coverage object"
            )
        if "blocked" not in value or not isinstance(
            value["blocked"], (str, type(None))
        ):
            raise ValueError("coverage output requires blocked (string or null)")
    return value


def parse_harness_output(raw_output):
    """
    Extract the json:harness-output block from a subagent's response.

    When more than one ``json:harness-output`` block is present — e.g. the
    subagent echoed the template from references/harness-mode.md before its real
    output — the LAST block with a valid protocol envelope wins, since the
    protocol requires the real block to be emitted last ("emit a single block
    and stop").

    Empty objects, incomplete envelopes and wrong container types are skipped,
    as are malformed JSON and scalar/list blocks. The CLI uses the same
    validator for direct result-file ingestion, so bypassing parse cannot
    turn missing fields into an apparently successful no-fix iteration.
    """
    if not raw_output:
        return None

    pattern = r"```json:harness-output\s*\n(.*?)\n\s*```"
    for block in reversed(re.findall(pattern, raw_output, re.DOTALL)):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        try:
            return validate_harness_output(parsed)
        except ValueError:
            continue

    return None
