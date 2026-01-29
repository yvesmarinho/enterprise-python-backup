"""N8N Backup & Restore Module.

Enterprise-grade backup and restore solution for N8N workflows and credentials.
Implements Constitution v1.1.0 compliance with all 5 core principles.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

__version__ = "0.1.0"
__author__ = "Vya Jobs DevOps Team"

# Module metadata
MODULE_INFO = {
    "name": "enterprise_backup.n8n",
    "version": __version__,
    "description": "N8N Backup & Restore Module",
    "constitution_version": "1.1.0",
    "python_requires": ">=3.11",
    "capabilities": [
        "backup_credentials",
        "backup_workflows",
        "restore_credentials",
        "restore_workflows",
        "selective_operations",
        "integrity_validation",
        "cloud_storage",
        "monitoring_alerts",
    ],
}


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string with log data
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "operation_id"):
            log_data["operation_id"] = record.operation_id
        if hasattr(record, "operation_type"):
            log_data["operation_type"] = record.operation_type
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration

        return json.dumps(log_data)


class OperationLogger:
    """Context manager for operation logging with audit trail."""

    def __init__(
        self,
        operation_type: str,
        operation_id: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize operation logger.

        Args:
            operation_type: Type of operation (backup, restore, etc.)
            operation_id: Unique operation ID
            logger: Logger instance (creates new if None)
        """
        self.operation_type = operation_type
        self.operation_id = operation_id
        self.logger = logger or logging.getLogger(__name__)
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def __enter__(self) -> "OperationLogger":
        """Start operation logging."""
        self.start_time = datetime.utcnow()

        self.logger.info(
            f"Operation started: {self.operation_type}",
            extra={
                "operation_id": self.operation_id,
                "operation_type": self.operation_type,
                "status": "started",
            },
        )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """End operation logging."""
        self.end_time = datetime.utcnow()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0

        if exc_type:
            self.logger.error(
                f"Operation failed: {self.operation_type}",
                extra={
                    "operation_id": self.operation_id,
                    "operation_type": self.operation_type,
                    "status": "failed",
                    "duration": duration,
                    "error": str(exc_val),
                },
                exc_info=(exc_type, exc_val, exc_tb),
            )
        else:
            self.logger.info(
                f"Operation completed: {self.operation_type}",
                extra={
                    "operation_id": self.operation_id,
                    "operation_type": self.operation_type,
                    "status": "completed",
                    "duration": duration,
                },
            )

    def log(self, message: str, level: str = "info", **kwargs: Any) -> None:
        """Log message with operation context.

        Args:
            message: Log message
            level: Log level (debug, info, warning, error, critical)
            **kwargs: Additional fields to include
        """
        extra = {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            **kwargs,
        }

        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra=extra)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[Path] = None,
    audit_log_file: Optional[Path] = None,
) -> logging.Logger:
    """Setup structured logging for the module.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Optional file path for general logs
        audit_log_file: Optional file path for audit logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("enterprise_backup.n8n")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    if log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        if log_format == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )

        logger.addHandler(file_handler)

    # Audit log handler (if specified)
    if audit_log_file:
        audit_log_file = Path(audit_log_file)
        audit_log_file.parent.mkdir(parents=True, exist_ok=True)

        audit_handler = logging.FileHandler(audit_log_file)
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(JSONFormatter())  # Always JSON for audit

        # Create separate audit logger
        audit_logger = logging.getLogger("enterprise_backup.n8n.audit")
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)

    return logger


# Initialize default logger
_default_logger = setup_logging()


def get_logger() -> logging.Logger:
    """Get module logger instance.

    Returns:
        Configured logger
    """
    return logging.getLogger("enterprise_backup.n8n")


# Export public API
__all__ = [
    # Version and metadata
    "__version__",
    "MODULE_INFO",
    # Logging
    "setup_logging",
    "get_logger",
    "OperationLogger",
    "JSONFormatter",
    # Core classes
    "N8NBackup",
    "N8NRestore",
    # Models
    "BackupType",
    "OperationStatus",
    "BackupOperation",
    "RestoreOperation",
    "BackupMetadata",
    "N8NCredential",
    "N8NWorkflow",
    # Storage
    "BackupRepository",
    "LocalRepository",
    # Exceptions
    "N8NBackupError",
    "BackupError",
    "RestoreError",
    "ValidationError",
    "DockerError",
    "N8NError",
    "StorageError",
    "EncryptionKeyError",
    # CLI
    "n8n_cli",
]

# Lazy imports for better startup performance
def __getattr__(name: str):
    """Lazy import of module components."""
    if name == "N8NBackup":
        from .backup import N8NBackup
        return N8NBackup
    elif name == "N8NRestore":
        from .restore import N8NRestore
        return N8NRestore
    elif name in ("BackupType", "OperationStatus", "BackupOperation", "RestoreOperation", "BackupMetadata", "N8NCredential", "N8NWorkflow"):
        from .models import (
            BackupType,
            OperationStatus,
            BackupOperation,
            RestoreOperation,
            BackupMetadata,
            N8NCredential,
            N8NWorkflow,
        )
        return locals()[name]
    elif name in ("BackupRepository", "LocalRepository"):
        from .storage import BackupRepository, LocalRepository
        return locals()[name]
    elif name in ("N8NBackupError", "BackupError", "RestoreError", "ValidationError", "DockerError", "N8NError", "StorageError", "EncryptionKeyError"):
        from .exceptions import (
            N8NBackupError,
            BackupError,
            RestoreError,
            ValidationError,
            DockerError,
            N8NError,
            StorageError,
            EncryptionKeyError,
        )
        return locals()[name]
    elif name == "n8n_cli":
        from .cli import n8n_cli
        return n8n_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

