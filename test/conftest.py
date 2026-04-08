"""Root test conftest — manages sys.path for harness impl modules.

Both deep-mode-harness and test-coverage-harness have an ``impl`` package.
When pytest collects tests from both suites in the same process, whichever
conftest runs last wins for ``impl`` in ``sys.modules``, breaking the other
suite's ``from impl.xxx import ...`` and ``mock.patch("impl.xxx.yyy")``.

This conftest solves the collision by saving/restoring module objects per
harness, so each test suite sees the exact same ``impl`` module instances
during both collection and execution.
"""

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent.parent / "scripts")

_HARNESS_MAP = {
    "deep-mode-harness": str(Path(_SCRIPTS) / "deep-mode-harness"),
    "test-coverage-harness": str(Path(_SCRIPTS) / "test-coverage-harness"),
}

# Module names that differ between harnesses and must be swapped
_SWAPPABLE = ("impl", "main")

# Ensure scripts/ is on sys.path (for harness_common imports)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

_saved_modules = {}  # harness_name -> {module_name: module_object}
_current_harness = None


def _detect_harness(node_path):
    """Return the harness name for a collector/item path, or None.

    Match on path *segments* rather than raw substrings — a parent
    directory name (e.g. a worktree called ``feat-deep-mode-harness-2``)
    must not be mistaken for the harness directory itself. We look for
    ``test/<harness>`` in the path parts, which is where the harness
    test suites actually live.
    """
    try:
        parts = Path(node_path).parts
    except (TypeError, ValueError):
        return None
    for i, part in enumerate(parts[:-1]):
        if part == "test" and parts[i + 1] in _HARNESS_MAP:
            return parts[i + 1]
    return None


def _activate_harness(node_path):
    """Ensure the correct harness's impl/main modules are active in sys.modules."""
    global _current_harness
    harness_name = _detect_harness(node_path)
    if harness_name is None:
        return
    if harness_name == _current_harness:
        return
    harness_path = _HARNESS_MAP[harness_name]
    # Save the outgoing harness's module objects
    if _current_harness is not None:
        _saved_modules[_current_harness] = {
            k: v
            for k, v in sys.modules.items()
            if any(k == s or k.startswith(s + ".") for s in _SWAPPABLE)
        }
    # Remove swappable modules from sys.modules
    for key in [
        k
        for k in sys.modules
        if any(k == s or k.startswith(s + ".") for s in _SWAPPABLE)
    ]:
        del sys.modules[key]
    # Restore saved modules for the incoming harness (if seen before)
    if harness_name in _saved_modules:
        sys.modules.update(_saved_modules[harness_name])
    # Ensure the correct harness path is at the front of sys.path
    if harness_path in sys.path:
        sys.path.remove(harness_path)
    sys.path.insert(0, harness_path)
    _current_harness = harness_name


def pytest_collectstart(collector):
    """Swap ``impl`` on sys.path before each test directory is collected."""
    _activate_harness(str(getattr(collector, "path", getattr(collector, "fspath", ""))))


def pytest_runtest_setup(item):
    """Restore the correct ``impl`` modules before each test executes."""
    _activate_harness(str(item.path))
