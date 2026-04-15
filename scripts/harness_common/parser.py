import json
import re


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

    if not isinstance(text, str):
        return None

    # Extract json:harness-output block
    pattern = r"```json:harness-output\s*\n(.*?)\n\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None
