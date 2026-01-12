"""Storage module initialization."""

from vya_backupbd.storage.local import LocalStorage
from vya_backupbd.storage.s3 import S3Storage

__all__ = ["LocalStorage", "S3Storage"]
