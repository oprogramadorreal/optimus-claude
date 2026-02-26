# bootstrap:commit-message

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that analyzes your local git changes and suggests [conventional commit](https://www.conventionalcommits.org/) messages — without committing anything.

## Features

- Analyzes staged, unstaged, and untracked changes
- Generates messages following the Conventional Commits spec
- Suggests splitting into multiple commits when changes span different concerns
- Read-only — never stages, commits, or modifies files

## Quick Start

This skill is part of the [bootstrap](https://github.com/oprogramadorreal/claude-code-bootstrap) plugin. See the [main README](../../README.md) for installation instructions.

## Usage

In Claude Code, use any of these:

- `/bootstrap:commit-message`
- "suggest a commit message"
- "generate commit message"
- "summarize my changes"

The skill will analyze your local changes and output a suggested commit message in a copyable code block.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Git

## License

[MIT](../../LICENSE)
