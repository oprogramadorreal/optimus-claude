from impl.constants import (
    DEFAULT_MAX_CYCLES,
    DEFAULT_MAX_TURNS,
    DEFAULT_SESSION_TIMEOUT,
    MAX_CYCLES_HARD_CAP,
    PHASE_COMMIT_TYPE,
    PREFIX,
    PROGRESS_FILE_NAME,
)


class TestConstants:
    def test_prefix(self):
        assert PREFIX == "[coverage]"

    def test_defaults(self):
        assert isinstance(DEFAULT_MAX_CYCLES, int)
        assert DEFAULT_MAX_CYCLES > 0
        assert isinstance(MAX_CYCLES_HARD_CAP, int)
        assert MAX_CYCLES_HARD_CAP >= DEFAULT_MAX_CYCLES

    def test_progress_file_name(self):
        assert "test-coverage" in PROGRESS_FILE_NAME
        assert PROGRESS_FILE_NAME.endswith(".json")

    def test_phase_commit_types(self):
        assert PHASE_COMMIT_TYPE["unit-test"] == "test"
        assert PHASE_COMMIT_TYPE["refactor"] == "refactor"

    def test_session_defaults(self):
        assert DEFAULT_MAX_TURNS > 0
        assert DEFAULT_SESSION_TIMEOUT > 0
