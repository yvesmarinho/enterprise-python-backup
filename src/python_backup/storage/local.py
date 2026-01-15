"""
Local file system storage implementation.

Handles backup storage operations on the local file system including
upload, download, listing, and deletion of backup files.
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import fnmatch

logger = logging.getLogger(__name__)


class LocalStorage:
    """
    Local file system storage for backups.
    
    Provides methods to store, retrieve, list, and delete backup files
    on the local file system.
    """
    
    def __init__(self, base_path: str | Path):
        """
        Initialize local storage.
        
        Args:
            base_path: Base directory for storing backups
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized LocalStorage at: {self.base_path}")
    
    def upload(self, source_file: str | Path, dest_name: str) -> bool:
        """
        Upload (copy) a file to storage.
        
        Args:
            source_file: Source file path
            dest_name: Destination file name (relative to base_path)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            source = Path(source_file)
            if not source.exists():
                logger.error(f"Source file not found: {source}")
                return False
            
            dest = self.base_path / dest_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source, dest)
            logger.info(f"Uploaded {source} to {dest}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def download(self, source_name: str, dest_file: str | Path) -> bool:
        """
        Download (copy) a file from storage.
        
        Args:
            source_name: Source file name (relative to base_path)
            dest_file: Destination file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            source = self.base_path / source_name
            if not source.exists():
                logger.error(f"Source file not found in storage: {source_name}")
                return False
            
            dest = Path(dest_file)
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source, dest)
            logger.info(f"Downloaded {source_name} to {dest}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def list_files(self, pattern: Optional[str] = None, 
                   sort_by: Optional[str] = None,
                   reverse: bool = False) -> List[str]:
        """
        List files in storage.
        
        Args:
            pattern: Optional glob pattern to filter files (e.g., "*.sql")
            sort_by: Sort by 'name' or 'time' (modification time)
            reverse: Reverse sort order
            
        Returns:
            list: List of file names (relative to base_path)
        """
        try:
            files = []
            
            # Recursively find all files
            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.base_path)
                    relative_str = str(relative_path).replace("\\", "/")
                    
                    # Apply pattern filter
                    if pattern:
                        if fnmatch.fnmatch(relative_path.name, pattern):
                            files.append(relative_str)
                    else:
                        files.append(relative_str)
            
            # Sort if requested
            if sort_by == "time":
                files.sort(
                    key=lambda f: (self.base_path / f).stat().st_mtime,
                    reverse=reverse
                )
            elif sort_by == "name":
                files.sort(reverse=reverse)
            
            logger.debug(f"Listed {len(files)} files")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def delete(self, file_name: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_name: File name (relative to base_path)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = self.base_path / file_name
            
            if not file_path.exists():
                logger.warning(f"File not found for deletion: {file_name}")
                return False
            
            file_path.unlink()
            logger.info(f"Deleted file: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def exists(self, file_name: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_name: File name (relative to base_path)
            
        Returns:
            bool: True if file exists, False otherwise
        """
        file_path = self.base_path / file_name
        return file_path.exists()
    
    def get_size(self, file_name: str) -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            file_name: File name (relative to base_path)
            
        Returns:
            int: File size in bytes, or None if file doesn't exist
        """
        try:
            file_path = self.base_path / file_name
            if not file_path.exists():
                return None
            
            return file_path.stat().st_size
            
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return None
    
    def get_modification_time(self, file_name: str) -> Optional[datetime]:
        """
        Get file modification time.
        
        Args:
            file_name: File name (relative to base_path)
            
        Returns:
            datetime: Modification time, or None if file doesn't exist
        """
        try:
            file_path = self.base_path / file_name
            if not file_path.exists():
                return None
            
            timestamp = file_path.stat().st_mtime
            return datetime.fromtimestamp(timestamp)
            
        except Exception as e:
            logger.error(f"Error getting modification time: {e}")
            return None
    
    def get_total_size(self) -> int:
        """
        Get total size of all files in storage.
        
        Returns:
            int: Total size in bytes
        """
        try:
            total = 0
            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    total += file_path.stat().st_size
            
            logger.debug(f"Total storage size: {total} bytes")
            return total
            
        except Exception as e:
            logger.error(f"Error calculating total size: {e}")
            return 0
    
    def clean_empty_directories(self) -> None:
        """Remove empty directories from storage."""
        try:
            # Walk from deepest to shallowest
            for dirpath in sorted(self.base_path.rglob("*"), reverse=True):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    logger.debug(f"Removed empty directory: {dirpath}")
                    
        except Exception as e:
            logger.error(f"Error cleaning empty directories: {e}")
