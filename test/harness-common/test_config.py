import argparse
import json

from harness_common.config import apply_config_defaults, load_project_config


class TestLoadProjectConfig:
    def test_returns_empty_when_no_file(self, tmp_path):
        assert load_project_config(tmp_path) == {}

    def test_loads_full_config(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "harness.json").write_text(
            json.dumps({"deep_mode": {"max_iterations": 10}}), encoding="utf-8"
        )
        config = load_project_config(tmp_path)
        assert config == {"deep_mode": {"max_iterations": 10}}

    def test_loads_section(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "harness.json").write_text(
            json.dumps(
                {
                    "deep_mode": {"max_iterations": 10},
                    "test_coverage": {"max_cycles": 3},
                }
            ),
            encoding="utf-8",
        )
        assert load_project_config(tmp_path, section="deep_mode") == {
            "max_iterations": 10
        }
        assert load_project_config(tmp_path, section="test_coverage") == {
            "max_cycles": 3
        }

    def test_missing_section_returns_empty(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "harness.json").write_text(
            json.dumps({"deep_mode": {}}), encoding="utf-8"
        )
        assert load_project_config(tmp_path, section="test_coverage") == {}

    def test_invalid_json_returns_empty(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "harness.json").write_text(
            "not valid json", encoding="utf-8"
        )
        assert load_project_config(tmp_path) == {}

    def test_non_dict_top_level_returns_empty(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "harness.json").write_text(
            json.dumps([1, 2, 3]), encoding="utf-8"
        )
        assert load_project_config(tmp_path) == {}

    def test_non_dict_section_returns_empty(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "harness.json").write_text(
            json.dumps({"deep_mode": "not a dict"}), encoding="utf-8"
        )
        assert load_project_config(tmp_path, section="deep_mode") == {}


class TestApplyConfigDefaults:
    def test_overrides_defaults(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-iterations", type=int, default=8)
        config = {"max_iterations": 12}
        apply_config_defaults(parser, config)
        args = parser.parse_args([])
        assert args.max_iterations == 12

    def test_cli_overrides_config(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-iterations", type=int, default=8)
        config = {"max_iterations": 12}
        apply_config_defaults(parser, config)
        args = parser.parse_args(["--max-iterations", "5"])
        assert args.max_iterations == 5

    def test_key_map(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-turns", type=int, default=30)
        config = {"turns": 50}
        apply_config_defaults(parser, config, key_map={"turns": "max_turns"})
        args = parser.parse_args([])
        assert args.max_turns == 50

    def test_empty_config_is_noop(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-iterations", type=int, default=8)
        apply_config_defaults(parser, {})
        args = parser.parse_args([])
        assert args.max_iterations == 8
