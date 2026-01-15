"""
Restore strategies for database restore operations.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import mkdtemp
from typing import Dict, List, Type

from python_backup.restore.context import RestoreContext
from python_backup.db.postgresql import PostgreSQLAdapter
from python_backup.db.mysql import MySQLAdapter
from python_backup.db.files import FilesAdapter
from python_backup.storage.local import LocalStorage
from python_backup.storage.s3 import S3Storage
from python_backup.utils.compression import decompress_file

logger = logging.getLogger(__name__)


def get_database_adapter(db_config):
    """Get appropriate database adapter based on config."""
    if db_config.type == "postgresql":
        return PostgreSQLAdapter(db_config)
    elif db_config.type == "mysql":
        return MySQLAdapter(db_config)
    elif db_config.type == "files":
        return FilesAdapter(db_config)
    else:
        raise ValueError(f"Unsupported database type: {db_config.type}")


def get_storage_adapter(storage_config):
    """Get appropriate storage adapter based on config."""
    if storage_config.type == "local":
        return LocalStorage(storage_config)
    elif storage_config.type == "s3":
        return S3Storage(storage_config)
    else:
        raise ValueError(f"Unsupported storage type: {storage_config.type}")


class RestoreStrategy(ABC):
    """Abstract base class for restore strategies."""
    
    @abstractmethod
    def execute(self, context: RestoreContext) -> bool:
        """
        Execute the restore strategy.
        
        Args:
            context: RestoreContext with configuration and state
            
        Returns:
            bool: True if restore successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this strategy."""
        pass


class FullRestoreStrategy(RestoreStrategy):
    """
    Full database restore strategy.
    
    Restores a complete database backup from storage.
    """
    
    def get_name(self) -> str:
        """Get strategy name."""
        return "full"
    
    def execute(self, context: RestoreContext) -> bool:
        """
        Execute full database restore.
        
        Steps:
        1. Create storage adapter
        2. Create temp directory for downloaded files
        3. Download backup from storage
        4. Decompress if needed
        5. Create database adapter
        6. Restore database from backup
        7. Update context with completion status
        
        Args:
            context: RestoreContext with configuration
            
        Returns:
            bool: True if restore successful, False otherwise
        """
        try:
            logger.info(f"Starting full restore of {context.backup_file}")
            
            # Create storage adapter
            storage_adapter = get_storage_adapter(context.storage_config)
            
            # Create temp directory
            temp_dir = Path(mkdtemp(prefix="vya_restore_"))
            logger.info(f"Created temp directory: {temp_dir}")
            
            # Download backup file
            download_path = temp_dir / Path(context.backup_file).name
            logger.info(f"Downloading backup to {download_path}")
            
            if not storage_adapter.download(context.backup_file, str(download_path)):
                context.fail("Failed to download backup file from storage")
                return False
            
            context.set_downloaded_file(download_path)
            context.set_download_size(download_path.stat().st_size)
            logger.info(f"Downloaded {context.download_size} bytes")
            
            # Decompress if needed
            restore_file = download_path
            if context.needs_decompression():
                compression_type = context.get_compression_type()
                logger.info(f"Decompressing backup ({compression_type})")
                
                decompressed_path = temp_dir / Path(context.backup_file).stem
                if decompressed_path.suffix in ['.gz', '.bz2']:
                    decompressed_path = decompressed_path.with_suffix('')
                
                if not decompress_file(
                    str(download_path),
                    str(decompressed_path),
                    method=compression_type
                ):
                    context.fail("Failed to decompress backup file")
                    return False
                
                context.set_decompressed_file(decompressed_path)
                restore_file = decompressed_path
                logger.info(f"Decompressed to {restore_file}")
            
            # Create database adapter
            db_adapter = get_database_adapter(context.database_config)
            
            # Determine target database (use target_database if specified, otherwise use config)
            target_db = context.target_database or context.database_config.database
            logger.info(f"Restoring to database: {target_db}")
            
            # Restore database
            if not db_adapter.restore_database(target_db, str(restore_file)):
                context.fail("Failed to restore database from backup")
                return False
            
            # Set restored size
            context.set_restored_size(restore_file.stat().st_size)
            
            # Mark as complete
            context.complete()
            logger.info("Restore completed successfully")
            
            return True
            
        except Exception as e:
            error_msg = f"Restore failed with exception: {str(e)}"
            logger.error(error_msg, exc_info=True)
            context.fail(error_msg)
            return False


class RestoreStrategyFactory:
    """Factory for creating restore strategies."""
    
    _strategies: Dict[str, Type[RestoreStrategy]] = {
        "full": FullRestoreStrategy,
    }
    
    @classmethod
    def create(cls, strategy_name: str) -> RestoreStrategy:
        """
        Create a restore strategy by name.
        
        Args:
            strategy_name: Name of the strategy (case-insensitive)
            
        Returns:
            RestoreStrategy: Instance of the requested strategy
            
        Raises:
            ValueError: If strategy name is unknown
        """
        if not strategy_name:
            raise ValueError("Strategy name cannot be empty")
        
        strategy_name_lower = strategy_name.lower()
        
        if strategy_name_lower not in cls._strategies:
            raise ValueError(
                f"Unknown restore strategy: {strategy_name}. "
                f"Available: {', '.join(cls._strategies.keys())}"
            )
        
        strategy_class = cls._strategies[strategy_name_lower]
        return strategy_class()
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available restore strategies."""
        return list(cls._strategies.keys())
    
    @classmethod
    def is_available(cls, strategy_name: str) -> bool:
        """Check if a strategy is available."""
        return strategy_name.lower() in cls._strategies
