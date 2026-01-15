"""Storage module initialization."""

from python_backup.storage.local import LocalStorage
from python_backup.storage.s3 import S3Storage

__all__ = ["LocalStorage", "S3Storage"]
