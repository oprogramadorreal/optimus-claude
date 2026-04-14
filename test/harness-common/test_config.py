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
        args = Namespace(log_dir="", verbose=False)
        apply_config_defaults(args, {"log_dir": "/tmp/logs"})
        assert args.log_dir == "/tmp/logs"

    def test_does_not_override_explicit(self):
        args = Namespace(log_dir="/explicit", verbose=True)
        apply_config_defaults(args, {"log_dir": "/from-config", "verbose": False})
        assert args.log_dir == "/explicit"
        assert args.verbose is True

    def test_key_map(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-retries", type=int, default=0)
        args = parser.parse_args([])
        apply_config_defaults(
            args,
            {"max-retries": 3},
            parser=parser,
            key_map={"max-retries": "max_retries"},
        )
        assert args.max_retries == 3

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
        args = Namespace(hooks_dir="")
        apply_config_defaults(args, {"hooks-dir": "/hooks"})
        assert args.hooks_dir == "/hooks"

    def test_ignores_unknown_keys(self):
        args = Namespace(verbose=False)
        apply_config_defaults(args, {"unknown_key": "value"})
        assert not hasattr(args, "unknown_key")
