DEFAULT_MAX_ITERATIONS = 8
MAX_ITERATIONS_HARD_CAP = 20
DEFAULT_MAX_TURNS = 50
DEFAULT_SESSION_TIMEOUT = 900  # 15 minutes per iteration
DEFAULT_TEST_TIMEOUT = 300  # 5 minutes for test runs
PROGRESS_FILE_NAME = ".claude/deep-mode-progress.json"
BACKUP_SUFFIX = ".bak"

PREFIX = "[deep-mode]"

# Maps skill names to conventional commit types. Unknown skills fall back to "chore".
SKILL_COMMIT_TYPE = {
    "code-review": "fix",
    "refactor": "refactor",
}
PERSISTENT_STATUS = "persistent — fix failed"
VALID_FOCUS_MODES = frozenset({"testability", "guidelines"})


def normalize_path(path_str):
    """Normalize path separators for cross-platform compatibility."""
    return path_str.replace("\\", "/")


# Status grouping constants — single source of truth for status classification
FIXED_STATUSES = frozenset({"fixed", "retained — revert failed"})
REVERTED_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "skipped — apply failed"}
)
FAILURE_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "persistent — fix failed"}
)
