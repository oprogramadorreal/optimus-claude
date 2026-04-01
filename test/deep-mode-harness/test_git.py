from unittest.mock import MagicMock, patch

from impl.git import _build_commit_body, git_rev_parse_head


class TestBuildCommitBody:
    def test_empty_findings(self):
        progress = {"findings": []}
        assert _build_commit_body(progress, 1) == ""

    def test_no_matching_iteration(self):
        progress = {"findings": [{"iteration_last_attempted": 2, "status": "fixed"}]}
        assert _build_commit_body(progress, 1) == ""

    def test_fixed_findings(self):
        progress = {
            "findings": [
                {
                    "iteration_last_attempted": 1,
                    "status": "fixed",
                    "file": "src/a.js",
                    "line": 10,
                    "category": "bug",
                    "summary": "Fix null check",
                },
            ]
        }
        body = _build_commit_body(progress, 1)
        assert "Fixed:" in body
        assert "src/a.js:10" in body
        assert "[bug]" in body

    def test_reverted_findings(self):
        progress = {
            "findings": [
                {
                    "iteration_last_attempted": 1,
                    "status": "reverted — test failure",
                    "file": "src/b.js",
                    "line": 5,
                    "category": "style",
                    "summary": "Reformat",
                },
            ]
        }
        body = _build_commit_body(progress, 1)
        assert "Reverted (test failure):" in body

    def test_max_entries_truncation(self):
        findings = []
        for i in range(15):
            findings.append({
                "iteration_last_attempted": 1,
                "status": "fixed",
                "file": f"src/file{i}.js",
                "line": i,
                "category": "bug",
                "summary": f"Fix {i}",
            })
        progress = {"findings": findings}
        body = _build_commit_body(progress, 1, max_entries=5)
        assert "... and 10 more" in body

    def test_long_summary_truncated(self):
        progress = {
            "findings": [
                {
                    "iteration_last_attempted": 1,
                    "status": "fixed",
                    "file": "a.js",
                    "line": 1,
                    "category": "x",
                    "summary": "A" * 100,
                },
            ]
        }
        body = _build_commit_body(progress, 1)
        assert "..." in body


class TestGitRevParseHead:
    @patch("impl.git.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
        assert git_rev_parse_head("/tmp") == "abc123"

    @patch("impl.git.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert git_rev_parse_head("/tmp") is None
