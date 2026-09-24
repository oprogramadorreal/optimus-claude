"""The `## Intent` detection rule, pinned with worked examples.

`/optimus:pr` writes the Intent section and `/optimus:code-review` decides whether
to run its intent-vs-implementation checks by looking for one. The rule lived only
as an English sentence in `skills/pr/references/pr-template.md`, in two skills that
each had to reproduce it by reading. A one-sided drift is silent: the review skips
every Intent claim and still reports a clean pass.

The regex in that reference is now the single definition. These tests extract it
from the doc — not a copy — and run it against the cases the prose called out, so
editing the prose without editing the pattern (or the reverse) fails here.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PR_TEMPLATE = REPO_ROOT / "skills" / "pr" / "references" / "pr-template.md"
CODE_REVIEW_SKILL = REPO_ROOT / "skills" / "code-review" / "SKILL.md"
PR_SKILL = REPO_ROOT / "skills" / "pr" / "SKILL.md"


def _documented_pattern():
    """Pull the rule straight out of the reference that owns it."""
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    match = re.search(r"```regex\n(.+?)\n```", text, re.DOTALL)
    assert (
        match
    ), f"{PR_TEMPLATE.name} must carry the detection rule in a ```regex block"
    return re.compile(match.group(1))


PATTERN = _documented_pattern()

ACCEPTS = [
    "## Intent",
    "##  Intent",
    "## Intent ",
    "## intent",
    "## Intent {#intent}",
    "## Intent:",
]

REJECTS = [
    "## Intentional rollback",
    "## Intents",
    "## Intent and scope",
    " ## Intent",
    "> ## Intent",
    "### Intent",
    "##Intent",
    "Intent",
    "## Summary",
]


@pytest.mark.parametrize("line", ACCEPTS)
def test_accepts_a_real_intent_heading(line):
    assert PATTERN.match(line), f"should detect an Intent section: {line!r}"


@pytest.mark.parametrize("line", REJECTS)
def test_rejects_everything_else(line):
    assert not PATTERN.match(line), f"should not detect an Intent section: {line!r}"


def test_fenced_and_quoted_blocks_are_excluded_by_the_rule_text():
    """The regex is per-line; the doc carries the block exclusion the caller applies."""
    prose = PR_TEMPLATE.read_text(encoding="utf-8")
    assert "outside fenced code blocks and blockquotes" in prose, (
        "the block-exclusion half of the rule must stay stated — the pattern alone "
        "would match an Intent heading inside a ``` example"
    )


def test_both_sides_of_the_handoff_point_at_the_owning_reference():
    """Neither consumer may restate the rule; both must resolve to pr-template.md."""
    for consumer in (PR_SKILL, CODE_REVIEW_SKILL):
        text = consumer.read_text(encoding="utf-8")
        assert "pr-template.md" in text, (
            f"{consumer.relative_to(REPO_ROOT)} must reference pr-template.md "
            "rather than carrying its own copy of the Intent detection rule"
        )
