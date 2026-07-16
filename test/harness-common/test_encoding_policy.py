"""Policy: text-mode subprocess calls must pin the codec, never the locale.

``text=True`` (or ``universal_newlines=True``) without ``encoding=`` decodes
child output with ``locale.getpreferredencoding(False)`` — cp1252 on Western
Windows — where a single non-decodable byte (e.g. the 0x9D of a UTF-8 ")
kills the subprocess reader thread and silently returns empty stdout/stderr.
Every text-mode subprocess call in shipped Python code must therefore pass
``encoding="utf-8"`` (paired with ``errors="replace"`` for arbitrary output).

Enforced via AST so it also covers calls routed through the ``_run``/``run_fn``
injection seams, and fails on any future call site added without the kwarg.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

POLICED_FILES = [
    *sorted((REPO_ROOT / "scripts" / "harness_common").glob("*.py")),
    REPO_ROOT / ".claude" / "hooks" / "format-python.py",
    REPO_ROOT / "skills" / "init" / "templates" / "hooks" / "format-python.py",
]


def _is_true(node):
    return isinstance(node, ast.Constant) and node.value is True


def _violations(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        text_kw = keywords.get("text", keywords.get("universal_newlines"))
        if text_kw is None or not _is_true(text_kw):
            continue
        if "encoding" not in keywords:
            found.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    return found


def test_policed_files_exist():
    assert POLICED_FILES, "policy file list resolved to nothing"
    missing = [str(p) for p in POLICED_FILES if not p.exists()]
    assert not missing, f"policed files moved or deleted: {missing}"


def test_text_mode_subprocess_calls_pin_utf8():
    violations = [v for path in POLICED_FILES for v in _violations(path)]
    assert not violations, (
        "text=True call(s) without encoding= — decoding follows the machine "
        "locale and silently loses output on cp1252 Windows: " + ", ".join(violations)
    )
