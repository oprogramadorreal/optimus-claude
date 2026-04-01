from impl.reporting import detect_test_command, print_report


class TestDetectTestCommand:
    def test_code_block_pattern(self, claude_md_dir):
        cmd = detect_test_command(claude_md_dir)
        assert cmd == "npm test"

    def test_no_claude_md(self, tmp_path):
        assert detect_test_command(tmp_path) is None

    def test_explicit_test_command_pattern(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "test command: `pytest -v`\n", encoding="utf-8"
        )
        assert detect_test_command(tmp_path) == "pytest -v"

    def test_strips_trailing_comment(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "test command: `npm test  # Run unit tests`\n", encoding="utf-8"
        )
        assert detect_test_command(tmp_path) == "npm test"

    def test_no_test_command_found(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "# Project\n\nNo test command here.\n", encoding="utf-8"
        )
        assert detect_test_command(tmp_path) is None


class TestPrintReport:
    def test_clean_report(self, sample_progress, capsys):
        sample_progress["termination"] = {
            "reason": "convergence",
            "message": "No new findings",
        }
        sample_progress["iteration"]["completed"] = 1
        print_report(sample_progress)
        output = capsys.readouterr().out
        assert "Cumulative Report" in output
        assert "Iterations:    1" in output
        assert "Fixed:         0" in output
        assert "codebase looks clean" in output

    def test_report_with_findings(self, sample_progress, tmp_path, capsys):
        sample_progress["config"]["project_root"] = str(tmp_path)
        sample_progress["findings"] = [
            {
                "file": "src/a.js",
                "line": 10,
                "category": "bug",
                "summary": "Fix null check",
                "status": "fixed",
                "iteration_discovered": 1,
            }
        ]
        sample_progress["termination"] = {"reason": "convergence", "message": "Done"}
        sample_progress["iteration"]["completed"] = 2
        print_report(sample_progress)
        output = capsys.readouterr().out
        assert "Fixed:         1" in output
        assert "src/a.js" in output
