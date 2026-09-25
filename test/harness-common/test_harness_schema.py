"""The harness JSON contract, enforced against its schema instead of its prose.

``references/harness-mode.md`` and ``coverage-harness-mode.md`` used to describe
every field's semantics in prose, with a third copy of the shape hand-written
inside a test. Three copies drift silently: renaming a field in the docs left the
parser rejecting real subagent output, and nothing failed until a deep run
terminated with ``parse-failure`` on every iteration.

The schemas under ``references/schemas/`` are now the single definition. These
tests check that the golden fixtures satisfy them, that the fixtures survive
``cli parse``, and that the docs point subagents at both the schema and the
fixture by real path — so a one-sided rename fails here rather than in production.

No ``jsonschema`` dependency: the project is stdlib-only, and ``_validate`` below
covers exactly the keywords these two schemas use. It raises on an unknown
keyword rather than ignoring it, so a schema edit cannot silently go unchecked.
"""

import json
from pathlib import Path

import pytest
from harness_common import cli

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "references" / "schemas"
# Not test/fixtures/ — that path is gitignored for generated skill-test output.
# These are committed test data and must survive a fresh clone.
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

DEEP_SCHEMA = SCHEMA_DIR / "harness-output.schema.json"
COVERAGE_SCHEMA = SCHEMA_DIR / "coverage-harness-output.schema.json"
DEEP_FIXTURE = FIXTURE_DIR / "harness-output.golden.json"
COVERAGE_FIXTURE = FIXTURE_DIR / "coverage-harness-output.golden.json"

DEEP_DOC = REPO_ROOT / "references" / "harness-mode.md"
COVERAGE_DOC = REPO_ROOT / "references" / "coverage-harness-mode.md"

# Keywords _validate understands. Anything else in a schema is a bug in the
# schema or a gap in this validator — either way it must fail loudly.
_SUPPORTED = {
    "$schema",
    "$id",
    "$defs",
    "$ref",
    "title",
    "description",
    "type",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "enum",
    "minimum",
    "maxLength",
}

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _resolve(ref, root):
    """Resolve a local '#/$defs/name' pointer against the schema root."""
    assert ref.startswith("#/"), f"only local refs are supported, got {ref}"
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _check_type(value, expected, path, errors):
    names = [expected] if isinstance(expected, str) else expected
    for name in names:
        py = _JSON_TYPES[name]
        # bool is a subclass of int in Python; JSON treats them as distinct.
        if name in ("integer", "number") and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return
    errors.append(f"{path}: expected type {expected}, got {type(value).__name__}")


def _validate(value, schema, root, path="$", errors=None):
    """Validate ``value`` against ``schema``. Returns a list of error strings."""
    if errors is None:
        errors = []

    unknown = set(schema) - _SUPPORTED
    assert not unknown, f"{path}: schema uses unsupported keywords {sorted(unknown)}"

    if "$ref" in schema:
        return _validate(value, _resolve(schema["$ref"], root), root, path, errors)

    if "type" in schema:
        before = len(errors)
        _check_type(value, schema["type"], path, errors)
        if len(errors) > before:
            return errors  # wrong type — deeper checks would be noise

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")

    if "minimum" in schema and isinstance(value, (int, float)):
        if value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")

    if "maxLength" in schema and isinstance(value, str):
        if len(value) > schema["maxLength"]:
            errors.append(
                f"{path}: length {len(value)} > maxLength {schema['maxLength']}"
            )

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing required property {name!r}")
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in properties:
                    errors.append(f"{path}: unexpected property {name!r}")
        for name, sub in properties.items():
            if name in value:
                _validate(value[name], sub, root, f"{path}.{name}", errors)

    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _validate(item, schema["items"], root, f"{path}[{i}]", errors)

    return errors


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMA_FIXTURE_PAIRS = [
    pytest.param(DEEP_SCHEMA, DEEP_FIXTURE, id="deep"),
    pytest.param(COVERAGE_SCHEMA, COVERAGE_FIXTURE, id="coverage"),
]


@pytest.mark.parametrize("schema_path,fixture_path", SCHEMA_FIXTURE_PAIRS)
def test_golden_fixture_satisfies_schema(schema_path, fixture_path):
    schema = _load(schema_path)
    errors = _validate(_load(fixture_path), schema, schema)
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("schema_path,fixture_path", SCHEMA_FIXTURE_PAIRS)
def test_golden_fixture_round_trips_through_cli_parse(
    schema_path, fixture_path, tmp_path, capsys
):
    """The documented shape must survive the parser the orchestrator actually runs."""
    payload = _load(fixture_path)
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "preamble the subagent wrote before its block\n"
        "```json:harness-output\n" + json.dumps(payload, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    assert cli.main(["parse", "--input-file", str(raw)]) == 0
    assert json.loads(capsys.readouterr().out) == payload


def test_validator_rejects_a_broken_instance():
    """Guard the guard: a validator that always passes would hide every drift."""
    schema = _load(DEEP_SCHEMA)
    payload = _load(DEEP_FIXTURE)
    del payload["no_actionable_fixes"]
    payload["new_findings"][0]["severity"] = "Nitpick"
    payload["new_findings"][0]["unexpected"] = True
    errors = _validate(payload, schema, schema)
    assert any("no_actionable_fixes" in e for e in errors)
    assert any("Nitpick" in e for e in errors)
    assert any("unexpected" in e for e in errors)


def test_no_actionable_fixes_matches_the_findings_it_describes():
    """The one rule JSON Schema cannot express, checked against the runtime guard.

    ``no_actionable_fixes`` is true only when no finding captured a swap pair. A
    stale ``false`` makes the orchestrator keep iterating on nothing; a stale
    ``true`` ends the run while real fixes are still pending. The fixture's flag
    must equal what ``cli._promote_actionable_fixes`` derives from its findings,
    so the worked instance and the guard cannot drift apart.
    """
    payload = _load(DEEP_FIXTURE)

    probe = {**payload, "no_actionable_fixes": True, "fixes_applied": []}
    cli._promote_actionable_fixes(probe)
    assert probe["no_actionable_fixes"] is payload["no_actionable_fixes"]

    barren = {
        **payload,
        "new_findings": [payload["new_findings"][2]],
        "fixes_applied": [],
        "no_actionable_fixes": True,
    }
    cli._promote_actionable_fixes(barren)
    assert (
        barren["no_actionable_fixes"] is True and barren["fixes_applied"] == []
    ), "fixture index 2 must stay the unconfirmed, unfixed finding this rule keys on"


@pytest.mark.parametrize(
    "schema_path,fixture_path,doc_path",
    [
        pytest.param(DEEP_SCHEMA, DEEP_FIXTURE, DEEP_DOC, id="deep"),
        pytest.param(COVERAGE_SCHEMA, COVERAGE_FIXTURE, COVERAGE_DOC, id="coverage"),
    ],
)
def test_docs_route_subagents_to_the_schema_and_fixture(
    schema_path, fixture_path, doc_path
):
    """The doc must send the subagent to the schema and the fixture, by real path.

    The docs used to inline a third copy of the shape, which is why the older
    version of this test asserted every required field name appeared in the prose.
    That copy is gone: the schema defines the contract and the fixture shows it.
    What has to hold now is that the doc actually points at both, and that both
    paths resolve — a moved or renamed file would otherwise leave the subagent
    with a pointer to nothing and no shape to emit.
    """
    doc = doc_path.read_text(encoding="utf-8")

    for target in (schema_path, fixture_path):
        assert target.exists(), f"{target} does not exist"
        rel = target.relative_to(REPO_ROOT).as_posix()
        assert rel in doc, f"{doc_path.name} does not point at {rel}"
