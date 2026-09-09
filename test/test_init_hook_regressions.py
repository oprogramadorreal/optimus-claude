"""Execute installed-hook fixtures; formatter stubs record the actual cwd/argv."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from harness_common.runner import _find_bash

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "skills/init/templates/hooks"
RESTRICT = ROOT / "skills/permissions/templates/hooks/restrict-paths.sh"
BASH = _find_bash()
NODE = shutil.which("node")


def _bash(script, tmp_path, *args, payload="", env=None):
    driver = tmp_path / "driver.sh"
    driver.write_text('export PATH="/usr/bin:/bin:$PATH"\n' + script, encoding="utf-8")
    return subprocess.run(
        [BASH, str(driver), *map(str, args)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        cwd=tmp_path,
        env={**os.environ, **(env or {})},
    )


@pytest.mark.skipif(not NODE, reason="Node is not installed")
@pytest.mark.parametrize("package_type", ["commonjs", "module"])
@pytest.mark.parametrize(
    "filename", ["source.ts", "%OPTIMUS_HOOK_LITERAL%.ts", "café source.ts"]
)
def test_node_hook_preserves_literal_path_in_each_package_type(
    tmp_path, package_type, filename
):
    project = tmp_path / "project with spaces"
    prettier = project / "node_modules/prettier"
    prettier.mkdir(parents=True)
    (project / "package.json").write_text(json.dumps({"type": package_type}))
    (prettier / "package.json").write_text(json.dumps({"bin": "cli.cjs"}))
    (prettier / "cli.cjs").write_text(
        "require('fs').writeFileSync(process.env.HOOK_LOG, "
        "JSON.stringify({cwd:process.cwd(),argv:process.argv.slice(2)}));"
    )
    template = HOOKS / "format-node.cjs"
    installed = project / template.name
    shutil.copyfile(template, installed)
    target = project / filename
    target.write_text("const answer=1\n")
    log = tmp_path / "argv.json"
    result = subprocess.run(
        [NODE, str(installed)],
        input=json.dumps(
            {"tool_input": {"file_path": str(target)}}, ensure_ascii=False
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=project,
        env={**os.environ, "HOOK_LOG": str(log), "OPTIMUS_HOOK_LITERAL": "wrong-file"},
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert log.exists(), result.stderr
    call = json.loads(log.read_text(encoding="utf-8"))
    assert Path(call["cwd"]) == project
    assert call["argv"][-1] == str(target)
    assert "--write" in call["argv"]


@pytest.mark.parametrize(
    "version, prefix", [("0.30.6", []), ("1.0.0", ["format"]), ("1.2.5", ["format"])]
)
@pytest.mark.parametrize("native_path", [False, True])
def test_csharp_hook_uses_package_cwd_and_pinned_cli_syntax(
    tmp_path, version, prefix, native_path
):
    package = tmp_path / "package with spaces"
    package.mkdir()
    target = package / "source.cs"
    target.write_text("class C{}")
    log = tmp_path / "calls.txt"
    result = _bash(
        "dotnet() {\n"
        '  if [[ "$*" == *--version ]]; then printf "%s\\n" "$CSHARPIER_VERSION"; return; fi\n'
        '  { pwd; printf "%s\\n" "$@"; } > "$HOOK_LOG"\n'
        '}\nexport -f dotnet\nbash "$1"\n',
        tmp_path,
        HOOKS / "format-csharp.sh",
        payload=json.dumps(
            {
                "tool_input": {
                    "file_path": str(target) if native_path else target.as_posix()
                }
            }
        ),
        env={"CSHARPIER_VERSION": version, "HOOK_LOG": log.as_posix()},
    )
    assert result.returncode == 0, result.stderr
    assert log.exists(), result.stderr
    lines = log.read_text().splitlines()
    assert lines[0].endswith("/package with spaces"), lines
    assert lines[1:-1] == ["tool", "run", "csharpier", "--", *prefix], lines
    assert lines[-1].endswith("/package with spaces/source.cs"), lines


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


@pytest.mark.parametrize("edition", ["2015", "2018", "2021", "2024", None])
def test_rust_hook_requires_explicit_nearest_config_edition(tmp_path, edition):
    (tmp_path / ".git").mkdir()
    (tmp_path / "rustfmt.toml").write_text('edition = "2015"\n')
    package = tmp_path / "rust package"
    package.mkdir()
    config = package / ".rustfmt.toml"
    config.write_text(
        f'edition = "{edition}"\nstyle_edition = "{edition}"\n'
        if edition
        else "max_width = 80\n"
    )
    target = package / "source.rs"
    target.write_text("fn main(){}\n")
    log = tmp_path / "rust-call.txt"
    result = _bash(
        'rustfmt() { { pwd; printf "%s\\n" "$@"; } > "$HOOK_LOG"; }\n'
        'export -f rustfmt\nbash "$1"\n',
        tmp_path,
        HOOKS / "format-rust.sh",
        payload=json.dumps({"tool_input": {"file_path": str(target)}}),
        env={"HOOK_LOG": log.as_posix()},
    )
    assert result.returncode == 0, result.stderr
    if edition:
        assert log.exists(), result.stderr
        lines = log.read_text().splitlines()
        assert lines[0].endswith("/rust package")
        assert lines[1] == "--config-path"
        assert lines[2].endswith("/rust package/.rustfmt.toml")
        assert lines[3].endswith("/rust package/source.rs")
        assert (
            target.read_text() == "fn main(){}\n"
        )  # The fixture formatter is a recorder.
    else:
        assert not log.exists()
        assert "cargo fmt" in result.stderr


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
