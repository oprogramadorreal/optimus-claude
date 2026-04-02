DEFAULT_MAX_ITERATIONS = 8
MAX_ITERATIONS_HARD_CAP = 20
DEFAULT_MAX_TURNS = 30
DEFAULT_SESSION_TIMEOUT = 900  # 15 minutes per iteration
DEFAULT_TEST_TIMEOUT = 300  # 5 minutes for test runs
PROGRESS_FILE_NAME = ".claude/deep-mode-progress.json"
BACKUP_SUFFIX = ".bak"

PREFIX = "[deep-mode]"

# Status grouping constants — single source of truth for status classification
FIXED_STATUSES = frozenset({"fixed", "retained — revert failed"})
REVERTED_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "skipped — apply failed"}
)
FAILURE_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "persistent — fix failed"}
)
