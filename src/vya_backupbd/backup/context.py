"""
BackupContext class for managing backup state and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from vya_backupbd.config.models import DatabaseConfig, StorageConfig, BackupConfig


@dataclass
class BackupContext:
    """
    Context object that holds all configuration and state for a backup operation.
    
    Tracks:
    - Configuration (database, storage, backup settings)
    - Timing (start/end times, duration)
    - Status (pending, running, completed, failed)
    - Metadata (file paths, sizes, compression info)
    - Errors (error messages)
    """
    
    database_config: Optional[DatabaseConfig] = None
    storage_config: Optional[StorageConfig] = None
    backup_config: Optional[BackupConfig] = None
    
    # State
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Backup metadata
    backup_file: Optional[Path] = None
    backup_size: Optional[int] = None
    compressed_size: Optional[int] = None
    storage_location: Optional[str] = None
    
    def start(self) -> None:
        """Mark backup as started and record start time."""
        self.start_time = datetime.now()
        self.status = "running"
    
    def complete(self) -> None:
        """Mark backup as completed and record end time."""
        self.end_time = datetime.now()
        self.status = "completed"
    
    def fail(self, error_message: str) -> None:
        """Mark backup as failed and record error message."""
        self.end_time = datetime.now()
        self.status = "failed"
        self.error_message = error_message
    
    def get_duration(self) -> Optional[timedelta]:
        """
        Get the duration of the backup operation.
        
        Returns:
            timedelta if backup has started, None otherwise
        """
        if self.start_time is None:
            return None
        
        end = self.end_time if self.end_time else datetime.now()
        return end - self.start_time
    
    def set_backup_file(self, path: Path) -> None:
        """Set the backup file path."""
        self.backup_file = path
    
    def set_backup_size(self, size_bytes: int) -> None:
        """Set the backup file size in bytes."""
        self.backup_size = size_bytes
    
    def set_compressed_size(self, size_bytes: int) -> None:
        """Set the compressed backup size in bytes."""
        self.compressed_size = size_bytes
    
    def set_storage_location(self, location: str) -> None:
        """Set the storage location (S3 key or local path)."""
        self.storage_location = location
    
    def get_compression_ratio(self) -> Optional[float]:
        """
        Calculate compression ratio.
        
        Returns:
            Ratio (original_size / compressed_size) or None if not compressed
        """
        if self.backup_size and self.compressed_size:
            return self.backup_size / self.compressed_size
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for serialization.
        
        Returns:
            Dictionary representation (excludes sensitive data)
        """
        duration = self.get_duration()
        
        data = {
            "database_type": self.database_config.type if self.database_config else None,
            "database_name": self.database_config.database if self.database_config else None,
            "storage_type": self.storage_config.type if self.storage_config else None,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration.total_seconds() if duration else None,
            "backup_file": str(self.backup_file) if self.backup_file else None,
            "backup_size": self.backup_size,
            "compressed_size": self.compressed_size,
            "storage_location": self.storage_location,
            "compression_ratio": self.get_compression_ratio(),
            "error_message": self.error_message,
        }
        
        return data
