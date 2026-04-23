# Repository Guidelines

## Project Structure & Module Organization
Core package code lives in `src/skill_mgr/`. Keep CLI entrypoints in `src/skill_mgr/cli.py` and `src/skill_mgr/main.py`, domain models in `src/skill_mgr/models.py`, service orchestration in `src/skill_mgr/services/`, source resolution in `src/skill_mgr/sources/`, adapter logic in `src/skill_mgr/adapters/`, and `SKILL.md` validation in `src/skill_mgr/validation/`. Tests live in `tests/` and generally mirror the package surface, for example `tests/test_cli.py` for `src/skill_mgr/cli.py`. Planning notes are in `project/`; user docs are in `README.md` and `docs/`.

## Build, Test, and Development Commands
Use Python 3.12 and install dev tooling with `uv sync --all-groups`. Key commands:

- `make format`: run Ruff formatting and fix import/unused-import issues.
- `make lint`: run `ruff check .`, `mypy src/`, and `ruff format . --check`.
- `make test`: run `pytest --cov --cov-report term-missing tests/`.
- `make doc`: serve MkDocs locally on `0.0.0.0:8080`.
- `uv run skill-mgr -h`: exercise the CLI from source without installing.

## Coding Style & Naming Conventions
Follow 4-space indentation, 88-character lines, and Ruff-managed import ordering. Use absolute imports only; relative imports are disallowed. New production code should be fully typed because `mypy` runs with `disallow_untyped_defs = true`. Prefer `snake_case` for functions/modules, `PascalCase` for classes, and short imperative docstrings with Google-style conventions where needed.

## Testing Guidelines
Write `pytest` tests in files named `tests/test_<area>.py` and keep coverage focused on user-visible behavior and error cases. Reuse helpers from `tests/helpers.py` for CLI and fixture setup when possible. Run `make test` before opening a PR; run `make lint` for changes that touch typing, formatting, or imports.

## Commit & Pull Request Guidelines
Recent history favors short, imperative commit subjects such as `Add badges` or `Enable coverage badge reporting and refresh README install docs`. Keep commits scoped; use the existing `Bump version: X → Y` pattern only for version updates. PRs should explain the behavioral change, list validation performed (`make lint`, `make test`), link any issue, and include sample CLI output when command UX or rendered tables change.

## Configuration & Packaging Notes
Project metadata and tool configuration live in `pyproject.toml`; keep packaging exclusions and script entrypoints aligned with code moves. Pre-commit hooks cover YAML/JSON hygiene, Ruff, and TOML formatting, so run `pre-commit run --all-files` when touching repo-wide config.
