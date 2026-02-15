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
   poetry install --with dev
   ```

4. **Configure VS Code to use Poetry's virtual environment**

   1. Install/enable the official *Python* extension from Microsoft (recommended in [\.vscode/extensions.json](.vscode/extensions.json). In VS Code, open the Extensions view and look for the **Recommended** section (or search `@recommended`) and install it from there.

   2. Open the **Python Environments** panel (status bar interpreter picker ➜ *Python Environments*, or run `Python: Focus Python Environments` from the Command Palette).

   3. Under **Workspace**, you should see the Poetry env created in steps 2–3 (e.g., `.cache/pypoetry/virtualenvs/plaid-cli-python-...`). Select it and click **Set as default for new terminals**.

   4. Create a fresh terminal with `Terminal: Create New Terminal` (or the `+` button). VS Code launches it with the Poetry environment already activated, so `python`/`poetry run` all map to the same interpreter.
