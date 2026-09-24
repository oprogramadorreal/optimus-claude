"""Drive single functions extracted from the shipped restrict-paths.sh hook template.

scripts/test-hooks.sh covers the hook end to end; these cases need pytest
parametrization (an optional Bash 3.2 via BASH32_BIN) or a stubbed `cd`.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
from harness_common.runner import _find_bash

ROOT = Path(__file__).resolve().parents[1]
RESTRICT = ROOT / "skills/permissions/templates/hooks/restrict-paths.sh"
BASH = _find_bash()


def _bash(script, tmp_path):
    driver = tmp_path / "driver.sh"
    driver.write_text('export PATH="/usr/bin:/bin:$PATH"\n' + script, encoding="utf-8")
    return subprocess.run(
        [BASH, str(driver)],
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        cwd=tmp_path,
    )


def test_normalize_keeps_parent_when_cd_fails(tmp_path):
    source = RESTRICT.read_text(encoding="utf-8")
    functions = "\n".join(
        re.search(rf"^{name}\(\) \{{.*?^\}}", source, re.M | re.S).group()
        for name in ("collapse_dot_segments", "normalize")
    )
    # Parent exists, but traversal fails: an access-control/race outcome. No real
    # permissions are changed, so this also works under an administrator/root.
    result = _bash(
        functions
        + '\ncommand() { if [[ "$1" == -v && ( "$2" == realpath || "$2" == cygpath ) ]]; then return 1; fi; builtin command "$@"; }\n'
        + 'cd() { return 1; }\nnormalize "$PWD/source.txt"\n',
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith(f"/{tmp_path.name}/source.txt"), result.stdout


@pytest.mark.parametrize("shell", [BASH, os.environ.get("BASH32_BIN")])
def test_precious_casefold_on_available_bash_versions(tmp_path, shell):
    if not shell:
        pytest.skip("Set BASH32_BIN to exercise an installed Bash 3.2")
    source = RESTRICT.read_text(encoding="utf-8")
    functions = "\n".join(
        re.search(rf"^{name}\(\) \{{.*?^\}}", source, re.M | re.S).group()
        for name in ("basename_of", "precious_basename")
    )
    driver = tmp_path / "casefold.sh"
    driver.write_text(
        'export PATH="/usr/bin:/bin:$PATH"\n'
        + functions
        + '\nOSTYPE=darwin\nprecious_basename "/project/.ENV.LOCAL"\nprintf "%s" "$_basename"\n'
    )
    result = subprocess.run(
        [shell, str(driver)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ".env.local"
