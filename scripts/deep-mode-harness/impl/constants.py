# Re-export shared constants for backward compatibility
from harness_common.constants import BACKUP_SUFFIX, DEFAULT_TEST_TIMEOUT, normalize_path

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
APPLIED_PENDING_TEST = "applied-pending-test"
PERSISTENT_STATUS = "persistent — fix failed"
VALID_FOCUS_MODES = frozenset({"testability", "guidelines"})


# Status grouping constants — single source of truth for status classification
FIXED_STATUSES = frozenset({"fixed", "retained — revert failed"})
REVERTED_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "skipped — apply failed"}
)
FAILURE_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "persistent — fix failed"}
)
