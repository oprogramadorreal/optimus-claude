"""Deterministic fixture oracles; run outside the model-visible project."""

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def load_module(path):
    spec = importlib.util.spec_from_file_location("evaluation_subject", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guidance(project):
    catalog_module = load_module(project / "catalog.py")
    items = {"AbC": "first", "abc": "second"}
    catalog = catalog_module.Catalog(items)
    checks = {
        "trim_spaces": catalog.lookup(" AbC ") == "first",
        "trim_tabs": catalog.lookup("\tabc\n") == "second",
        "preserve_case": catalog.lookup("AbC") != catalog.lookup("abc"),
        "unknown": catalog.lookup("unknown") is None,
        "empty": catalog.lookup(" \t") is None,
        "mapping_unchanged": items == {"AbC": "first", "abc": "second"},
    }
    items["later"] = "third"
    checks["observe_caller_update"] = catalog.lookup("later") == "third"
    return checks


def review(project):
    app = load_module(project / "app.py")
    try:
        empty_bug = app.average([]) is not None
    except ZeroDivisionError:
        empty_bug = True
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE invoices (amount TEXT, cents INTEGER)")
        connection.execute("INSERT INTO invoices VALUES ('12.75', NULL)")
        connection.executescript(
            (project / "Migrations/001_money.sql").read_text(encoding="utf-8")
        )
        cents = connection.execute("SELECT cents FROM invoices").fetchone()[0]
        connection.executescript(
            (project / "Migrations/schema.generated.sql").read_text(encoding="utf-8")
        )
    return {
        "seeded_empty_input_bug_reproduces": empty_bug,
        "seeded_money_bug_reproduces": cents == 1200,
        "guarded_control_valid": app.first_if_present([]) is None,
        "nonempty_control_valid": app.average([2, 4]) == 3,
        "generated_control_loads": True,
    }


if __name__ == "__main__":
    cases = {"guidance-app": guidance, "review-app": review}
    if len(sys.argv) != 3 or sys.argv[1] not in cases:
        raise SystemExit("Usage: score.py guidance-app|review-app <copied-project>")
    results = cases[sys.argv[1]](Path(sys.argv[2]).resolve())
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if all(results.values()) else 1)
