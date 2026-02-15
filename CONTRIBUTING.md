# Contributing

Thanks for helping improve Plaid CLI! This project uses Poetry for dependency management. Follow the workflow below to mirror the maintainers' setup.

## Development environment (VS Code + Poetry)

1. **Install [Poetry](https://python-poetry.org/docs/#installation) (recommended via [pipx](https://pipx.pypa.io/stable/))**

   ```bash
   pipx install poetry
   ```

   If you don't already have `pipx`, install it with `python3 -m pip install --user pipx` (or follow your OS package instructions). Reload your shell or ensure `~/.local/bin` (or the path printed by the installer) is on `PATH`.

2. **Select the Python interpreter** (adjust the version if desired):

   ```bash
   poetry env use 3.12
   ```

   If `python3.12` is not available, point Poetry to the interpreter you prefer (e.g., `poetry env use $(which python3.12)`).

3. **Install all dependency groups** (runtime + lint/typecheck/test/dev tooling):

   ```bash
   poetry install --with lint,typecheck,test,dev
   ```

4. **Configure VS Code to use Poetry's virtual environment**

   - Discover the environment path: `poetry env info --path`
   - In VS Code run *Python: Select Interpreter* and pick the path returned above
   - Optionally set "python.defaultInterpreterPath" to that path inside `.vscode/settings.json`

5. **Run project commands through Poetry**

   ```bash
   poetry run pytest
   poetry run ruff check
   poetry run mypy
   ```

   Add additional helpers (formatters, hooks, etc.) with `poetry run ...` to keep the workflow consistent for all contributors.
