# Coverage command detection

Used by `/optimus:tdd` for the `### Coverage` section of its summary block. This reference covers only *how to detect the command* and *when to omit the section*; the consuming skill decides **when** to run it (before/after its build) and records the Before and After percentages itself.

## Detecting the command

Look for a coverage command in this order; use the first one found:

1. The coverage section of `testing.md`, if it documents one.
2. A test-runner coverage flag — e.g. `vitest --coverage`, `pytest --cov=.`, `go test -cover`, `dotnet test --collect:"XPlat Code Coverage"`.
3. A `package.json` coverage script.

## When to omit

Emit the `### Coverage` section only when **both** the Before and After runs produced a real percentage. Omit it entirely if no coverage command is found, or if either run fails or returns no parseable number — never emit a half-filled block (a `Before` with a blank `After`, or vice versa).
