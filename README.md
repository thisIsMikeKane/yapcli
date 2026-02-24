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
# Show loaded .env paths and default directories
yapcli config paths

# Interactive setup (prompts for core values)
yapcli config init

# Set/update a single key
yapcli config set PLAID_CLIENT_ID your_client_id
yapcli config set PLAID_ENV sandbox
```

`yapcli` loads this default `.env` file on package import.

### Configuration precedence (highest to lowest)

1. Command-line arguments/options
2. Environment variables already set in your shell/session
3. Values defined in the `.env` file in your CWD
4. Values defined in the `.env` file in your [config directory](https://platformdirs.readthedocs.io/en/latest/explanation.html#config-directories)

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
2. Serve the bundled [Plaid Link frontend](yapcli/frontend/build/index.html)
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

`yapcli` resolves default directories using [platform directories](https://platformdirs.readthedocs.io/en/latest/explanation.html#config-directories) (unless you override them with command options or environment variables):

- `YAPCLI_DEFAULT_DIRS` controls the default location for **config**, **secrets**, and **logs**:
  - `CWD`: use the current working directory (e.g. `./secrets`, `./logs`, `./.env`)
  - `PLATFORMDIRS`: use platform-native locations via `platformdirs` (e.g. `~/.config/yapcli` on Linux)
- `PLAID_ENV=sandbox` adds a `sandbox/` subdirectory for secrets/logs/exports.
- Export **output** defaults to the current working directory:
  - `./output` (production)
  - `./sandbox/output` (sandbox)

### Overrides

- Pass `--out-dir` on export commands to explicitly choose output location
- Set `PLAID_SECRETS_DIR` to override secrets location globally
- Set `YAPCLI_LOG_DIR` to override log directory globally
- Set `YAPCLI_OUTPUT_DIR` to override the default output directory globally

## Development environment

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.

## Project scripts

The CLI entry point is defined in `pyproject.toml` under `[project.scripts]` as `yapcli = "yapcli.cli.main:main"`. When installed via pipx or pip, the `yapcli` command becomes available in your PATH.

## Related works

- **[`ebridges/plaid2qif`](https://github.com/ebridges/plaid2qif)** No longer supported as of Feb. 2023. [`bhipple`](https://github.com/bhipple/plaid2qif/tree/master) fork also seems to have ceased development.
- **[dthigpen/plaid-cli-python](https://github.com/dthigpen/plaid-cli-python)** Last updated Feb. 2024. No community development engagement. Uses `plaid-python` v17.0.0 (currently at 38.1.0)
- **[madhat2r/plaid2text](https://github.com/madhat2r/plaid2text)**
- **[build-your-own-mint](https://github.com/yyx990803/build-your-own-mint)**
- **[plaid-sync](https://github.com/mbafford/plaid-sync)** Has an html page to launch the link, but likely outdated.
- **[plaid-cli](https://github.com/landakram/plaid-cli)** Writen in GO. Last updated 5 years ago

### Differences

- Last updated / activitely updated / archived or depreciated
- Works with institutions that require OAuth authentication
- Works with institutions that require MFA authmentication
- Installs in single command (doesn't require repo download or environment management)
