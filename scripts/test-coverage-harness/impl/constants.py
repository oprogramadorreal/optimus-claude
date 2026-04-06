DEFAULT_MAX_CYCLES = 5
MAX_CYCLES_HARD_CAP = 10
DEFAULT_MAX_TURNS = 30
DEFAULT_SESSION_TIMEOUT = 900  # 15 minutes per session
PROGRESS_FILE_NAME = ".claude/test-coverage-progress.json"

PREFIX = "[coverage]"

# Commit type mapping for coverage harness phases
PHASE_COMMIT_TYPE = {
    "unit-test": "test",
    "refactor": "refactor",
}
