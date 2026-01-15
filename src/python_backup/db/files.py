"""
Files backup adapter implementation.

Provides file-based backup operations using tar.gz compression
and glob pattern matching for flexible file selection.
"""

import subprocess
import logging
import os
import tarfile
import glob
from pathlib import Path
from typing import Any
from datetime import datetime

from python_backup.config.loader import DatabaseConfig
from python_backup.db.base import DatabaseAdapter
from python_backup.utils.log_sanitizer import safe_repr

logger = logging.getLogger(__name__)


class FilesAdapter(DatabaseAdapter):
    """
    Files backup adapter.
    
    Implements backup operations for files and directories using tar.gz
    compression with glob pattern support.
    
    Example:
        >>> config = DatabaseConfig(dbms="files", db_list=["/data/**/*.pdf"], ...)
        >>> with FilesAdapter(config) as adapter:
        ...     patterns = adapter.get_databases()
        ...     adapter.backup_database("/data/**/*.pdf", "/backups/files.tar.gz")
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize Files adapter.
        
        Args:
            config: Database configuration (dbms must be 'files')
            
        Raises:
            ValueError: If config dbms is not 'files'
        """
        logger.debug(f"=== Função: __init__ (FilesAdapter) ===")
        logger.debug(f"==> PARAM: config TYPE: {type(config)}, CONTENT: {safe_repr(config)}")
        
        # Check dbms field (loader.py uses 'dbms', models.py uses 'type')
        dbms_type = getattr(config, 'dbms', None) or getattr(config, 'type', None)
        
        if dbms_type != "files":
            raise ValueError(
                f"Files adapter requires dbms='files', got '{dbms_type}'"
            )
        
        # Files adapter doesn't need SQLAlchemy engine
        self.config = config
        self._engine = None
        
        logger.debug(f"=== Término Função: __init__ (FilesAdapter) ===")
    
    @property
    def engine(self):
        """Files adapter doesn't use database engine."""
        return None
    
    def get_databases(self) -> list[str]:
        """
        Get list of file patterns from db_list.
        
        Returns:
            List of glob patterns for file backup
        """
        logger.debug(f"=== Função: get_databases (FilesAdapter) ===")
        
        # Get db_list from config (loader.py has it, models.py doesn't)
        patterns = getattr(self.config, 'db_list', [])
        if not patterns:
            patterns = []
        
        logger.debug(f"Found {len(patterns)} file patterns")
        logger.debug(f"=== Término Função: get_databases (FilesAdapter) ===")
        
        return patterns
    
    def test_connection(self) -> bool:
        """
        Test if base directories exist and are accessible.
        
        Returns:
            True if directories are accessible, False otherwise
        """
        logger.debug(f"=== Função: test_connection (FilesAdapter) ===")
        
        try:
            patterns = self.get_databases()
            if not patterns:
                logger.warning("No file patterns configured")
                return False
            
            # Test if at least one base directory exists
            for pattern in patterns:
                base_path = self._extract_base_path(pattern)
                if base_path and os.path.exists(base_path):
                    logger.debug(f"Base path exists and accessible: {base_path}")
                    logger.debug(f"=== Término Função: test_connection (FilesAdapter) ===")
                    return True
            
            logger.warning("No accessible base paths found")
            logger.debug(f"=== Término Função: test_connection (FilesAdapter) ===")
            return False
            
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            logger.debug(f"=== Término Função: test_connection (FilesAdapter) COM ERRO ===")
            return False
    
    def _extract_base_path(self, pattern: str) -> str:
        """
        Extract base directory path from glob pattern.
        
        Args:
            pattern: Glob pattern (e.g., "/data/**/*.pdf")
            
        Returns:
            Base directory path without wildcards
        """
        # Remove glob wildcards to get base path
        parts = pattern.split('/')
        base_parts = []
        for part in parts:
            if '*' in part or '{' in part or '?' in part:
                break
            base_parts.append(part)
        
        return '/'.join(base_parts) if base_parts else '/'
    
    def _expand_pattern(self, pattern: str) -> list[str]:
        """
        Expand glob pattern to list of files.
        
        Args:
            pattern: Glob pattern (supports *, **, {}, ?)
            
        Returns:
            List of file paths matching pattern
        """
        logger.debug(f"Expanding pattern: {pattern}")
        
        # Use pathlib for better glob support
        if '**' in pattern:
            # Recursive glob
            base_path = self._extract_base_path(pattern)
            relative_pattern = pattern[len(base_path):].lstrip('/')
            path = Path(base_path)
            files = [str(p) for p in path.glob(relative_pattern) if p.is_file()]
        else:
            # Standard glob
            files = [f for f in glob.glob(pattern, recursive=False) if os.path.isfile(f)]
        
        logger.debug(f"Pattern matched {len(files)} files")
        return files
    
    def get_backup_command(self, pattern: str, output_path: str) -> str:
        """
        Get tar command for backup (for logging).
        
        Args:
            pattern: Glob pattern to backup
            output_path: Output tar.gz file path
            
        Returns:
            Command string representation
        """
        logger.debug(f"=== Função: get_backup_command (FilesAdapter) ===")
        
        command = f"tar -czf {output_path} <files matching: {pattern}>"
        
        logger.debug(f"=== Término Função: get_backup_command (FilesAdapter) ===")
        return command
    
    def backup_database(self, pattern: str, output_path: str) -> bool:
        """
        Backup files matching pattern to tar.gz.
        
        Args:
            pattern: Glob pattern to backup
            output_path: Path where tar.gz should be saved
            
        Returns:
            True if backup successful, False otherwise
        """
        logger.debug(f"=== Função: backup_database (FilesAdapter) ===")
        logger.debug(f"==> PARAM: pattern TYPE: {type(pattern)}, SIZE: {len(pattern)} chars, CONTENT: {pattern}")
        logger.debug(f"==> PARAM: output_path TYPE: {type(output_path)}, SIZE: {len(output_path)} chars, CONTENT: {output_path}")
        
        try:
            # Expand pattern to get file list
            files = self._expand_pattern(pattern)
            
            if not files:
                logger.warning(f"No files found matching pattern: {pattern}")
                return False
            
            logger.info(f"Starting backup of {len(files)} files matching '{pattern}' to '{output_path}'")
            
            # Create tar.gz with matched files
            with tarfile.open(output_path, 'w:gz') as tar:
                for file_path in files:
                    try:
                        # Add file preserving path structure
                        arcname = file_path  # Keep full path in archive
                        tar.add(file_path, arcname=arcname)
                        logger.debug(f"Added to archive: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to add file {file_path}: {e}")
                        continue
            
            # Verify archive was created
            if os.path.exists(output_path):
                archive_size = os.path.getsize(output_path)
                logger.info(f"Backup completed successfully: {len(files)} files, {archive_size} bytes")
                logger.debug(f"=== Término Função: backup_database (FilesAdapter) ===")
                return True
            else:
                logger.error("Archive file was not created")
                logger.debug(f"=== Término Função: backup_database (FilesAdapter) COM ERRO ===")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            logger.debug(f"=== Término Função: backup_database (FilesAdapter) COM ERRO ===")
            return False
    
    def restore_database(self, pattern: str, backup_file: str, target_dir: str = None) -> bool:
        """
        Restore files from tar.gz backup.
        
        Args:
            pattern: Original pattern (used for naming/logging)
            backup_file: Path to tar.gz backup file
            target_dir: Target directory for restore (if None, restore to original paths)
            
        Returns:
            True if restore successful, False otherwise
        """
        logger.debug(f"=== Função: restore_database (FilesAdapter) ===")
        logger.debug(f"==> PARAM: pattern TYPE: {type(pattern)}, CONTENT: {pattern}")
        logger.debug(f"==> PARAM: backup_file TYPE: {type(backup_file)}, CONTENT: {backup_file}")
        logger.debug(f"==> PARAM: target_dir TYPE: {type(target_dir) if target_dir else None}, CONTENT: {target_dir}")
        
        try:
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return False
            
            logger.info(f"Starting restore from '{backup_file}'")
            
            # Determine extraction path
            extract_path = target_dir if target_dir else '/'
            
            # Create target directory if needed
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                logger.debug(f"Created target directory: {target_dir}")
            
            # Extract tar.gz
            with tarfile.open(backup_file, 'r:gz') as tar:
                # Get list of members
                members = tar.getmembers()
                logger.info(f"Extracting {len(members)} files/directories")
                
                # Extract all files
                tar.extractall(path=extract_path)
                logger.debug(f"Files extracted to: {extract_path}")
            
            logger.info(f"Restore completed successfully: {len(members)} items")
            logger.debug(f"=== Término Função: restore_database (FilesAdapter) ===")
            return True
                
        except tarfile.TarError as e:
            logger.error(f"Error extracting tar archive: {e}")
            logger.debug(f"=== Término Função: restore_database (FilesAdapter) COM ERRO ===")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during restore: {e}")
            logger.debug(f"=== Término Função: restore_database (FilesAdapter) COM ERRO ===")
            return False
    
    def filter_system_databases(self, databases: list[str]) -> list[str]:
        """
        Filter system patterns (not applicable for files).
        
        Args:
            databases: List of patterns
            
        Returns:
            Same list (no filtering for files)
        """
        return databases
    
    def __enter__(self):
        """Context manager entry (no connection needed for files)."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (no cleanup needed for files)."""
        pass
