"""
VYA BackupDB - Main entry point for CLI execution.

This module allows the package to be executed as:
    python -m vya_backupbd
"""

from vya_backupbd.cli import app

if __name__ == "__main__":
    app()
