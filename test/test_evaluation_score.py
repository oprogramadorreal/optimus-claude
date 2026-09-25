"""Real runs of the fixture oracle in test/evaluations/score.py."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVALUATIONS = ROOT / "test" / "evaluations"


def run_scorer(*arguments):
    return subprocess.run(
        [sys.executable, str(EVALUATIONS / "score.py"), *map(str, arguments)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=EVALUATIONS,
    )


def test_guidance_oracle_rejects_seeded_fixture_and_accepts_trimmed_lookup(tmp_path):
    fixture = EVALUATIONS / "fixtures" / "guidance-app"
    assert run_scorer("guidance-app", fixture).returncode == 1
    project = tmp_path / "fixed project"
    shutil.copytree(fixture, project)
    catalog = project / "catalog.py"
    catalog.write_text(
        catalog.read_text(encoding="utf-8").replace(
            "get(identifier)", "get(identifier.strip())"
        ),
        encoding="utf-8",
    )
    completed = run_scorer("guidance-app", project)
    assert completed.returncode == 0, completed.stdout
    assert not list(project.rglob("__pycache__"))


def test_review_oracle_confirms_seeded_ground_truth():
    completed = run_scorer("review-app", EVALUATIONS / "fixtures" / "review-app")
    assert completed.returncode == 0, completed.stdout
    assert all(json.loads(completed.stdout).values())


@pytest.mark.parametrize(
    "arguments",
    [["review-app"], ["unknown-case", "."], ["review-app", "missing project"]],
)
def test_usage_errors_exit_2_not_the_oracle_failure_code(arguments):
    completed = run_scorer(*arguments)
    assert completed.returncode == 2
    assert "Usage" in completed.stderr
