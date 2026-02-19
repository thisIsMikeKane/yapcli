# Yet Another Plaid CLI

A CLI for exporting Plaid API requests to plain text for importing into accounting/budgeting software (e.g, GnuCash)

## Features

- Exports the following Plaid API requests to plain text
  - [Plaid `transactions`](https://plaid.com/docs/api/products/transactions/)
    - `yapcli balances`
    - `yapcli transactions`
  - [Plaid `investments`](https://plaid.com/docs/api/products/investments/)
    - `yapcli holdings`
    - `yapcli investment_transactions`
- Supports financial institutions that require OAuth authentication with Plaid

## Prerequisites

### Plaid developer credentials

[ ] TODO explain how to get Plaid developer credentials

### Dependencies

- **Python 3.12**: Minimum necessary version of Python to run `yapcli`
- **[pipx](https://pipx.pypa.io/stable/#install-pipx)**: Streamlines installation and commandline use

## Quick start

### Install from PyPI

```bash
pipx install yapcli
yapcli --help
```

## Usage

### Configure Plaid credentials

Use the `config` commands to create and manage your `yapcli` `.env` file:

```bash
# Show the default .env path
yapcli config path

# Interactive setup (prompts for core values)
yapcli config init

# Set/update a single key
yapcli config set PLAID_CLIENT_ID your_client_id
yapcli config set PLAID_ENV sandbox
```

`yapcli` loads this default `.env` file on package import.

Configuration precedence (highest to lowest):

1. Command-line arguments/options
2. Environment variables already set in your shell/session
3. Values defined in the default `.env` file

Examples:

- `yapcli --production ...` overrides `PLAID_ENV` from both shell env and `.env`
- Exporting `PLAID_ENV=sandbox` in your shell overrides `PLAID_ENV` in `.env`
- `.env` values are used as defaults when neither CLI options nor shell env provide a value

### Link a Plaid account

To link your financial institution and obtain credentials:

```bash
yapcli link
```

This will:

1. Start a local Flask backend server
2. Serve the React frontend (Plaid Link UI)
3. Open your browser to complete the Plaid Link flow
4. Save credentials to the default secrets directory (see Default paths below)

### Export transactions

```bash
yapcli transactions --help
```

### Check balances

```bash
yapcli balances --help
```

## Default paths

`yapcli` resolves default directories as follows (unless you override them):

- **Development checkout** (repo contains `pyproject.toml`):
  - Config root: `<repo-root>/`
  - Secrets: `<repo-root>/secrets` (or `<repo-root>/sandbox/secrets` when `PLAID_ENV=sandbox`)
  - Logs: `<repo-root>/logs`
- **Installed package** (pip/pipx):
  - Config/log dirs use platform-native locations via `platformdirs` (for app `yapcli`)
  - Secrets: `<platform-config-dir>/secrets` (or `<platform-config-dir>/sandbox/secrets` when `PLAID_ENV=sandbox`)
- **Data output**:
  - Defaults to `./data` under your current terminal working directory
  - Command-specific subdirectories are created under `./data` (for example `transactions`, `balances`, etc.)

### Overrides

- Pass `--secrets-dir` on commands that support it to explicitly choose secrets location
- Pass `--out-dir` on export commands to explicitly choose output location
- Set `PLAID_SECRETS_DIR` to override secrets location globally
- Set `YAPCLI_LOG_DIR` to override log directory globally

## Development environment

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.

## Project scripts

The CLI entry point is defined in `pyproject.toml` under `[project.scripts]` as `yapcli = "yapcli.cli.main:main"`. When installed via pipx or pip, the `yapcli` command becomes available in your PATH.

## Related works

- **[`ebridges/plaid2qif`](https://github.com/ebridges/plaid2qif)** No longer supported as of Feb. 2023. [`bhipple`](https://github.com/bhipple/plaid2qif/tree/master) fork also seems to have ceased development.
- **[dthigpen/plaid-cli-python](https://github.com/dthigpen/plaid-cli-python)** Last updated Feb. 2024. No community development engagement. Uses `plaid-python` v17.0.0 (currently at 38.1.0)
- [madhat2r/plaid2text](https://github.com/madhat2r/plaid2text)
