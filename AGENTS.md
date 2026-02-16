# Repository Guidelines

## Project Structure & Module Organization
- Source code lives in `src/pymacs/`.
- `src/pymacs/state.py` defines `EditorState`, the mutable runtime model (buffers, current buffer, variables).
- `src/pymacs/core.py` defines `Editor`, including command registration/execution, hooks, and plugin loading.
- `src/pymacs/cli.py` provides the interactive shell and built-in command wiring.
- Top-level docs: `README.md` (usage) and `IMPLEMENTATION.md` (architecture and milestones).
- Runtime user config is expected at `~/.pymacs/init.py`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create and activate a local environment.
- `pip install -e .`: install PyMACS in editable mode with the `pymacs` console script.
- `python -m pymacs.cli`: run the interactive shell directly from source.
- `pymacs`: run via installed entry point (after `pip install -e .`).
- `python -m build`: create wheel/sdist packages (install `build` first if missing).

## Coding Style & Naming Conventions
- Target Python `>=3.11`; keep code type-annotated.
- Use PEP 8 defaults: 4-space indentation, `snake_case` for functions/variables, `PascalCase` for classes.
- Keep module and function docstrings concise and factual.
- Command names exposed to the shell should remain lowercase, kebab-case strings (for example, `new-buffer`, `show-buffer`).
- Prefer small, focused modules and standard-library-first dependencies.

## Testing Guidelines
- A test suite is not committed yet; add tests under `tests/` mirroring `src/pymacs/` (for example, `tests/test_core.py`).
- Use `pytest` conventions (`test_*.py`, `test_*` functions).
- Run tests with `pytest -q`.
- For behavior changes, include regression coverage for command dispatch, hook emission, plugin loading, and state mutation paths.

## Commit & Pull Request Guidelines
- This workspace snapshot does not include `.git` history; use clear, imperative commit messages with optional scope (for example, `core: validate plugin activate signature`).
- Keep subject lines short (about 72 chars); explain why in the body when non-trivial.
- PRs should include:
  - what changed and why,
  - how it was validated (commands/tests run),
  - linked issue/task if applicable,
  - terminal output snippets when CLI behavior changes.

## Security & Configuration Notes
- `Editor.load_plugin()` executes Python from a file path; only load trusted plugins.
- Avoid committing machine-local paths or secrets from `~/.pymacs/`.
