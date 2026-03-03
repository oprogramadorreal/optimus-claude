# Framework and Coverage Tooling Recommendations

Recommend the most popular test framework and coverage tooling for each tech stack. These are starting points — analyze the actual project to decide.

| Stack | Recommended Framework | Coverage Tooling | Report Tool |
|-------|----------------------|-----------------|-------------|
| Node.js/TypeScript + Vite | Vitest | Built-in (c8/v8) | Built-in |
| Node.js/TypeScript (other) | Jest | jest --coverage (istanbul) | Built-in |
| Python | pytest | pytest-cov | Built-in (`--cov-report=html`) |
| Java (Maven/Gradle) | JUnit 5 | JaCoCo | Built-in (Maven/Gradle plugin) |
| C#/.NET | xUnit | coverlet | dotnet-reportgenerator-globaltool |
| Go | built-in `testing` | built-in `go test -cover` | Built-in (`go tool cover -html`) |
| Rust | built-in `#[test]` | cargo-tarpaulin or cargo-llvm-cov | Built-in (tarpaulin: `--out Html`, llvm-cov: `--html`) |
| PHP | PHPUnit | built-in coverage (requires Xdebug or PCOV) | Built-in |
| Ruby | RSpec | SimpleCov | Built-in |
| C/C++ | Google Test (gtest) or Catch2 | gcov/lcov | genhtml (from lcov) |
| Angular | Vitest | built-in `--coverage` (v8 provider) | Built-in |

## Selection Guidelines

- Prefer the framework already used by the project's dependencies or peer projects.
- For Node.js projects using Vite, ESBuild, or SWC, favor Vitest over Jest for native ESM and faster execution.
- For projects with existing Jest configuration, keep Jest unless migration is explicitly requested.
- For Go and Rust, use the built-in test tooling — third-party frameworks are rarely needed.
- When multiple frameworks are viable, prefer the one with the largest community and best IDE integration for the stack.
