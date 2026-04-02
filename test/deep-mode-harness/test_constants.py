from impl.constants import (
    BACKUP_SUFFIX,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_TURNS,
    DEFAULT_SESSION_TIMEOUT,
    MAX_ITERATIONS_HARD_CAP,
    PREFIX,
    PROGRESS_FILE_NAME,
)


class TestConstants:
    def test_types(self):
        assert isinstance(DEFAULT_MAX_ITERATIONS, int)
        assert isinstance(MAX_ITERATIONS_HARD_CAP, int)
        assert isinstance(DEFAULT_MAX_TURNS, int)
        assert isinstance(DEFAULT_SESSION_TIMEOUT, int)
        assert isinstance(PROGRESS_FILE_NAME, str)
        assert isinstance(BACKUP_SUFFIX, str)
        assert isinstance(PREFIX, str)

    def test_values(self):
        assert DEFAULT_MAX_ITERATIONS == 8
        assert MAX_ITERATIONS_HARD_CAP == 20
        assert DEFAULT_MAX_ITERATIONS <= MAX_ITERATIONS_HARD_CAP
        assert DEFAULT_SESSION_TIMEOUT > 0
        assert PROGRESS_FILE_NAME.endswith(".json")
