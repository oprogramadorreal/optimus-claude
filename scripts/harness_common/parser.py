import json
import re


def parse_harness_output(raw_output):
    """
    Extract the json:harness-output block from a subagent's response.

    When more than one ``json:harness-output`` block is present — e.g. the
    subagent echoed the template from references/harness-mode.md before its real
    output — the LAST block that parses as valid JSON wins, since the protocol
    requires the real block to be emitted last ("emit a single block and stop").
    """
    if not raw_output:
        return None

    pattern = r"```json:harness-output\s*\n(.*?)\n\s*```"
    for block in reversed(re.findall(pattern, raw_output, re.DOTALL)):
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue

    return None
