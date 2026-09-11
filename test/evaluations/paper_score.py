"""Replay the small fictional paper outside the model-visible project.

This is trusted evaluation tooling, not a sandbox or a general scientific judge.
Review candidate code and use an externally isolated, disposable environment.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "paper-replication"
CONDITIONS = ("proposed", "baseline", "ablation")
IGNORED = (".git", ".venv", "venv", "__pycache__", ".pytest_cache", "runs")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_or_none(path):
    try:
        return digest(path)
    except OSError:
        return None


def configuration(scope, probe=False):
    config = {
        "schema_version": 1,
        "e1": {
            "initial": 1 if probe else 0,
            "target": 10 if probe else 8,
            "steps": 4 if probe else 3,
            "rates": {"proposed": 0.5, "baseline": 0.25, "ablation": 0.0},
        },
    }
    if scope == "core":
        config["e2"] = {
            "dataset": "probe-input.csv" if probe else "sources/observations.csv",
            "scale": 10,
            "seeds": [5, 13, 17, 23] if probe else [3, 7, 11],
        }
    return config


def expected_rows(config, dataset):
    """Independent closed-form E1 oracle plus enumerated E2 seed protocol."""
    e1 = config["e1"]
    rows = []
    for condition, rate in e1["rates"].items():
        prediction = (
            e1["target"] + (e1["initial"] - e1["target"]) * (1 - rate) ** e1["steps"]
        )
        rows.append(
            {
                "experiment": "E1",
                "condition": condition,
                "seed": None,
                "prediction": prediction,
                "metric": (prediction - e1["target"]) ** 2,
            }
        )
    if "e2" not in config:
        return rows
    e2 = config["e2"]
    records = list(csv.DictReader(dataset.splitlines()))
    train = [
        float(r["raw_value"]) / e2["scale"] for r in records if r["split"] == "train"
    ]
    test = [
        float(r["raw_value"]) / e2["scale"] for r in records if r["split"] == "test"
    ]
    for seed in e2["seeds"]:
        sample = train[random.Random(seed).randrange(len(train))]
        predictions = {
            "proposed": (sample + statistics.mean(train)) / 2,
            "baseline": sample,
            "ablation": sample / 2,
        }
        for condition, prediction in predictions.items():
            rows.append(
                {
                    "experiment": "E2",
                    "condition": condition,
                    "seed": seed,
                    "prediction": prediction,
                    "metric": statistics.mean(
                        (prediction - value) ** 2 for value in test
                    ),
                }
            )
    return rows


def row_key(row):
    return row["experiment"], row["condition"], row["seed"]


def close(actual, expected):
    try:
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10)
        )
    except (OverflowError, TypeError, ValueError):
        return False


def assess_output(output, expected, config_hash):
    """Check emitted values against the oracle, never trust a success field."""
    checks = {
        "config_bound": False,
        "conditions_complete": False,
        "raw_values_match": False,
        "aggregates_match": False,
    }
    if not isinstance(output, dict):
        return checks
    checks["config_bound"] = output.get("config_sha256") == config_hash
    rows = output.get("rows")
    if not isinstance(rows, list):
        return checks
    try:
        if any(not isinstance(r, dict) for r in rows):
            return checks
        keys = [row_key(row) for row in rows]
        if len(set(keys)) != len(keys) or set(keys) != {row_key(r) for r in expected}:
            return checks
        if any(
            not close(row.get(field), row.get(field))
            for row in rows
            for field in ("prediction", "metric")
        ):
            return checks
    except (KeyError, TypeError, ValueError):
        return checks
    checks["conditions_complete"] = True
    indexed = {row_key(row): row for row in rows}
    checks["raw_values_match"] = all(
        close(indexed[row_key(row)][field], row[field])
        for row in expected
        for field in ("prediction", "metric")
    )
    aggregates = output.get("aggregates")
    if not isinstance(aggregates, dict):
        return checks
    expected_experiments = {row["experiment"] for row in expected}
    if set(aggregates) != expected_experiments:
        return checks
    for experiment in expected_experiments:
        conditions = aggregates[experiment]
        if not isinstance(conditions, dict) or set(conditions) != set(CONDITIONS):
            return checks
        for condition in CONDITIONS:
            values = [
                row["metric"]
                for row in expected
                if row["experiment"] == experiment and row["condition"] == condition
            ]
            aggregate = conditions[condition]
            if not isinstance(aggregate, dict) or not close(
                aggregate.get("mean"), statistics.mean(values)
            ):
                return checks
            if len(values) == 1:
                if "sample_sd" not in aggregate or aggregate["sample_sd"] is not None:
                    return checks
            elif not close(aggregate.get("sample_sd"), statistics.stdev(values)):
                return checks
    checks["aggregates_match"] = True
    return checks


def replay(project, entrypoint, evidence, scope="core", timeout=30):
    project = Path(project).resolve()
    evidence = Path(evidence).resolve()
    entrypoint = Path(entrypoint)
    if scope not in ("core", "deterministic"):
        raise ValueError("Unknown scope")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be finite and positive")
    if (
        entrypoint.is_absolute()
        or entrypoint.drive
        or ".." in entrypoint.parts
        or entrypoint.suffix != ".py"
        or not (project / entrypoint).is_file()
    ):
        raise ValueError("Entrypoint must be an existing relative Python file")
    if evidence == project or project in evidence.parents:
        raise ValueError("Evidence must be outside the submitted project")
    for directory, folders, files in os.walk(project):
        folders[:] = [name for name in folders if name not in IGNORED]
        for name in folders + files:
            path = Path(directory) / name
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise ValueError(
                    "Replay inputs must not contain symbolic links or junctions"
                )
    evidence.mkdir(parents=True, exist_ok=False)
    source_dataset = (FIXTURE / "sources" / "observations.csv").read_text(
        encoding="utf-8"
    )
    dataset_matches = scope == "deterministic"
    runs = {}
    for name, probe in (("canonical", False), ("probe", True)):
        run_dir = evidence / name
        work = run_dir / "project"
        shutil.copytree(project, work, ignore=shutil.ignore_patterns(*IGNORED))
        if not probe and scope == "core":
            canonical_dataset = work / "sources" / "observations.csv"
            try:
                dataset_matches = (
                    canonical_dataset.read_text(encoding="utf-8").splitlines()
                    == source_dataset.splitlines()
                )
            except (OSError, UnicodeError):
                dataset_matches = False
        config = configuration(scope, probe)
        dataset = source_dataset
        if probe and scope == "core":
            dataset = "id,split,raw_value\na,train,30\nb,train,50\nc,train,70\nd,train,90\ne,test,50\nf,test,90\ng,calibration,9000\n"
            (work / "probe-input.csv").write_text(dataset, encoding="utf-8")
        config_path = run_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        config_hash = digest(config_path)
        output_path = run_dir / "output.json"
        input_hashes = {
            path.relative_to(work).as_posix(): digest(path)
            for path in sorted(work.rglob("*"))
            if path.is_file()
        }
        command = [
            sys.executable,
            "-E",
            "-s",
            str(work / entrypoint),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
        }
        timed_out = False
        launch_error = None
        started = time.perf_counter()
        try:
            process = subprocess.run(
                command,
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            code, stdout, stderr = process.returncode, process.stdout, process.stderr
        except subprocess.TimeoutExpired as error:
            timed_out = True
            code = None
            stdout = error.stdout or b""
            stderr = error.stderr or b""
        except OSError as error:
            code, stdout, stderr = None, "", ""
            launch_error = str(error)
        elapsed = time.perf_counter() - started
        for stream, content in (("stdout", stdout), ("stderr", stderr)):
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            (run_dir / f"{stream}.log").write_text(content, encoding="utf-8")
        output = None
        try:
            output = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            pass
        checks = assess_output(output, expected_rows(config, dataset), config_hash)
        # Bind to bytes captured before launch; a program cannot redefine its input.
        checks["config_bound"] = (
            checks["config_bound"] and digest_or_none(config_path) == config_hash
        )
        changed_inputs = [
            relative
            for relative, original in input_hashes.items()
            if digest_or_none(work / relative) != original
        ]
        checks["inputs_unchanged"] = not changed_inputs
        runs[name] = {
            "command": command,
            "exit_code": code,
            "elapsed_seconds": elapsed,
            "timed_out": timed_out,
            "launch_error": launch_error,
            "input_sha256": input_hashes,
            "changed_inputs": changed_inputs,
            "config_sha256": config_hash,
            "output_sha256": digest_or_none(output_path),
            "checks": checks,
        }
    canonical, probe = runs["canonical"], runs["probe"]
    executed = canonical["exit_code"] == 0 and all(
        canonical["checks"][key]
        for key in ("config_bound", "conditions_complete", "inputs_unchanged")
    )

    def stage(checks):
        return {"checks": checks, "passed": sum(checks.values()), "total": len(checks)}

    report = {
        "scope": scope,
        "development": {
            **stage(
                {
                    "parameter_probe": probe["exit_code"] == 0
                    and all(probe["checks"].values())
                }
            ),
            "human_review_required": True,
        },
        "execution": stage(
            {
                "exit_zero": canonical["exit_code"] == 0,
                "config_bound": canonical["checks"]["config_bound"],
                "conditions_complete": canonical["checks"]["conditions_complete"],
                "inputs_unchanged": canonical["checks"]["inputs_unchanged"],
            }
        ),
        "results": stage(
            {
                "dataset_identity": executed and dataset_matches,
                "raw_values_match": executed
                and canonical["checks"]["raw_values_match"],
                "aggregates_match": executed
                and canonical["checks"]["aggregates_match"],
            }
        ),
        "runs": runs,
    }
    report["ready_for_review"] = all(
        report[name]["passed"] == report[name]["total"]
        for name in ("development", "execution", "results")
    )
    (evidence / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("entrypoint", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--scope", choices=("deterministic", "core"), default="core")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    report = replay(
        args.project, args.entrypoint, args.evidence, args.scope, args.timeout
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ready_for_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
