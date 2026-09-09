"""Run install.cmd with Python module stubs; never install packages or a venv."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe quoting")
@pytest.mark.parametrize("pip_upgrade_exit", [0, 7])
def test_install_paths_with_spaces_and_upgrade_failure(tmp_path, pip_upgrade_exit):
    root = tmp_path / "checkout with spaces"
    root.mkdir()
    shutil.copyfile(
        Path(__file__).resolve().parent.parent / "install.cmd", root / "install.cmd"
    )
    (root / "requirements-dev.txt").write_text("# stub\n", encoding="utf-8")
    # Current-directory modules precede stdlib/site-packages for `python -m`.
    # Use the real interpreter while replacing every mutating module it invokes.
    common = "import json, pathlib, sys\nwith open('calls.jsonl', 'a') as out: out.write(json.dumps(sys.argv) + '\\n')\n"
    (root / "venv.py").write_text(
        common
        + "target = pathlib.Path(sys.argv[1])\nassert len(sys.argv) == 2\n(target / 'Scripts').mkdir(parents=True)\n(target / 'Scripts' / 'activate.bat').write_text('@echo off\\nexit /b 0\\n')\n",
        encoding="utf-8",
    )
    (root / "pip.py").write_text(
        common + f"sys.exit({pip_upgrade_exit} if '--upgrade' in sys.argv else 0)\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PATH"] = (
        str(Path(sys.executable).parent)
        + os.pathsep
        + str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
    )
    result = subprocess.run(
        [env.get("COMSPEC", "cmd.exe"), "/d", "/c", "install.cmd"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    calls = [
        json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()
    ]
    assert calls[0][1:] == [str(root / ".venv")]
    if pip_upgrade_exit:
        assert result.returncode == 1
        assert len(calls) == 2
        assert "Failed to upgrade pip" in result.stdout
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert calls[-1][1:] == ["install", "-r", str(root / "requirements-dev.txt")]
