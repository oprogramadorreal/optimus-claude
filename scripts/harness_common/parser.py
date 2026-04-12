import json
import re

from .schema import validate_harness_output


def parse_harness_output(raw_output, harness_type=None, phase=None):
    """Extract the json:harness-output block from claude's response.

    With ``--output-format json``, the output is a JSON object with a
    ``result`` field.

    When *harness_type* is provided (e.g. ``"deep-mode"`` or ``"coverage"``),
    the parsed data is validated against the expected schema.  Contract
    warnings are printed to stderr but do not prevent the data from being
    returned — callers get best-effort normalized data.

    Returns the parsed dict, or ``None`` on extraction failure.
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
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    # Schema validation — normalize data and log warnings
    if harness_type and isinstance(data, dict):
        data, warnings = validate_harness_output(data, harness_type, phase=phase)
        for warning in warnings:
            print(f"[harness] Contract warning: {warning}")

    return data
