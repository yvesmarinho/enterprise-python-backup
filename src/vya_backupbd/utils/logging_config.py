"""
Logging configuration for VYA BackupDB.

Configures logging to file and console based on vya_backupbd.json settings.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    log_dir: str = "/var/log/enterprise",
    app_name: str = "vya_backupdb"
) -> None:
    """
    Setup logging configuration.
    
    Args:
        console_level: Console log level (INFO, DEBUG, WARNING, ERROR)
        file_level: File log level (INFO, DEBUG, WARNING, ERROR)
        log_dir: Directory for log files (default: /var/log/enterprise)
        app_name: Application name for log file
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fallback to user's home directory if no permission
        log_path = Path.home() / ".local" / "log" / "enterprise"
        log_path.mkdir(parents=True, exist_ok=True)
        print(f"Warning: No permission to write to {log_dir}, using {log_path}", file=sys.stderr)
    
    # Generate log filename with date and time
    log_file = log_path / f"{app_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    try:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Log startup message
        root_logger.info("=" * 80)
        root_logger.info(f"VYA BackupDB started - Log file: {log_file}")
        root_logger.info("=" * 80)
        
    except Exception as e:
        print(f"Warning: Could not create log file {log_file}: {e}", file=sys.stderr)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
