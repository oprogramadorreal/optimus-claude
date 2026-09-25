"""Root test conftest: puts ``scripts/`` on ``sys.path``.

Tests import ``harness_common`` and the standalone script modules
(``skill_test_support``, ``validate_skill_metadata``) from there.
"""

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent.parent / "scripts")

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
