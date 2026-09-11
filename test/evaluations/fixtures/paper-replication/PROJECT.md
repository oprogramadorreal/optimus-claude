# Paper preparation fixture

This project contains an original fictional paper for inexpensive skill evaluations.
Its sources are local Markdown and CSV; no external publication, author, permission,
dataset or reported experiment is implied. Read `sources/paper.md` and its cited
supporting materials. The task selects the reproduction scope.

During preparation, create durable context only. Do not implement experiments,
install packages, create an environment, or change these source files. The later
implementing session may use Python's standard library. All source files are safe
to commit. Record uncertainties and scope honestly.

For the separate implementation/replay stage, provide a relative Python entrypoint
that accepts `--config <JSON-path> --output <JSON-path>`. The evaluator supplies a
fresh config and output path. It may vary parameters to check that the program
computes results. Those probes are code checks, not new paper claims.

Config shape:

```json
{"schema_version":1,"e1":{"initial":0,"target":8,"steps":3,"rates":{"proposed":0.5,"baseline":0.25,"ablation":0}},"e2":{"dataset":"sources/observations.csv","scale":10,"seeds":[3,7,11]}}
```

`e2` is omitted for an E1-only run. Honor the configured dataset, rates, steps,
initial value, target, scale and seeds. Write JSON with `config_sha256` (SHA-256 of
the supplied config's bytes), `rows`, and `aggregates`. Each row has `experiment`
(`E1` or `E2`), `condition` (`proposed`, `baseline`, or `ablation`), `seed` (`null`
for E1), `prediction`, and `metric`. Include every configured condition/seed once.
`aggregates` maps experiment to condition to `{"mean": number, "sample_sd": number
or null}`. Use `null` for singleton SD. Save ordinary generated outputs under
`runs/`; the evaluator omits that directory, caches and environments from replay.

This interface is fixture-specific. It is not a required paper-init artifact or
a production entrypoint convention. Independently recomputed numbers alone do not
prove method fidelity; source review and replay evidence are separate checks.
