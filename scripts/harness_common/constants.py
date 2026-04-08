BACKUP_SUFFIX = ".bak"
DEFAULT_TEST_TIMEOUT = 300  # 5 minutes for test runs


def normalize_path(path_str):
    """Normalize path separators for cross-platform compatibility."""
    return path_str.replace("\\", "/")
