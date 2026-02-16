# Yet Another Plaid CLI

A CLI for exporting Plaid API requests to plain text for importing into accounting/budgeting software (e.g, GnuCash)

## Features

- Exports the following Plaid API requests to plain text
  - [`transactions`](https://plaid.com/docs/api/products/transactions/)
  - [`investments`](https://plaid.com/docs/api/products/investments/)
  - [`liabilities`](https://plaid.com/docs/api/products/liabilities/)
- Supports financial institutions that require OAuth authentication with Plaid

## Prerequisites

- Python 3.12+
- [pipx](https://pipx.pypa.io/) for installation

[ ] TODO explain how to get Plaid developer credentials

## Quick start

### Install from PyPI

```bash
pipx install yapcli
yapcli --help
```

## Usage

### Link a Plaid account

To link your financial institution and obtain credentials:

```bash
yapcli link
```

This will:
1. Start a local Flask backend server
2. Serve the React frontend (Plaid Link UI)
3. Open your browser to complete the Plaid Link flow
4. Save the credentials to `~/.yapcli/secrets/`

### Export transactions

```bash
yapcli transactions --help
```

### Check balances

```bash
yapcli balances --help
```

## Development environment

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.

## Project scripts

The CLI entry point is defined in `pyproject.toml` under `[project.scripts]` as `yapcli = "yapcli.cli.main:main"`. When installed via pipx or pip, the `yapcli` command becomes available in your PATH.

## Related works

- **[`ebridges/plaid2qif`](https://github.com/ebridges/plaid2qif)** No longer supported as of Feb. 2023. [`bhipple`](https://github.com/bhipple/plaid2qif/tree/master) fork also seems to have ceased development.
- **[dthigpen/plaid-cli-python](https://github.com/dthigpen/plaid-cli-python)** Last updated Feb. 2024. No community development engagement. Uses `plaid-python` v17.0.0 (currently at 38.1.0)
- [madhat2r/plaid2text](https://github.com/madhat2r/plaid2text)