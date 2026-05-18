BACKUP_SUFFIX = ".bak"
DEFAULT_TEST_TIMEOUT = 300  # 5 minutes for test runs

APPLIED_PENDING_TEST = "applied-pending-test"
PERSISTENT_STATUS = "persistent — fix failed"

FIXED_STATUSES = frozenset({"fixed", "retained — revert failed"})
REVERTED_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "skipped — apply failed"}
)
FAILURE_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "persistent — fix failed"}
)


def normalize_path(path_str):
    """Normalize path separators for cross-platform compatibility."""
    return path_str.replace("\\", "/")
