# Contributing

Thanks for helping improve Plaid CLI! This project uses UV for dependency management. Follow the workflow below to mirror the maintainers' setup.

## Helpful references

- [Plaid docs](https://plaid.com/docs/)
  - [Institution coverage](https://plaid.com/docs/institutions/)
  - [Plaid API docs](https://plaid.com/docs/api/)
- [Plaid dashboard](https://dashboard.plaid.com) (requires developer login)
  - [Instition status](https://dashboard.plaid.com/activity/status)
  - [Logs](https://dashboard.plaid.com/developers/logs)
  - [Item debugger](https://dashboard.plaid.com/activity/debugger)
  - [OAuth production status](https://dashboard.plaid.com/activity/status/oauth-institutions)
- **[Plaid quickstart](https://github.com/plaid/quickstart)** was copied as the foundation for `yapcli/server.py` and `frontend/`.

## Development environment (VS Code + uv)

### Prerequisites

1. **Install [uv](https://docs.astral.sh/uv/)**

   ```bash
   pipx install uv
   ```

   Reload your shell and verify `uv --version`.

2. **Install [tox](https://tox.wiki)** (optional)

   ```bash
   pipx install tox
   ```

### Create uv environments and set as default for VS Code project

1. **Create the base package environment** (runtime only):

   ```bash
   uv venv .venv --python 3.12
   source .venv/bin/activate
   uv pip install -e .
   ```

2. **Create the development environment** (runtime + lint/typecheck/test tooling):

   ```bash
   uv venv .venv-dev --python 3.12
   source .venv-dev/bin/activate
   uv pip install -e . --group dev
   ```

3. **Configure VS Code to use the uv environments**

   1. Install/enable the official *Python* extension from Microsoft (recommended in [\.vscode/extensions.json](.vscode/extensions.json). In VS Code, open the Extensions view and look for the **Recommended** section (or search `@recommended`) and install it from there.

   2. Open the **Python Environments** panel (status bar interpreter picker ➜ *Python Environments*, or run `Python: Focus Python Environments` from the Command Palette).

   3. Under **Workspace**, select `.venv-dev` and click **Set as default for new terminals**.

   4. Create a fresh terminal with `Terminal: Create New Terminal` (or the `+` button). VS Code launches it with the selected environment activated.

## Building and publishing

This project uses standard Python build tooling (PEP 517/518) with git-derived versions.

1. **Build the package**

   ```bash
   uv tool install build
   python -m build
   ```

2. **Publish to PyPI**

   ```bash
   uv tool install twine
   twine upload dist/*
   ```

Version numbers are derived from Git tags via `setuptools-scm`. Create a tag like `v0.1.0` and the build will use it automatically.
