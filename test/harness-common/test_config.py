import argparse
import json
from argparse import Namespace

from harness_common.config import apply_config_defaults, load_project_config


class TestLoadProjectConfig:
    def test_missing_file(self, tmp_path):
        assert load_project_config(tmp_path) == {}

    def test_valid_config(self, tmp_path):
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        (config_dir / "harness.json").write_text(
            json.dumps({"deep_mode": {"max_iterations": 10}}),
            encoding="utf-8",
        )
        result = load_project_config(tmp_path)
        assert result == {"deep_mode": {"max_iterations": 10}}

    def test_section_extraction(self, tmp_path):
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        (config_dir / "harness.json").write_text(
            json.dumps(
                {"deep_mode": {"max_iterations": 10}, "common": {"verbose": True}}
            ),
            encoding="utf-8",
        )
        assert load_project_config(tmp_path, section="deep_mode") == {
            "max_iterations": 10
        }
        assert load_project_config(tmp_path, section="common") == {"verbose": True}

    def test_missing_section(self, tmp_path):
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        (config_dir / "harness.json").write_text(
            json.dumps({"deep_mode": {}}),
            encoding="utf-8",
        )
        assert load_project_config(tmp_path, section="nonexistent") == {}

    def test_invalid_json(self, tmp_path):
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        (config_dir / "harness.json").write_text("not json!", encoding="utf-8")
        assert load_project_config(tmp_path) == {}

    def test_non_dict_root(self, tmp_path):
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        (config_dir / "harness.json").write_text('"just a string"', encoding="utf-8")
        assert load_project_config(tmp_path) == {}

    def test_non_dict_section(self, tmp_path):
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        (config_dir / "harness.json").write_text(
            json.dumps({"deep_mode": "not a dict"}),
            encoding="utf-8",
        )
        assert load_project_config(tmp_path, section="deep_mode") == {}


class TestApplyConfigDefaults:
    def test_fills_empty_string(self):
        args = Namespace(max_turns="", verbose=False)
        apply_config_defaults(args, {"max_turns": "50"})
        assert args.max_turns == "50"

    def test_does_not_override_explicit(self):
        args = Namespace(max_turns="100", verbose=True)
        apply_config_defaults(args, {"max_turns": "50", "verbose": False})
        assert args.max_turns == "100"
        assert args.verbose is True

    def test_explicit_zero_not_overridden(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-retries", type=int, default=2)
        args = parser.parse_args(["--max-retries", "0"])
        apply_config_defaults(args, {"max_retries": 5}, parser=parser)
        assert args.max_retries == 0

    def test_parser_default_overridden_by_config(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-retries", type=int, default=2)
        args = parser.parse_args([])
        apply_config_defaults(args, {"max_retries": 5}, parser=parser)
        assert args.max_retries == 5

    def test_dash_to_underscore_auto(self):
        args = Namespace(max_turns="")
        apply_config_defaults(args, {"max-turns": "50"})
        assert args.max_turns == "50"

    def test_ignores_unknown_keys(self):
        args = Namespace(verbose=False)
        apply_config_defaults(args, {"unknown_key": "value"})
        assert not hasattr(args, "unknown_key")

    def test_security_sensitive_keys_blocked(self):
        """Project config must not be able to set hooks_dir, allowed_tools, etc."""
        args = Namespace(
            hooks_dir="",
            allowed_tools="",
            project_dir="",
            log_dir="",
            json_summary="",
            max_turns="",
        )
        apply_config_defaults(
            args,
            {
                "hooks_dir": "/evil/hooks",
                "allowed_tools": "Bash",
                "project_dir": "/evil/proj",
                "log_dir": "/evil/logs",
                "json_summary": "/evil.json",
                "max_turns": "50",
            },
        )
        # Blocklisted keys keep their empty defaults
        assert args.hooks_dir == ""
        assert args.allowed_tools == ""
        assert args.project_dir == ""
        assert args.log_dir == ""
        assert args.json_summary == ""
        # Non-blocklisted keys still flow through
        assert args.max_turns == "50"
