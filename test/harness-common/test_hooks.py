import os
import stat

from harness_common.hooks import run_hook


class TestRunHook:
    def _create_hook(self, hooks_dir, name, script="#!/bin/bash\nexit 0\n"):
        hook = hooks_dir / name
        hook.write_text(script, encoding="utf-8")
        hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
        return hook

    def test_runs_existing_hook(self, tmp_path):
        self._create_hook(tmp_path, "pre-iteration")
        assert run_hook(str(tmp_path), "pre-iteration") is True

    def test_returns_false_when_no_hook(self, tmp_path):
        assert run_hook(str(tmp_path), "nonexistent") is False

    def test_returns_false_when_hooks_dir_empty(self):
        assert run_hook("", "pre-iteration") is False

    def test_returns_false_when_hooks_dir_none(self):
        assert run_hook(None, "pre-iteration") is False

    def test_passes_env_vars(self, tmp_path):
        self._create_hook(
            tmp_path,
            "pre-iteration",
            '#!/bin/bash\necho "$HARNESS_ITERATION" > '
            + str(tmp_path / "out.txt")
            + "\n",
        )
        run_hook(
            str(tmp_path),
            "pre-iteration",
            env_vars={"HARNESS_ITERATION": "3"},
        )
        out = (tmp_path / "out.txt").read_text(encoding="utf-8").strip()
        assert out == "3"

    def test_nonzero_exit_returns_false(self, tmp_path):
        self._create_hook(tmp_path, "post-iteration", "#!/bin/bash\nexit 1\n")
        assert run_hook(str(tmp_path), "post-iteration") is False

    def test_harness_event_env_set(self, tmp_path):
        self._create_hook(
            tmp_path,
            "my-event",
            '#!/bin/bash\necho "$HARNESS_EVENT" > '
            + str(tmp_path / "event.txt")
            + "\n",
        )
        run_hook(str(tmp_path), "my-event")
        out = (tmp_path / "event.txt").read_text(encoding="utf-8").strip()
        assert out == "my-event"

    def test_missing_dir_returns_false(self):
        assert run_hook("/nonexistent/path", "pre-iteration") is False
