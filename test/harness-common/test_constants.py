from harness_common.constants import BACKUP_SUFFIX, DEFAULT_TEST_TIMEOUT, normalize_path


class TestNormalizePath:
    def test_backslash_to_forward(self):
        assert normalize_path("C:\\Users\\test\\file.txt") == "C:/Users/test/file.txt"

    def test_forward_slash_unchanged(self):
        assert normalize_path("src/app.js") == "src/app.js"

    def test_empty_string(self):
        assert normalize_path("") == ""

    def test_mixed_slashes(self):
        assert normalize_path("src\\api/routes\\v1") == "src/api/routes/v1"


class TestConstants:
    def test_backup_suffix(self):
        assert BACKUP_SUFFIX == ".bak"

    def test_default_test_timeout(self):
        assert isinstance(DEFAULT_TEST_TIMEOUT, int)
        assert DEFAULT_TEST_TIMEOUT > 0
