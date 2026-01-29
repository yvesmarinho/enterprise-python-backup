# CLI Import Error Troubleshooting

## Error Description

**Error Message:**
```
ImportError: cannot import name 'main' from 'python_backup.__main__'
```

**Occurrence:**
When attempting to run the `vya-backupdb` command after code changes or initial installation.

**Example Command:**
```bash
vya-backupdb vault-get --id mysql-prod
```

## Root Cause

This error occurs when:

1. **Package Not Installed**: The `vya-backupdb` package is not installed in the current Python environment
2. **Outdated Installation**: Code changes were made but the package was not reinstalled
3. **Entry Point Mismatch**: The console script entry point cannot find the `main` function in `__main__.py`

## Solution

### Using UV (Recommended)

If you're using **uv** for package management:

```bash
# Navigate to project root
cd /path/to/enterprise-python-backup

# Install/reinstall package in editable mode
uv pip install -e .
```

**Output:**
```
Resolved 25 packages in 220ms
Built vya-backupdb @ file:///path/to/enterprise-python-backup
Prepared 1 package in 602ms
Uninstalled 1 package in 0.46ms
Installed 1 package in 0.83ms
 ~ vya-backupdb==2.0.0
```

### Using Standard Pip

If you're using standard pip:

```bash
# Navigate to project root
cd /path/to/enterprise-python-backup

# Install/reinstall package in editable mode
pip install -e .
```

### Verify Installation

Test that the CLI works:

```bash
vya-backupdb --help
```

**Expected Output:**
```
Usage: vya-backupdb [OPTIONS] COMMAND [ARGS]...

VYA BackupDB - Enterprise Database Backup & Restore System

╭─ Options ───────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                     │
╰─────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────╮
│ version           Show version information.                     │
│ backup            Execute database backup.                      │
│ restore-list      List available backup files.                 │
│ restore           Restore database from backup file.            │
│ ...                                                             │
╰─────────────────────────────────────────────────────────────────╯
```

## Prevention

### 1. Always Reinstall After Code Changes

When making changes to the source code, always reinstall:

```bash
uv pip install -e .  # or pip install -e .
```

### 2. Check Entry Point Configuration

Verify [pyproject.toml](../../pyproject.toml) has the correct entry point:

```toml
[project.scripts]
vya-backupdb = "python_backup.__main__:main"
```

### 3. Verify __main__.py Structure

Check [src/python_backup/__main__.py](../../src/python_backup/__main__.py):

```python
from python_backup.cli import app

def main():
    """Main entry point for console script."""
    app()

if __name__ == "__main__":
    main()
```

## Related Errors

### Error: "command not found: vya-backupdb"

**Cause**: Package not installed or not in PATH

**Solution**:
```bash
# Check if installed
uv pip list | grep vya-backupdb

# If not installed
uv pip install -e .
```

### Error: "ModuleNotFoundError: No module named 'python_backup'"

**Cause**: Wrong directory or environment

**Solution**:
```bash
# Verify you're in project root
pwd  # Should end with enterprise-python-backup

# Verify Python environment
which python

# Reinstall
uv pip install -e .
```

## Technical Details

### Entry Point Mechanism

The `vya-backupdb` console script is created by setuptools based on `pyproject.toml`:

```toml
[project.scripts]
vya-backupdb = "python_backup.__main__:main"
```

This creates a shell script in your virtual environment's `bin/` directory:

```bash
~/.venv/bin/vya-backupdb
```

The script imports and calls `main()` from `python_backup.__main__`.

### Why Editable Install (-e)?

**Editable mode** allows you to:
- Modify source code without reinstalling
- See changes immediately (for most changes)
- Keep development workflow smooth

**When to Reinstall:**
- Entry point changes (`pyproject.toml`)
- New dependencies added
- Package metadata changes
- After git pull with structural changes

## Diagnostic Commands

### Check Installation
```bash
# List installed packages
uv pip list | grep vya-backupdb

# Show package details
uv pip show vya-backupdb

# Find entry point script location
which vya-backupdb
```

### Check Python Environment
```bash
# Current Python
which python

# Python version
python --version

# Check if in virtual environment
echo $VIRTUAL_ENV
```

### Verify Package Structure
```bash
# Check __main__.py exists
ls -lh src/python_backup/__main__.py

# Verify it's a Python package
ls -lh src/python_backup/__init__.py

# Check entry point configuration
grep -A2 "\[project.scripts\]" pyproject.toml
```

## Environment-Specific Notes

### Using UV
- **Faster** than pip (written in Rust)
- Drop-in replacement for pip
- Command: `uv pip install -e .`

### Using Poetry
```bash
poetry install
```

### Using Pipenv
```bash
pipenv install -e .
```

### Using Conda
```bash
conda activate your-env
pip install -e .
```

## Timestamp

- **Error First Encountered**: 2026-01-26 15:12:29
- **Resolution**: 2026-01-26 15:17:19
- **Resolution Time**: ~5 minutes
- **Method**: `uv pip install -e .`

## Related Documentation

- [SECRETS_DIRECTORY_GUIDE.md](../guides/SECRETS_DIRECTORY_GUIDE.md) - Where the error was discovered
- [pyproject.toml](../../pyproject.toml) - Entry point configuration
- [src/python_backup/__main__.py](../../src/python_backup/__main__.py) - Main entry point

---

**Created**: 2026-01-26  
**Last Updated**: 2026-01-26  
**Severity**: 🟡 MEDIUM  
**Resolution**: ✅ SOLVED
