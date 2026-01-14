"""
Backup file management utilities.

Provides functions to discover, list, and analyze backup files.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BackupMetadata:
    """Metadata extracted from backup filename."""
    file_path: str
    filename: str
    date: datetime
    dbms_type: str  # 'mysql' or 'postgresql'
    database: str
    extension: str  # '.sql', '.gz', or '.zip'
    size_bytes: int
    is_compressed: bool


class BackupManager:
    """
    Manager for backup file operations.
    
    Handles listing, filtering, and analyzing backup files.
    
    Example:
        >>> manager = BackupManager("/tmp/bkpzip")
        >>> backups = manager.list_backups(database="mydb", limit=10)
        >>> latest = manager.find_latest_backup("mydb", "mysql")
    """
    
    # Filename pattern: YYYYMMDD_HHMMSS_dbms_database.ext
    # Supports: mysql, postgresql, files
    # Extensions: .sql, .gz, .zip, .tar.gz
    FILENAME_PATTERN = re.compile(
        r'^(\d{8})_(\d{6})_(mysql|postgresql|files)_(.+?)\.(sql|gz|zip|tar\.gz)$'
    )
    
    def __init__(self, backup_dir: str):
        """
        Initialize BackupManager.
        
        Args:
            backup_dir: Directory containing backup files
        """
        self.backup_dir = Path(backup_dir)
        logger.debug(f"BackupManager initialized with directory: {backup_dir}")
    
    def list_backups(
        self,
        database: Optional[str] = None,
        dbms_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[BackupMetadata]:
        """
        List available backup files with optional filtering.
        
        Args:
            database: Filter by database name (optional)
            dbms_type: Filter by DBMS type ('mysql' or 'postgresql', optional)
            limit: Maximum number of backups to return (optional)
            
        Returns:
            List of BackupMetadata objects sorted by date (newest first)
        """
        logger.debug(f"Listing backups - database={database}, dbms_type={dbms_type}, limit={limit}")
        
        if not self.backup_dir.exists():
            logger.warning(f"Backup directory does not exist: {self.backup_dir}")
            return []
        
        backups = []
        
        # Search for all backup files
        for pattern in ['*.sql', '*.gz', '*.zip']:
            for file_path in self.backup_dir.glob(pattern):
                if not file_path.is_file():
                    continue
                
                metadata = self.get_backup_metadata(str(file_path))
                if metadata is None:
                    continue
                
                # Apply filters
                if database and metadata.database != database:
                    continue
                
                if dbms_type and metadata.dbms_type != dbms_type:
                    continue
                
                backups.append(metadata)
        
        # Sort by date descending (newest first)
        backups.sort(key=lambda x: x.date, reverse=True)
        
        # Apply limit
        if limit is not None and limit > 0:
            backups = backups[:limit]
        
        logger.debug(f"Found {len(backups)} backup files")
        return backups
    
    def get_backup_metadata(self, file_path: str) -> Optional[BackupMetadata]:
        """
        Extract metadata from backup filename.
        
        Args:
            file_path: Path to backup file
            
        Returns:
            BackupMetadata object or None if filename doesn't match pattern
        """
        path = Path(file_path)
        filename = path.name
        
        # Parse filename
        match = self.FILENAME_PATTERN.match(filename)
        if not match:
            logger.debug(f"Filename does not match pattern: {filename}")
            return None
        
        date_str, time_str, dbms_type, database, extension = match.groups()
        
        # Parse date and time
        try:
            date = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except ValueError as e:
            logger.warning(f"Could not parse date/time from filename {filename}: {e}")
            return None
        
        # Get file size
        try:
            size_bytes = path.stat().st_size
        except OSError as e:
            logger.warning(f"Could not get file size for {file_path}: {e}")
            size_bytes = 0
        
        # Determine if compressed
        is_compressed = extension in ('gz', 'zip')
        
        return BackupMetadata(
            file_path=str(path),
            filename=filename,
            date=date,
            dbms_type=dbms_type,
            database=database,
            extension=f".{extension}",
            size_bytes=size_bytes,
            is_compressed=is_compressed
        )
    
    def find_latest_backup(
        self,
        database: str,
        dbms_type: Optional[str] = None,
        compressed_only: bool = False
    ) -> Optional[BackupMetadata]:
        """
        Find the most recent backup for a database.
        
        Args:
            database: Database name
            dbms_type: Filter by DBMS type (optional)
            compressed_only: Only return compressed backups (optional)
            
        Returns:
            BackupMetadata of most recent backup or None if not found
        """
        logger.debug(
            f"Finding latest backup - database={database}, "
            f"dbms_type={dbms_type}, compressed_only={compressed_only}"
        )
        
        # Get all backups for this database
        backups = self.list_backups(database=database, dbms_type=dbms_type)
        
        # Filter by compression if requested
        if compressed_only:
            backups = [b for b in backups if b.is_compressed]
        
        # Return first (newest) or None
        if backups:
            logger.debug(f"Found latest backup: {backups[0].filename}")
            return backups[0]
        else:
            logger.debug(f"No backup found for database: {database}")
            return None
    
    def get_backup_count(
        self,
        database: Optional[str] = None,
        dbms_type: Optional[str] = None
    ) -> int:
        """
        Count total number of backups.
        
        Args:
            database: Filter by database name (optional)
            dbms_type: Filter by DBMS type (optional)
            
        Returns:
            Number of backup files matching criteria
        """
        backups = self.list_backups(database=database, dbms_type=dbms_type)
        return len(backups)
    
    def format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g., "1.23 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def list_backups(
    backup_dir: str,
    database: Optional[str] = None,
    dbms_type: Optional[str] = None,
    limit: Optional[int] = 10
) -> List[Dict]:
    """
    Convenience function to list backups.
    
    Args:
        backup_dir: Directory containing backups
        database: Filter by database name (optional)
        dbms_type: Filter by DBMS type (optional)
        limit: Maximum number of backups to return (optional)
        
    Returns:
        List of dictionaries with backup information
    """
    manager = BackupManager(backup_dir)
    backups = manager.list_backups(database=database, dbms_type=dbms_type, limit=limit)
    
    # Convert to dictionaries
    return [
        {
            'file_path': b.file_path,
            'filename': b.filename,
            'date': b.date,
            'dbms_type': b.dbms_type,
            'database': b.database,
            'extension': b.extension,
            'size_bytes': b.size_bytes,
            'size_formatted': manager.format_size(b.size_bytes),
            'is_compressed': b.is_compressed
        }
        for b in backups
    ]