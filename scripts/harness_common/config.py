import json
from pathlib import Path


def load_project_config(project_root, section=None):
    """Load harness configuration from ``.claude/harness.json``.

    Returns the full config dict, or just the named *section* if given.
    Gracefully returns ``{}`` on missing file, invalid JSON, or non-dict root.
    """
    config_path = Path(project_root) / ".claude" / "harness.json"
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    if section:
        return data.get(section, {}) if isinstance(data.get(section), dict) else {}
    return data


def apply_config_defaults(args, config, key_map=None):
    """Apply *config* values as defaults for unset argparse attributes.

    Only fills in attributes that are still at their argparse default (i.e.
    the caller did not explicitly pass a CLI flag).  *key_map* translates
    config keys to attribute names when they differ (e.g.
    ``{"max_iterations": "max_iterations"}`` is identity, but
    ``{"max-retries": "max_retries"}`` handles the dash/underscore mismatch).

    Mutates *args* in place and returns it for convenience.
    """
    key_map = key_map or {}
    for config_key, value in config.items():
        attr = key_map.get(config_key, config_key.replace("-", "_"))
        if hasattr(args, attr) and getattr(args, attr) in (None, "", False, 0):
            setattr(args, attr, value)
    return args
