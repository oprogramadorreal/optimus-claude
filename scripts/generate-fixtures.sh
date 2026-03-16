#!/usr/bin/env bash
# Generates minimal project fixtures for testing optimus skills.
# No dependencies installed — just enough files for project detection to work.
# Run: bash scripts/generate-fixtures.sh [fixture-name...]
# Output: test/fixtures/<name>/ (gitignored)
#
# Examples:
#   bash scripts/generate-fixtures.sh              # generate all fixtures
#   bash scripts/generate-fixtures.sh node python   # generate specific fixtures

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURES_DIR="$PLUGIN_ROOT/test/fixtures"

# --- Fixture generators ---

generate_node_project() {
  local dir="$FIXTURES_DIR/node-project"
  rm -rf "$dir"
  mkdir -p "$dir"
  (
    cd "$dir"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false

    cat > package.json <<'EOF'
{
  "name": "hello-node",
  "version": "1.0.0",
  "description": "Minimal Node.js fixture for testing",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "echo \"no tests yet\" && exit 1"
  }
}
EOF

    cat > index.js <<'EOF'
function greet(name) {
  return `Hello, ${name}!`;
}

console.log(greet("World"));
module.exports = { greet };
EOF

    cat > .gitignore <<'EOF'
node_modules/
.claude/
EOF

    git add -A && git commit -q -m "initial: node project"
  )
  echo "  Created: node-project"
}

generate_python_project() {
  local dir="$FIXTURES_DIR/python-project"
  rm -rf "$dir"
  mkdir -p "$dir/src"
  (
    cd "$dir"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false

    cat > pyproject.toml <<'EOF'
[project]
name = "hello-python"
version = "1.0.0"
description = "Minimal Python fixture for testing"
requires-python = ">=3.9"

[project.scripts]
hello = "src.main:main"
EOF

    cat > src/__init__.py <<'EOF'
EOF

    cat > src/main.py <<'EOF'
def greet(name: str) -> str:
    return f"Hello, {name}!"


def main():
    print(greet("World"))


if __name__ == "__main__":
    main()
EOF

    cat > .gitignore <<'EOF'
__pycache__/
*.pyc
.venv/
.claude/
EOF

    git add -A && git commit -q -m "initial: python project"
  )
  echo "  Created: python-project"
}

generate_go_project() {
  local dir="$FIXTURES_DIR/go-project"
  rm -rf "$dir"
  mkdir -p "$dir"
  (
    cd "$dir"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false

    cat > go.mod <<'EOF'
module example.com/hello-go

go 1.21
EOF

    cat > main.go <<'EOF'
package main

import "fmt"

func greet(name string) string {
	return fmt.Sprintf("Hello, %s!", name)
}

func main() {
	fmt.Println(greet("World"))
}
EOF

    cat > .gitignore <<'EOF'
.claude/
EOF

    git add -A && git commit -q -m "initial: go project"
  )
  echo "  Created: go-project"
}

generate_rust_project() {
  local dir="$FIXTURES_DIR/rust-project"
  rm -rf "$dir"
  mkdir -p "$dir/src"
  (
    cd "$dir"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false

    cat > Cargo.toml <<'EOF'
[package]
name = "hello-rust"
version = "0.1.0"
edition = "2021"
EOF

    cat > src/main.rs <<'EOF'
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

fn main() {
    println!("{}", greet("World"));
}
EOF

    cat > .gitignore <<'EOF'
target/
.claude/
EOF

    git add -A && git commit -q -m "initial: rust project"
  )
  echo "  Created: rust-project"
}

generate_csharp_project() {
  local dir="$FIXTURES_DIR/csharp-project"
  rm -rf "$dir"
  mkdir -p "$dir"
  (
    cd "$dir"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false

    cat > HelloCsharp.csproj <<'EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
</Project>
EOF

    cat > Program.cs <<'EOF'
namespace HelloCsharp;

class Program
{
    static string Greet(string name) => $"Hello, {name}!";

    static void Main(string[] args)
    {
        Console.WriteLine(Greet("World"));
    }
}
EOF

    cat > .gitignore <<'EOF'
bin/
obj/
.claude/
EOF

    git add -A && git commit -q -m "initial: csharp project"
  )
  echo "  Created: csharp-project"
}

generate_monorepo_project() {
  local dir="$FIXTURES_DIR/monorepo-project"
  rm -rf "$dir"
  mkdir -p "$dir/packages/api/src" "$dir/packages/web/src"
  (
    cd "$dir"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false

    # Root package.json with workspaces
    cat > package.json <<'EOF'
{
  "name": "hello-monorepo",
  "private": true,
  "workspaces": ["packages/*"]
}
EOF

    # API package
    cat > packages/api/package.json <<'EOF'
{
  "name": "@hello/api",
  "version": "1.0.0",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "test": "echo \"no tests yet\" && exit 1"
  }
}
EOF

    cat > packages/api/src/index.js <<'EOF'
function handleRequest(req) {
  return { status: 200, body: "Hello from API" };
}

module.exports = { handleRequest };
EOF

    # Web package
    cat > packages/web/package.json <<'EOF'
{
  "name": "@hello/web",
  "version": "1.0.0",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "test": "echo \"no tests yet\" && exit 1"
  }
}
EOF

    cat > packages/web/src/index.js <<'EOF'
function render(page) {
  return `<html><body>${page}</body></html>`;
}

module.exports = { render };
EOF

    cat > .gitignore <<'EOF'
node_modules/
.claude/
EOF

    git add -A && git commit -q -m "initial: monorepo project"
  )
  echo "  Created: monorepo-project"
}

generate_empty_project() {
  local dir="$FIXTURES_DIR/empty-project"
  rm -rf "$dir"
  mkdir -p "$dir"
  (
    cd "$dir"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false
    git commit --allow-empty -q -m "initial: empty project"
  )
  echo "  Created: empty-project"
}

generate_multi_repo_workspace() {
  local dir="$FIXTURES_DIR/multi-repo-workspace"
  rm -rf "$dir"
  mkdir -p "$dir/backend" "$dir/frontend"

  # Backend repo
  (
    cd "$dir/backend"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false
    cat > package.json <<'EOF'
{
  "name": "backend",
  "version": "1.0.0",
  "scripts": { "start": "node index.js" }
}
EOF
    echo 'console.log("backend");' > index.js
    cat > .gitignore <<'EOF'
node_modules/
.claude/
EOF
    git add -A && git commit -q -m "initial: backend"
  )

  # Frontend repo
  (
    cd "$dir/frontend"
    git init -q .
    git config user.email "test@test.com"
    git config user.name "Test"
    git config core.autocrlf false
    cat > package.json <<'EOF'
{
  "name": "frontend",
  "version": "1.0.0",
  "scripts": { "start": "node index.js" }
}
EOF
    echo 'console.log("frontend");' > index.js
    cat > .gitignore <<'EOF'
node_modules/
.claude/
EOF
    git add -A && git commit -q -m "initial: frontend"
  )

  echo "  Created: multi-repo-workspace"
}

# --- Available fixtures ---
declare -A GENERATORS=(
  [node]=generate_node_project
  [python]=generate_python_project
  [go]=generate_go_project
  [rust]=generate_rust_project
  [csharp]=generate_csharp_project
  [monorepo]=generate_monorepo_project
  [empty]=generate_empty_project
  [multi-repo]=generate_multi_repo_workspace
)

# --- Main ---

echo "=== Generating test fixtures ==="

mkdir -p "$FIXTURES_DIR"

if [ $# -eq 0 ]; then
  # Generate all fixtures
  targets=(node python go rust csharp monorepo empty multi-repo)
else
  targets=("$@")
fi

for target in "${targets[@]}"; do
  if [ -n "${GENERATORS[$target]+x}" ]; then
    ${GENERATORS[$target]}
  else
    echo "  ERROR: Unknown fixture '$target'. Available: ${!GENERATORS[*]}"
    exit 1
  fi
done

echo
echo "=== Done. Fixtures in: test/fixtures/ ==="
echo "Run skills against them:"
echo "  cd test/fixtures/node-project && claude -p \"/optimus:init\""
