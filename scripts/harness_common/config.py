import json
from pathlib import Path

CONFIG_FILE_NAME = "harness.json"


def load_project_config(project_root, section=None):
    """Load project-level harness defaults from ``.claude/harness.json``.

    Returns the ``section`` dict (e.g. ``"deep_mode"`` or ``"test_coverage"``)
    if specified, otherwise the full config dict.  Returns an empty dict when
    the file is missing, unreadable, or contains invalid JSON — never raises.
    """
    config_path = Path(project_root) / ".claude" / CONFIG_FILE_NAME
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    if section:
        sub = data.get(section, {})
        return sub if isinstance(sub, dict) else {}
    return data


def apply_config_defaults(parser, config, key_map=None):
    """Override argparse defaults with values from a config dict.

    Only keys that exist in both the config dict and the parser's defaults
    are applied.  Explicit CLI args always win because ``set_defaults``
    only changes the default — ``parse_args`` overwrites defaults with
    command-line values.

    ``key_map`` translates config keys (underscored) to argparse dest names
    when they differ (e.g. ``{"max_iterations": "max_iterations"}``).  By
    default, config keys are used as-is.
    """
    key_map = key_map or {}
    defaults = {}
    for cfg_key, value in config.items():
        dest = key_map.get(cfg_key, cfg_key)
        defaults[dest] = value
    if defaults:
        parser.set_defaults(**defaults)
