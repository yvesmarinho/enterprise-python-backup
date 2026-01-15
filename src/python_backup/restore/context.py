"""
RestoreContext for managing restore operation state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from python_backup.config.models import DatabaseConfig, StorageConfig


@dataclass
class RestoreContext:
    """
    Context for a restore operation.
    
    Manages state, timing, and metadata for database restore operations.
    """
    
    database_config: Optional[DatabaseConfig]
    storage_config: Optional[StorageConfig]
    backup_file: str
    target_database: Optional[str] = None
    
    # State management
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # File tracking
    downloaded_file: Optional[Path] = None
    decompressed_file: Optional[Path] = None
    
    # Size tracking
    download_size: Optional[int] = None
    restored_size: Optional[int] = None
    
    # Error tracking
    error_message: Optional[str] = None
    
    def start(self) -> None:
        """Mark restore as started."""
        self.status = "running"
        self.start_time = datetime.now()
    
    def complete(self) -> None:
        """Mark restore as completed."""
        self.status = "completed"
        self.end_time = datetime.now()
    
    def fail(self, error_message: str) -> None:
        """Mark restore as failed with error message."""
        self.status = "failed"
        self.end_time = datetime.now()
        self.error_message = error_message
    
    def get_duration(self) -> Optional[timedelta]:
        """Get duration of restore operation."""
        if self.start_time is None:
            return None
        
        end = self.end_time if self.end_time else datetime.now()
        return end - self.start_time
    
    def set_downloaded_file(self, file_path: Path) -> None:
        """Set the path to the downloaded backup file."""
        self.downloaded_file = file_path
    
    def set_decompressed_file(self, file_path: Path) -> None:
        """Set the path to the decompressed backup file."""
        self.decompressed_file = file_path
    
    def set_restored_size(self, size: int) -> None:
        """Set the size of data restored to database."""
        self.restored_size = size
    
    def set_download_size(self, size: int) -> None:
        """Set the size of downloaded backup file."""
        self.download_size = size
    
    def needs_decompression(self) -> bool:
        """Check if backup file needs decompression."""
        return self.backup_file.endswith(('.gz', '.bz2'))
    
    def get_compression_type(self) -> Optional[str]:
        """Get the compression type from filename."""
        if self.backup_file.endswith('.gz'):
            return 'gzip'
        elif self.backup_file.endswith('.bz2'):
            return 'bzip2'
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary representation."""
        result = {
            'status': self.status,
            'backup_file': self.backup_file,
            'target_database': self.target_database,
        }
        
        # Add timestamps if set
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.end_time:
            result['end_time'] = self.end_time.isoformat()
        
        duration = self.get_duration()
        if duration:
            result['duration'] = str(duration)
        
        # Add file paths if set
        if self.downloaded_file:
            result['downloaded_file'] = str(self.downloaded_file)
        if self.decompressed_file:
            result['decompressed_file'] = str(self.decompressed_file)
        
        # Add sizes if set
        if self.download_size:
            result['download_size'] = self.download_size
        if self.restored_size:
            result['restored_size'] = self.restored_size
        
        # Add error if failed
        if self.error_message:
            result['error_message'] = self.error_message
        
        # Add database config (excluding password)
        if self.database_config:
            db_dict = self.database_config.model_dump()
            if 'password' in db_dict:
                db_dict.pop('password')
            result['database_config'] = db_dict
        
        # Add storage config (excluding keys)
        if self.storage_config:
            storage_dict = self.storage_config.model_dump()
            if 'secret_key' in storage_dict:
                storage_dict.pop('secret_key')
            if 'access_key' in storage_dict:
                storage_dict.pop('access_key')
            result['storage_config'] = storage_dict
        
        return result
