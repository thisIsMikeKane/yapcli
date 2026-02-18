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

[ ] TODO explain how to install pipx

## Quick start

```bash
pipx install git+https://github.com/thisismikekane/plaid-cli-python.git
plaid-cli --help
```

## Development environment

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.

## Project scripts

The CLI entry point is defined in `pyproject.toml` under `[project.scripts]` as `plaid-cli = plaid_cli.cli:app`. Implement your Typer application in `src/plaid_cli/cli.py`.

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
