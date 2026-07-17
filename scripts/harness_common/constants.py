BACKUP_SUFFIX = ".bak"
DEFAULT_TEST_TIMEOUT = 300  # 5 minutes for test runs

APPLIED_PENDING_TEST = "applied-pending-test"
PERSISTENT_STATUS = "persistent — fix failed"

# commit_checkpoint result statuses (internal — cmd_commit_checkpoint maps these
# to the orchestrator-facing words "committed" / "nothing-to-commit" / "commit-failed").
COMMIT_COMMITTED = "committed"
COMMIT_NOTHING = "nothing-to-commit"
COMMIT_FAILED = "failed"

FIXED_STATUSES = frozenset({"fixed", "retained — revert failed"})
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

# Skills that accept --focus, mapped to their valid modes. cmd_init derives
# both the gate and its error message from this table, so a newly focus-capable
# skill is one data row here — not a branch in cli.py with a hardcoded skill
# name whose error message would point users at the wrong skill.
FOCUS_MODES_BY_SKILL = {"refactor": VALID_FOCUS_MODES}

# Per-iteration scratch-file prefixes the loop writes alongside the progress
# file in .claude/. Consumed bare by cli.py's final-report cleanup (globbing
# inside the .claude/ dir) and anchored with a ".claude/" prefix by git.py's
# _HARNESS_STATE_EXCLUDES. This repo's .gitignore and
# references/orchestrator-loop-single.md mirror them for the harness dev loop
# and the orchestrator — rename a prefix here and update those two mirrors.
SCRATCH_GLOBS = (".deep-iteration-*", ".unit-test-deep-*")

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

# /optimus:deep target → (base skill, loop reference). The deep SKILL.md
# Targets table, the skill-contract test, and validate.sh's harness-routing
# check all derive from this mapping, so adding a target here puts every gate
# on notice instead of leaving frozen per-gate rosters to drift.
DEEP_TARGETS = {
    "review": ("code-review", "references/orchestrator-loop-single.md"),
    "refactor": ("refactor", "references/orchestrator-loop-single.md"),
    "coverage": ("unit-test", "references/orchestrator-loop-paired.md"),
}


def normalize_path(path_str):
    """Normalize path separators for cross-platform compatibility."""
    return path_str.replace("\\", "/")
