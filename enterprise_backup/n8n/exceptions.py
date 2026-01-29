"""Custom exceptions for N8N backup and restore operations."""

from typing import Optional


class N8NBackupError(Exception):
    """Base exception for all N8N backup/restore errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        """Initialize exception with message and optional details.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class BackupError(N8NBackupError):
    """Raised when backup operation fails."""

    pass


class RestoreError(N8NBackupError):
    """Raised when restore operation fails."""

    pass


class ValidationError(N8NBackupError):
    """Raised when validation checks fail."""

    pass


class DockerError(N8NBackupError):
    """Raised when Docker operations fail."""

    pass


class N8NError(N8NBackupError):
    """Raised when N8N CLI commands fail."""

    pass


class StorageError(N8NBackupError):
    """Raised when storage operations (S3, Azure, local) fail."""

    pass


class EncryptionKeyError(N8NBackupError):
    """Raised when N8N_ENCRYPTION_KEY is missing or mismatched."""

    pass


class HealthcheckError(N8NBackupError):
    """Raised when N8N healthcheck fails after restart."""

    pass


class DiskSpaceError(N8NBackupError):
    """Raised when insufficient disk space is available."""

    pass
