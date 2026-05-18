"""Root test conftest — ensures ``scripts/`` is on ``sys.path``.

The harness CLI and its modules live under ``scripts/harness_common/``. Tests
under ``test/harness-common/`` import them as ``from harness_common.<module>
import ...`` — this conftest adds the parent ``scripts/`` directory to
``sys.path`` so those imports resolve.
"""

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent.parent / "scripts")

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
