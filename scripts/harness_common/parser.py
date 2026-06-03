import json
import re


def parse_harness_output(raw_output):
    """
    Extract the json:harness-output block from a subagent's response.

    When more than one ``json:harness-output`` block is present — e.g. the
    subagent echoed the template from references/harness-mode.md before its real
    output — the LAST block that parses as a valid JSON object wins, since the
    protocol requires the real block to be emitted last ("emit a single block
    and stop").

    Only a JSON *object* is accepted. A block that parses to a list/scalar is
    malformed harness output and is skipped (like an unparseable block), so the
    function returns ``None`` instead of a value the callers would immediately
    crash on with ``.get(...)`` — and the orchestrator counts it as a parse
    failure (``cmd_parse --progress-file``) rather than ingesting garbage.
    """
    if not raw_output:
        return None

    pattern = r"```json:harness-output\s*\n(.*?)\n\s*```"
    for block in reversed(re.findall(pattern, raw_output, re.DOTALL)):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None
