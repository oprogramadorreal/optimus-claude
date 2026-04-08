from unittest.mock import patch

from impl.reporting import build_commit_body, print_report


class TestPrintReport:
    def test_basic_report(self, sample_coverage_progress, capsys):
        sample_coverage_progress["cycle"]["completed"] = 2
        sample_coverage_progress["coverage"]["baseline"] = 40.0
        sample_coverage_progress["coverage"]["current"] = 65.0
        sample_coverage_progress["tests_created"] = [
            {"test_count": 3, "cycle": 1},
            {"test_count": 5, "cycle": 2},
        ]
        sample_coverage_progress["termination"] = {
            "reason": "convergence",
            "message": "Coverage plateau",
        }
        with patch("impl.reporting.git_current_branch", return_value="feature/x"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Coverage Harness Report" in output
        assert "40.0% → 65.0%" in output
        assert "8 tests in 2 files" in output
        assert "convergence" in output

    def test_no_coverage_measured(self, sample_coverage_progress, capsys):
        with patch("impl.reporting.git_current_branch", return_value="main"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "not measured" in output

    def test_with_coverage_history(self, sample_coverage_progress, capsys):
        sample_coverage_progress["coverage"]["history"] = [
            {"cycle": 1, "before": 40, "after": 55, "delta": 15},
        ]
        with patch("impl.reporting.git_current_branch", return_value="main"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Cycle" in output
        assert "Before" in output

    def test_with_bugs(self, sample_coverage_progress, capsys):
        sample_coverage_progress["bugs_discovered"] = [{"description": "bug1"}]
        with patch("impl.reporting.git_current_branch", return_value="main"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Bugs discovered" in output

    def test_with_untestable(self, sample_coverage_progress, capsys):
        sample_coverage_progress["untestable_code"] = [{"file": "src/x.py"}]
        with patch("impl.reporting.git_current_branch", return_value="main"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Still untestable" in output

    def test_with_fixes_shows_git_advice(self, sample_coverage_progress, capsys):
        sample_coverage_progress["tests_created"] = [{"test_count": 1}]
        with patch("impl.reporting.git_current_branch", return_value="feature/x"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "git rebase" in output
        assert "git push" in output

    def test_no_changes_report(self, sample_coverage_progress, capsys):
        with patch("impl.reporting.git_current_branch", return_value="main"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "No changes made" in output

    def test_current_branch_parameter(self, sample_coverage_progress, capsys):
        sample_coverage_progress["tests_created"] = [{"test_count": 1}]
        print_report(sample_coverage_progress, current_branch="my-branch")
        output = capsys.readouterr().out
        assert "my-branch" in output

    def test_main_branch_no_push_advice(self, sample_coverage_progress, capsys):
        sample_coverage_progress["tests_created"] = [{"test_count": 1}]
        print_report(sample_coverage_progress, current_branch="main")
        output = capsys.readouterr().out
        assert "git push" not in output

    def test_refactor_fixes_counted(self, sample_coverage_progress, capsys):
        sample_coverage_progress["refactor_findings"] = [
            {"status": "fixed"},
            {"status": "reverted"},
        ]
        with patch("impl.reporting.git_current_branch", return_value="main"):
            print_report(sample_coverage_progress)
        output = capsys.readouterr().out
        assert "Testability fixes: 1" in output


class TestBuildCommitBody:
    def test_unit_test_phase(self, sample_coverage_progress):
        sample_coverage_progress["tests_created"] = [
            {
                "cycle": 1,
                "file": "tests/test_auth.py",
                "target_file": "src/auth.py",
                "test_count": 5,
            }
        ]
        body = build_commit_body(sample_coverage_progress, 1, "unit-test")
        assert "Tests written:" in body
        assert "test_auth.py" in body
        assert "5 tests" in body

    def test_refactor_phase(self, sample_coverage_progress):
        sample_coverage_progress["refactor_findings"] = [
            {
                "cycle": 1,
                "file": "src/db.py",
                "line": 15,
                "category": "testability",
                "summary": "Extract dependency",
                "status": "fixed",
            }
        ]
        body = build_commit_body(sample_coverage_progress, 1, "refactor")
        assert "Testability fixes" in body
        assert "src/db.py:15" in body

    def test_empty_cycle(self, sample_coverage_progress):
        body = build_commit_body(sample_coverage_progress, 1, "unit-test")
        assert "Coverage harness checkpoint" in body

    def test_max_entries_truncation(self, sample_coverage_progress):
        sample_coverage_progress["tests_created"] = [
            {
                "cycle": 1,
                "file": f"tests/test_{i}.py",
                "target_file": f"src/{i}.py",
                "test_count": 1,
            }
            for i in range(15)
        ]
        body = build_commit_body(
            sample_coverage_progress, 1, "unit-test", max_entries=5
        )
        assert "... and 10 more" in body

    def test_reverted_findings(self, sample_coverage_progress):
        sample_coverage_progress["refactor_findings"] = [
            {
                "cycle": 1,
                "file": "src/x.py",
                "line": 1,
                "category": "test",
                "summary": "Fix",
                "status": "reverted — test failure",
            }
        ]
        body = build_commit_body(sample_coverage_progress, 1, "refactor")
        assert "Reverted" in body
