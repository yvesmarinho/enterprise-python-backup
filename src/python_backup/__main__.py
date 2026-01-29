"""
VYA BackupDB - Main entry point for CLI execution.

This module allows the package to be executed as:
    python -m python_backup
    vya-backupdb (console script)
"""

from python_backup.cli import app


def main():
    """Main entry point for console script."""
    app()


if __name__ == "__main__":
    main()
