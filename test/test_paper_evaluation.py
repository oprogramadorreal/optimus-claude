"""Real local replays test the fixture scorer, not model or skill effectiveness."""

import importlib.util
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "paper_score", ROOT / "test" / "evaluations" / "paper_score.py"
)
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)

# Test subject uses iterative E1 updates; the evaluator uses a closed form.
REPRODUCER = """import argparse, csv, hashlib, json, random, statistics
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("--config")
p.add_argument("--output")
a = p.parse_args()
config_bytes = Path(a.config).read_bytes()
c = json.loads(config_bytes)
rows = []
e = c["e1"]
for name, rate in e["rates"].items():
    x = e["initial"]
    for _ in range(e["steps"]):
        x += rate * (e["target"] - x)
    rows.append(dict(experiment="E1", condition=name, seed=None,
                     prediction=x, metric=(x-e["target"])**2))
if "e2" in c:
    e = c["e2"]
    records = list(csv.DictReader(Path(e["dataset"]).read_text().splitlines()))
    train = [float(r["raw_value"])/e["scale"] for r in records if r["split"] == "train"]
    test = [float(r["raw_value"])/e["scale"] for r in records if r["split"] == "test"]
    for seed in e["seeds"]:
        sample = train[random.Random(seed).randrange(len(train))]
        for name, x in (("proposed",(sample+sum(train)/len(train))/2),
                        ("baseline",sample),("ablation",sample/2)):
            rows.append(dict(experiment="E2",condition=name,seed=seed,prediction=x,
                             metric=sum((x-y)**2 for y in test)/len(test)))
aggregates = {}
for row in rows:
    values = [r["metric"] for r in rows if r["experiment"] == row["experiment"]
              and r["condition"] == row["condition"]]
    aggregates.setdefault(row["experiment"], {})[row["condition"]] = dict(
        mean=statistics.mean(values),sample_sd=statistics.stdev(values) if len(values)>1 else None)
result = dict(config_sha256=hashlib.sha256(config_bytes).hexdigest(),
              rows=rows, aggregates=aggregates)
Path(a.output).write_text(json.dumps(result))
"""


@pytest.fixture
def project(tmp_path):
    project = tmp_path / "submission with spaces"
    shutil.copytree(SCORER.FIXTURE, project)
    (project / "reproduce.py").write_text(REPRODUCER, encoding="utf-8")
    return project


def run(project, tmp_path, **kwargs):
    return SCORER.replay(project, "reproduce.py", tmp_path / "evidence", **kwargs)


def test_oracle_agrees_with_independently_known_paper_values():
    dataset = (SCORER.FIXTURE / "sources" / "observations.csv").read_text()
    rows = SCORER.expected_rows(SCORER.configuration("core"), dataset)
    assert [r["metric"] for r in rows[:3]] == [1, 11.390625, 64]
    proposed = [
        r["metric"]
        for r in rows
        if r["experiment"] == "E2" and r["condition"] == "proposed"
    ]
    assert proposed == [6.25, 4.25, 4.25]
    assert statistics.mean(proposed) == pytest.approx(59 / 12)
    assert statistics.stdev(proposed) == pytest.approx((4 / 3) ** 0.5)


@pytest.mark.parametrize("scope", ["core", "deterministic"])
def test_real_replay_passes_computation_without_claiming_replication(
    project, tmp_path, scope
):
    (project / "runs").mkdir()
    (project / "runs" / "stale.json").write_text('{"success":true}')
    report = run(project, tmp_path, scope=scope)
    assert report["ready_for_review"] is True
    assert report["development"]["human_review_required"] is True
    assert "replicated" not in report
    for name, execution in report["runs"].items():
        assert execution["exit_code"] == 0
        assert execution["elapsed_seconds"] > 0
        assert execution["input_sha256"]["reproduce.py"] == SCORER.digest(
            project / "reproduce.py"
        )
        assert execution["output_sha256"]
        assert not (tmp_path / "evidence" / name / "project" / "runs").exists()
        assert (tmp_path / "evidence" / name / "stdout.log").is_file()


def test_success_claim_and_staged_results_do_not_count_as_execution(project, tmp_path):
    (project / "reproduce.py").write_text('print("All experiments reproduced")')
    (project / "output.json").write_text('{"success":true}')
    report = run(project, tmp_path)
    assert report["execution"]["checks"]["exit_zero"] is True
    assert report["execution"]["checks"]["conditions_complete"] is False
    assert report["results"]["passed"] == 0
    assert report["ready_for_review"] is False


def test_wrong_variability_is_execution_but_not_reproduced_result(project, tmp_path):
    (project / "reproduce.py").write_text(
        REPRODUCER.replace("statistics.stdev(values)", "statistics.pstdev(values)")
    )
    report = run(project, tmp_path)
    assert report["execution"]["passed"] == report["execution"]["total"]
    assert report["results"]["checks"]["raw_values_match"] is True
    assert report["results"]["checks"]["aggregates_match"] is False


def test_wrong_split_can_execute_but_fails_results(project, tmp_path):
    (project / "reproduce.py").write_text(
        REPRODUCER.replace('r["split"] == "train"', 'r["split"] != "calibration"')
    )
    report = run(project, tmp_path)
    assert report["execution"]["passed"] == report["execution"]["total"]
    assert report["results"]["checks"]["raw_values_match"] is False


def test_canned_canonical_values_fail_changed_parameter_probe(project, tmp_path):
    canonical = repr(SCORER.configuration("core"))
    script = REPRODUCER.replace("c = json.loads(config_bytes)", f"c = {canonical}")
    (project / "reproduce.py").write_text(script)
    report = run(project, tmp_path)
    assert report["results"]["passed"] == report["results"]["total"]
    assert report["development"]["checks"]["parameter_probe"] is False
    assert report["ready_for_review"] is False


@pytest.mark.parametrize(
    "extra",
    [
        "\nraise SystemExit(7)\n",
        "\nPath(a.config).write_text('{}')\n",
        "\nPath(a.config).unlink()\n",
        "\nPath('sources/observations.csv').write_text('changed')\n",
    ],
)
def test_nonzero_exit_or_changed_config_cannot_validate_results(
    project, tmp_path, extra
):
    (project / "reproduce.py").write_text(REPRODUCER + extra)
    report = run(project, tmp_path)
    assert report["results"]["passed"] == 0
    assert report["ready_for_review"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "rows.pop()",
        "rows.append(rows[0])",
        "rows[0]['metric'] = float('nan')",
        "rows[0]['metric'] = 10**1000",
    ],
)
def test_missing_duplicate_and_nonfinite_measurements_fail_execution(
    project, tmp_path, mutation
):
    script = REPRODUCER.replace(
        "Path(a.output).write_text(json.dumps(result))",
        f"{mutation}\nPath(a.output).write_text(json.dumps(result))",
    )
    (project / "reproduce.py").write_text(script)
    report = run(project, tmp_path)
    assert report["execution"]["checks"]["conditions_complete"] is False
    assert report["results"]["passed"] == 0


def test_timeout_is_preserved_as_failure(project, tmp_path):
    (project / "reproduce.py").write_text("import time\ntime.sleep(2)\n")
    report = run(project, tmp_path, timeout=0.05)
    assert report["runs"]["canonical"]["timed_out"] is True
    assert report["runs"]["canonical"]["exit_code"] is None
    assert report["results"]["passed"] == 0


def test_replay_refuses_overwrite_and_entrypoint_escape(project, tmp_path):
    evidence = tmp_path / "existing evidence"
    evidence.mkdir()
    marker = evidence / "keep.txt"
    marker.write_bytes(b"owned by reviewer")
    with pytest.raises(FileExistsError):
        SCORER.replay(project, "reproduce.py", evidence)
    assert marker.read_bytes() == b"owned by reviewer"
    with pytest.raises(ValueError, match="relative Python"):
        SCORER.replay(project, "../elsewhere.py", tmp_path / "new evidence")
    with pytest.raises(ValueError, match="outside"):
        SCORER.replay(project, "reproduce.py", project / "evidence")


def test_cli_emits_inspectable_json_and_rejects_nonfinite_timeout(project, tmp_path):
    scorer_path = str(ROOT / "test" / "evaluations" / "paper_score.py")
    command = [
        sys.executable,
        scorer_path,
        str(project),
        "reproduce.py",
        "--evidence",
        str(tmp_path / "cli evidence"),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["ready_for_review"] is True
    refused = subprocess.run(
        command + ["--timeout", "nan"], capture_output=True, text=True
    )
    assert refused.returncode == 2
    assert "finite and positive" in refused.stderr


def test_new_cases_keep_existing_consumer_shape_and_isolate_oracle():
    root = ROOT / "test" / "evaluations"
    cases = json.loads((root / "cases.json").read_text())["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        fixture = root / case["fixture"]
        assert fixture.is_dir()
        assert isinstance(case["task"], str) and case["task"]
        assert not list(fixture.rglob("paper_score.py"))
        assert not list(fixture.rglob("paper-review.md"))
