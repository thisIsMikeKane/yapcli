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

## Default path behavior

`yapcli` centralizes path resolution in `yapcli/utils.py`.

- **In a development checkout** (repository with `pyproject.toml`):
  - Config root is the repository root
  - Default logs are written to `<repo-root>/logs`
  - Default secrets are read/written under `<repo-root>/secrets` (or `<repo-root>/sandbox/secrets` when `PLAID_ENV=sandbox`)
- **As an installed package** (pip/pipx):
  - Config and log directories are chosen via `platformdirs` for app name `yapcli`
  - Default secrets are under the resolved config dir (`secrets` or `sandbox/secrets`)
- **Data exports** default to `./data` relative to the current terminal working directory.

Overrides take precedence:

- CLI option `--secrets-dir`
- CLI option `--out-dir`
- Environment variable `PLAID_SECRETS_DIR`
- Environment variable `YAPCLI_LOG_DIR`

## Development environment (VS Code + uv)

### Prerequisites

1. **Install [pipx](https://pipx.pypa.io/stable/installation/)**

2. **Install [uv](https://docs.astral.sh/uv/)**

   ```bash
   pipx install uv
   ```

   Reload your shell and verify `uv --version`.

3. **Install [tox](https://tox.wiki)** (optional)

   ```bash
   pipx install tox
   ```

4. **Install [node.js](https://nodejs.org/en/download)**  and npm for building the frontend

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

### Build Process

1. **Build the React frontend**

   The frontend must be built before packaging:

   ```bash
   python scripts/build_frontend.py
   ```

   This will:
   - Install npm dependencies in the `frontend/` directory
   - Build the React app with `npm run build`
   - Copy the build output to `yapcli/frontend/build/`

   Alternatively, use the automated preparation script:

   ```bash
   python scripts/prepare_package.py
   ```

2. **Build the Python package**

   ```bash
   uv tool install build
   python -m build
   ```

   This creates both source distribution (`.tar.gz`) and wheel (`.whl`) in the `dist/` directory.

3. **Validate the package**

   ```bash
   uv tool install twine
   python -m twine check dist/*
   ```

   Verify the frontend is included:

   ```bash
   tar -tzf dist/*.tar.gz | grep frontend
   ```

4. **Publish to PyPI**

   ```bash
   twine upload dist/*
   ```

   Or use the preparation script with upload:

   ```bash
   python scripts/prepare_package.py --upload
   ```

### Automated Build Script

The `scripts/prepare_package.py` script automates the entire process:

```bash
# Clean, build, and validate
python scripts/prepare_package.py

# Build and upload to Test PyPI
python scripts/prepare_package.py --test-pypi

# Build and upload to PyPI
python scripts/prepare_package.py --upload
```

### Package Contents

The built package includes:

- Python CLI application
- Bundled React frontend (Plaid Link UI) at `yapcli/frontend/build/`
- All Python dependencies

Version numbers are derived from Git tags via `setuptools-scm`. Create a tag like `v0.1.0` and the build will use it automatically.
