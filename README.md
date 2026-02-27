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

- [ ] TODO explain how to get Plaid developer credentials

### Dependencies

- **Python 3.12**: Minimum necessary version of Python to run `yapcli`
- **[pipx](https://pipx.pypa.io/stable/#install-pipx)**: Streamlines installation and commandline use

## Quick start

### Install from PyPI

```bash
pipx install yapcli
yapcli --help
```

### Configure Plaid credentials

Use the `config` commands to create and manage your `yapcli` `.env` file:

```bash
# Show loaded .env paths and default directories
yapcli config paths

# Interactive setup (prompts for required values)
yapcli config init
```

#### Default paths

`yapcli` resolves default directories using [platform directories](https://platformdirs.readthedocs.io/en/latest/explanation.html#config-directories) (unless you override them with command options or environment variables):

- `YAPCLI_DEFAULT_DIRS` controls the default location for **config**, **secrets**, and **logs**:
  - `CWD`: use the current working directory (e.g. `./secrets`, `./logs`, `./.env`)
  - `PLATFORMDIRS`: use platform-native locations via `platformdirs` (e.g. `~/.config/yapcli` on Linux)
- `PLAID_ENV=sandbox` adds a `sandbox/` subdirectory for secrets/logs/exports.
- Export **output** defaults to the current working directory:
  - `./output` (production)
  - `./sandbox/output` (sandbox)

#### Configuration precedence

`yapcli` loads this default `.env` file on package import. The following describes how different `.env` files, environment variables, and command options take precedence (highest to lowest).

1. Command-line arguments/options
2. Environment variables already set in your shell/session
3. Values defined in the `.env` file in your CWD
4. Values defined in the `.env` file in your [config directory](https://platformdirs.readthedocs.io/en/latest/explanation.html#config-directories)

Examples:

- `yapcli --production ...` overrides `PLAID_ENV` from both shell env and `.env`
- Exporting `PLAID_ENV=sandbox` in your shell overrides `PLAID_ENV` in `.env`
- `.env` values are used as defaults when neither CLI options nor shell env provide a value

#### Overrides

- Pass `--out-dir` on export commands to explicitly choose output location
- Set `PLAID_SECRETS_DIR` to override secrets location globally
- Set `YAPCLI_LOG_DIR` to override log directory globally
- Set `YAPCLI_OUTPUT_DIR` to override the default output directory globally

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

## Related works

The features and limitations of these related projects inspired yapcli. Information below as of 2/26/2026.

| Project                                                                                     | Lang          | Last commit | Stars | Forks | Open issues | Open PRs | Status                         | Plaid API version                       | Plaid client library                           | Supports Plaid Link                        | Link OAuth flows                                                 | Install (1-liner?)                    | Output format(s)                                        | Target software              | TX             | INV         |
| ------------------------------------------------------------------------------------------- | ------------- | ----------: | ----: | ----: | ----------: | -------: | ------------------------------ | --------------------------------------- | ---------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------- | ---------------------------- | -------------- | ----------- |
| [jverdi/plaid-cli](https://github.com/jverdi/plaid-cli)                                     | Go            |  2026-01-03 |     1 |     0 |           0 |        0 | Active (recent fork + release) | 2020-09-14 (SDK default)                | plaid-go/v41 v41.0.0                           | Yes                                        | No (no redirect_uri wiring found)                                | go install / releases                 | CSV, JSON                                               | Generic (manual import)      | Yes            | No          |
| [dvankley/firefly-plaid-connector-2](https://github.com/dvankley/firefly-plaid-connector-2) | Kotlin        |  2025-11-18 |   141 |    21 |           7 |        3 | Active                         | 2020-09-14 (explicit OpenAPI spec file) | Generated client from plaid-2020-09-14 OpenAPI | Partial (delegates linking to Quickstart)  | Partial (via Quickstart)                                         | Docker / JVM app                      | Firefly III transactions (writes via API)               | Firefly III                  | Yes            | No          |
| [mbafford/plaid-sync](https://github.com/mbafford/plaid-sync)                               | Python        |  2025-10-25 |    45 |     7 |           4 |        0 | Active                         | Not stated (SDK default)                | plaid-python >= 30.0.0                         | Yes                                        | No (OAuth marked wontfix; redirect_uri not used)                 | Clone + run (not packaged)            | SQLite DB                                               | Generic / downstream tooling | Yes            | No          |
| [allancalix/clerk](https://github.com/allancalix/clerk)                                     | Rust          |  2024-11-26 |     6 |     0 |           2 |        0 | Maintained (small)             | Not stated                              | rplaid (git) + local plaid-link crate          | Yes                                        | Unknown (not confirmed from primary sources)                     | cargo build / releases                | SQLite DB (+ JSON state)                                | Generic (beancount-oriented) | Yes            | No evidence |
| [dknelson9876/oregano](https://github.com/dknelson9876/oregano)                             | Go            |  2024-04-22 |     1 |     0 |           2 |        0 | Early-stage                    | Not stated                              | plaid-go v1.10.0                               | Yes                                        | No/Partial (borrowed from landakram; redirect_uri not evidenced) | go build (not clearly packaged)       | App-local store; CSV import supported                   | Oregano TUI budgeting app    | Yes            | Unknown     |
| [dthigpen/plaid-cli-python](https://github.com/dthigpen/plaid-cli-python)                   | Python        |  2024-02-03 |     5 |     0 |           0 |        0 | Unclear (single maintainer)    | 2020-09-14 (explicit default config)    | plaid-python == 17.0.0                         | Yes                                        | No (redirect_uri commented out)                                  | pip install (from git URL)            | table, CSV, JSON (stdout)                               | Generic                      | Yes            | No          |
| [ebridges/plaid2qif](https://github.com/ebridges/plaid2qif)                                 | Python        |  2024-01-11 |   118 |    12 |           3 |        2 | **EOL / abandoned**            | 2020-09-14 (explicit default env)       | plaid-python >= 8.0.0                          | Yes (separate account-linker)              | Partial (redirect env var supported)                             | pip install (PyPI)                    | QIF, CSV, JSON                                          | GnuCash / any QIF importer   | Yes            | No          |
| [bhipple/plaid2qif](https://github.com/bhipple/plaid2qif)                                   | Python        |  2024-01-11 |     1 |    12 |           0 |        0 | Fork; unclear independent dev  | Not stated                              | Same as upstream (fork)                        | Yes (same as upstream)                     | Partial (inherits upstream approach)                             | pip install (if published) / clone    | QIF, CSV, JSON                                          | GnuCash / any QIF importer   | Yes            | No          |
| [benkn/mercury](https://github.com/benkn/mercury)                                           | TypeScript    |  2024-01-08 |     2 |     0 |           0 |        0 | Personal tool / semi-stale     | Not stated                              | Node plaid ^17.0.0                             | Partial (uses Quickstart to obtain tokens) | Partial (via Quickstart)                                         | npm install (repo)                    | Google Sheets                                           | Spreadsheet workflow         | Yes            | No          |
| [madhat2r/plaid2text](https://github.com/madhat2r/plaid2text)                               | Python        |  2022-03-14 |    94 |    19 |          10 |        8 | Likely abandoned               | Not stated                              | plaid-python == 7.1.0                          | Yes                                        | No (no redirect_uri evidenced)                                   | clone + pip install (services needed) | Ledger / Beancount text (plus MongoDB/SQLite storage)   | Ledger / Beancount           | Yes            | No          |
| [infiniteluke/actualplaid](https://github.com/infiniteluke/actualplaid)                     | JavaScript    |  2020-11-23 |    42 |    22 |           3 |        0 | Likely abandoned               | Not stated                              | Node plaid ^6.0.0                              | Yes (setup links banks)                    | Unknown (not confirmed from primary sources)                     | npm -g / yarn global                  | Imports into Actual Budget via API                      | Actual Budget                | Yes            | No          |
| [landakram/plaid-cli](https://github.com/landakram/plaid-cli)                               | Go            |  2020-06-16 |    56 |    17 |           4 |        0 | Abandoned                      | Not stated                              | plaid-go (older)                               | Yes                                        | No (no redirect_uri wiring; OAuth issue exists)                  | go get / binaries                     | CSV, JSON                                               | Generic (manual import)      | Yes            | No          |
| [tobidae/bank-me](https://github.com/tobidae/bank-me)                                       | TypeScript/JS |  2019-07-03 |    10 |     3 |           0 |        0 | Abandoned                      | Not stated                              | Node plaid ^4.1.0                              | Yes (links accounts)                       | Unknown (not confirmed)                                          | clone + multi npm installs            | CSV, Google Sheets (Firebase optional)                  | Spreadsheet workflow         | Yes            | No          |
| [yyx990803/build-your-own-mint](https://github.com/yyx990803/build-your-own-mint)           | JavaScript    |  2019-01-23 |  2500 |   205 |           0 |        9 | Abandoned (tutorial)           | 2018-05-22 (explicit)                   | Node plaid ^2.10.0                             | Yes                                        | No (legacy; pre-OAuth-era wiring)                                | npm install (repo)                    | Google Sheets                                           | Spreadsheet workflow         | Yes            | No          |
| [cyrusstoller/plaid-cli](https://github.com/cyrusstoller/plaid-cli)                         | JavaScript    |  2018-10-18 |     2 |     0 |           0 |        0 | Abandoned                      | Not stated                              | Node plaid ^2.8.2                              | No (no Link flow described)                | No                                                               | npm -g                                | Interactive REPL / stdout (no export format documented) | Generic                      | Yes (API tool) | No evidence |

## Development environment

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.

## Caveats

This tool is meant to simplify the maintenance of a personal plaintext finance records, please consider where and how your data is stored (please don't run this on a public machine). Note that data and secrets are stored in as plain text and makes no effort to encrypt or otherwise obfuscate your data.
