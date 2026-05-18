# Re-export shared constants for backward compatibility
from harness_common.constants import (
    APPLIED_PENDING_TEST,
    BACKUP_SUFFIX,
    DEFAULT_TEST_TIMEOUT,
    FAILURE_STATUSES,
    FIXED_STATUSES,
    PERSISTENT_STATUS,
    REVERTED_STATUSES,
    normalize_path,
)

DEFAULT_MAX_ITERATIONS = 8
MAX_ITERATIONS_HARD_CAP = 20
DEFAULT_MAX_TURNS = 50
DEFAULT_SESSION_TIMEOUT = 900  # 15 minutes per iteration
PROGRESS_FILE_NAME = ".claude/deep-mode-progress.json"

PREFIX = "[deep-mode]"

# Maps skill names to conventional commit types. Unknown skills fall back to "chore".
SKILL_COMMIT_TYPE = {
    "code-review": "fix",
    "refactor": "refactor",
}
VALID_FOCUS_MODES = frozenset({"testability", "guidelines"})
