# Package Distribution Setup for yapcli

This document summarizes the changes made to enable PyPI distribution and pipx installation.

## Changes Made

### 1. Entry Point Configuration ([pyproject.toml](pyproject.toml))

- **Changed**: Entry point from `py-plaid` to `yapcli`
- **Updated**: Entry point target to `yapcli.cli.main:main`
- **Result**: Users can run `yapcli` command after installation

### 2. Package Data Configuration ([pyproject.toml](pyproject.toml))

- **Added**: `[tool.setuptools.package-data]` section
- **Includes**: `yapcli = ["frontend/build/**/*"]`
- **Added**: `exclude = ["tests*"]` in `[tool.setuptools.packages.find]`
- **Result**: Frontend build files are included, tests are excluded (no MANIFEST.in needed)

### 3. Frontend Build Script ([scripts/build_frontend.py](scripts/build_frontend.py))

- **Created**: Python script to build React frontend
- **Actions**:
  - Installs npm dependencies
  - Builds React app with `npm run build`
  - Copies build output to `yapcli/frontend/build/`
- **Result**: Automated frontend packaging preparation

### 4. Path Resolution Updates ([yapcli/cli/link.py](yapcli/cli/link.py))

- **Updated**: Frontend directory discovery
  - First checks for packaged frontend (installed scenario)
  - Falls back to project root (development scenario)
- **Updated**: Secrets directory location
  - Uses `~/.yapcli/secrets/` for installed packages
  - Uses project root for development
- **Updated**: Log directory location
  - Uses `~/.yapcli/logs/` for installed packages
  - Uses project root for development
- **Removed**: Hard-coded `PROJECT_ROOT` references from subprocess calls
- **Result**: Works correctly in both development and installed environments

### 5. Log Directory Updates ([yapcli/cli/main.py](yapcli/cli/main.py))

- **Updated**: Default log directory logic
  - Detects development vs installed environment
  - Uses appropriate paths for each scenario
- **Result**: Consistent logging behavior

### 6. Test Suite ([tests/scripts/test_packaging.py](tests/scripts/test_packaging.py))

- **Created**: Comprehensive packaging tests
- **Test Classes**:
  - `TestPackageStructure`: Verifies package configuration
  - `TestPackageBuild`: Tests sdist and wheel building
  - `TestInstalledPackage`: Tests installed package behavior
- **Validates**:
  - Entry point configuration
  - Frontend build inclusion
  - Package data configuration in pyproject.toml
  - Package building (sdist and wheel)
  - Installation in virtual environments
  - Command availability (`yapcli` command)
  - Frontend files in installed package

### 7. Configuration Tests ([tests/scripts/test_package_config.py](tests/scripts/test_package_config.py))

- **Created**: Quick configuration validation tests
- **Tests**:
  - Entry point configuration
  - Package data configuration in pyproject.toml
  - Build script existence
  - Module import syntax

### 8. Documentation Updates ([README.md](README.md))

- **Added**: Installation instructions for PyPI and from source
- **Added**: Usage examples
- **Added**: Build instructions for distribution
- **Updated**: Prerequisites section
- **Updated**: Project scripts section

## Building and Installing

### For Development

```bash
# Install dependencies
pip install -e .[dev]

# Build frontend (if needed)
python scripts/build_frontend.py

# Run from source
python -m yapcli link
```

### For Distribution
```bash
# 1. Build the frontend
python scripts/build_frontend.py

# 2. Build the package
python -m build

# 3. Upload to PyPI
python -m twine upload dist/*
```

### For End Users
```bash
# Install from PyPI
pipx install yapcli

# Run the command
yapcli link
```

## Testing

Run the packaging tests:
```bash
# Configuration tests (fast)
pytest tests/scripts/test_package_config.py -v

# Full packaging tests (requires npm, longer runtime)
pytest tests/scripts/test_packaging.py -v
```

## Key Implementation Details

### Frontend Location Strategy
The package uses a tiered approach to find the frontend:
1. **Packaged frontend**: `yapcli/frontend/build/` (inside package)
2. **Development frontend**: `PROJECT_ROOT/frontend/` (project source)

### Directory Strategy
For secrets and logs:
1. **Environment variables**: `YAPCLI_SECRETS_DIR`, `YAPCLI_LOG_DIR`
2. **Development**: `PROJECT_ROOT/secrets/`, `PROJECT_ROOT/logs/`
3. **Installed**: `~/.yapcli/secrets/`, `~/.yapcli/logs/`

### Benefits
- Works seamlessly in development and production
- No hard-coded paths that break when installed
- User data stored in standard home directory location
- Frontend bundled with Python package

## Verification

To verify the package is correctly configured:

1. **Build the frontend**:
   ```bash
   python scripts/build_frontend.py
   ```

2. **Check the build output**:
   ```bash
   ls -la yapcli/frontend/build/
   ```

3. **Build the package**:
   ```bash
   python -m build
   ```

4. **Verify package contents**:
   ```bash
   tar -tzf dist/yapcli-*.tar.gz | grep frontend
   ```

5. **Install in test environment**:
   ```bash
   python -m venv test_venv
   source test_venv/bin/activate
   pip install dist/yapcli-*.whl
   yapcli --help
   yapcli link --help
   ```

## Future Improvements

- Add CI/CD workflow to automate frontend build and package testing
- Add pre-commit hook to ensure frontend is built before commits
- Consider using `setuptools` build hooks for automatic frontend building
- Add integration tests that actually run the link command (with mocked Plaid API)
