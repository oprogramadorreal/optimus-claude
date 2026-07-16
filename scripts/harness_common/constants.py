BACKUP_SUFFIX = ".bak"
DEFAULT_TEST_TIMEOUT = 300  # 5 minutes for test runs

APPLIED_PENDING_TEST = "applied-pending-test"
PERSISTENT_STATUS = "persistent — fix failed"

# commit_checkpoint result statuses (internal — cmd_commit_checkpoint maps these
# to the orchestrator-facing words "committed" / "nothing-to-commit" / "commit-failed").
COMMIT_COMMITTED = "committed"
COMMIT_NOTHING = "nothing-to-commit"
COMMIT_FAILED = "failed"

FIXED_STATUSES = frozenset({"fixed"})
REVERTED_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "skipped — apply failed"}
)
FAILURE_STATUSES = frozenset(
    {"reverted — test failure", "reverted — attempt 2", "persistent — fix failed"}
)

# Orchestrator CLI defaults
DEFAULT_MAX_ITERATIONS = 8
MAX_ITERATIONS_HARD_CAP = 20
DEFAULT_MAX_CYCLES = 5
MAX_CYCLES_HARD_CAP = 10

VALID_FOCUS_MODES = frozenset({"testability", "guidelines"})

SKILL_COMMIT_TYPE = {
    "code-review": "fix",
    "refactor": "refactor",
}
PHASE_COMMIT_TYPE = {
    "unit-test": "test",
    "refactor": "refactor",
}

# Diminishing-returns soft-exit thresholds
SOFT_EXIT_MIN_ITERATION = 4
SOFT_EXIT_LOW_YIELD_THRESHOLD = 1
SOFT_EXIT_WINDOW = 2

DEFAULT_PROGRESS_FILES = {
    "code-review": ".claude/code-review-deep-progress.json",
    "refactor": ".claude/refactor-deep-progress.json",
    "unit-test": ".claude/unit-test-deep-progress.json",
}

# Skills using the deep-mode (single-skill iteration) variant
DEEP_VARIANT_SKILLS = frozenset({"code-review", "refactor"})
# Skill using the coverage (paired-cycle) variant
COVERAGE_VARIANT_SKILLS = frozenset({"unit-test"})


def normalize_path(path_str):
    """Normalize path separators for cross-platform compatibility."""
    return path_str.replace("\\", "/")
