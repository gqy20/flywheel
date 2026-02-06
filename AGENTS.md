# Repository Guidelines

## Project Structure & Module Organization

- `src/flywheel/`: core Todo CLI implementation (`cli.py`, `storage.py`, `formatter.py`, `todo.py`).
- `scripts/`: AI flywheel automation (`scan.py`, `evaluate.py`, `fix.py`).
- `tests/`: pytest test suite, mostly issue-focused regression tests.
- `.github/workflows/`: CI and automation workflows.
- `docs/`: design docs, workflow, PRD, and architecture notes.
- `.claude/skills/`: Claude Code skills for scan, evaluate, issue curation, candidate-fix, merge arbitration, CI failure autofix.

## Build, Test, and Development Commands

- `uv sync`: install dependencies from `pyproject.toml`.
- `uv pip install -e .`: optional editable install for local CLI usage.
- `uv run pytest --cov=src`: run tests with coverage.
- `uv run ruff check .`: lint the codebase.
- `uv run ruff format .`: apply formatting.
- `gh workflow run flywheel-orchestrator.yml`: manual unified flywheel pipeline run (scan/evaluate/fix/merge/curation).
- `gh workflow run ci-failure-auto-fix.yml`: manual CI failure autofix run.
- `gh workflow run docs-ci.yml`: manual docs gate run.
- `gh workflow run docs-auto-maintenance.yml`: manual docs autofix run.
- `gh workflow run automation-metrics.yml`: manual automation metrics snapshot run.

## Coding Style & Naming Conventions

- Python 3.13+, 4-space indentation, line length 100.
- Ruff is the source of truth for linting and formatting; formatter uses double quotes.
- Favor explicit, readable naming. Tests follow `test_<feature>_<condition>_<expected>` where practical.

## Testing Guidelines

- Framework: `pytest` with `pytest-cov` (coverage reported via `--cov=src`).
- Tests live under `tests/` and are auto-discovered via `pyproject.toml`.
- Use regression-style tests when fixing issues (many tests are named after issue IDs).

## Commit & Pull Request Guidelines

- Commit format follows Conventional Commits: `<type>: <short description> (#<issue>)`.
- Common types: `test`, `feat`, `fix`, `docs`, `refactor`, `perf`, default `chore`.
- TDD flow is expected for issue work:
  - RED: add failing test (`test:`)
  - GREEN: implement fix (`feat:`/`fix:`)
  - REFACTOR: optional cleanup (`refactor:`)
- PRs should link the issue number, describe tests run, and include coverage notes if relevant.

## Security & Configuration Tips

- `FLYWHEEL_STRICT_MODE=1` is recommended in production to prevent degraded locking modes.
- StatsD telemetry is optional via `FW_STATSD_HOST` and `FW_STATSD_PORT`.
