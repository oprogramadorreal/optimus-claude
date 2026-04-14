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


# Config keys that must never be set from a project-level harness.json.
# These either influence execution security (hooks_dir, allowed_tools,
# project_dir) or allow writing to arbitrary filesystem paths (log_dir,
# json_summary).  An untrusted repo could exploit either vector.
_CONFIG_BLOCKLIST = frozenset(
    {
        "hooks_dir",
        "allowed_tools",
        "project_dir",
        "log_dir",
        "json_summary",
    }
)


def apply_config_defaults(args, config, parser=None):
    """Apply *config* values as defaults for unset argparse attributes.

    An attribute is considered unset when its current value equals the
    argparse default for that flag — determined via ``parser.get_default``
    when *parser* is supplied.  Without *parser*, only ``None`` / ``""``
    values are treated as unset (a legitimately-passed ``0``/``False`` is
    preserved).

    Security-sensitive keys (``hooks_dir``, ``allowed_tools``, etc.) are
    ignored — those must come from the CLI, not a checked-in config file.

    Mutates *args* in place and returns it for convenience.
    """
    for config_key, value in config.items():
        attr = config_key.replace("-", "_")
        if attr.startswith("_") or not hasattr(args, attr):
            continue
        if attr in _CONFIG_BLOCKLIST:
            continue
        current = getattr(args, attr)
        if parser is not None:
            is_unset = current == parser.get_default(attr)
        else:
            is_unset = current in (None, "")
        if is_unset:
            setattr(args, attr, value)
    return args
