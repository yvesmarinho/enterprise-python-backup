"""
Backup strategy implementations using the Strategy pattern.

Strategies define different backup approaches (full, incremental, differential).
"""

import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional

from vya_backupbd.backup.context import BackupContext
from vya_backupbd.db.mysql import MySQLAdapter
from vya_backupbd.db.postgresql import PostgreSQLAdapter
from vya_backupbd.storage.local import LocalStorage
from vya_backupbd.storage.s3 import S3Storage
from vya_backupbd.utils.compression import compress_file

logger = logging.getLogger(__name__)


def get_database_adapter(db_config):
    """Get database adapter based on configuration."""
    if db_config.type == "mysql":
        return MySQLAdapter(db_config)
    elif db_config.type == "postgresql":
        return PostgreSQLAdapter(db_config)
    else:
        raise ValueError(f"Unknown database type: {db_config.type}")


def get_storage_adapter(storage_config):
    """Get storage adapter based on configuration."""
    if storage_config.type == "local":
        return LocalStorage(base_path=storage_config.path)
    elif storage_config.type == "s3":
        return S3Storage(
            bucket=storage_config.bucket,
            region=storage_config.region,
            access_key=storage_config.access_key,
            secret_key=storage_config.secret_key,
            prefix=storage_config.prefix
        )
    else:
        raise ValueError(f"Unknown storage type: {storage_config.type}")


class BackupStrategy(ABC):
    """Abstract base class for backup strategies."""
    
    @abstractmethod
    def execute(self, context: BackupContext) -> bool:
        """
        Execute the backup strategy.
        
        Args:
            context: BackupContext with configuration and state
            
        Returns:
            True if backup succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the strategy name."""
        pass


class FullBackupStrategy(BackupStrategy):
    """
    Full backup strategy - complete database dump.
    
    Process:
    1. Create temporary directory
    2. Dump database to file
    3. Compress if configured
    4. Upload to storage
    5. Update context with metadata
    """
    
    def get_name(self) -> str:
        """Get strategy name."""
        return "full"
    
    def execute(self, context: BackupContext) -> bool:
        """
        Execute full backup.
        
        Args:
            context: BackupContext with configuration
            
        Returns:
            True if backup succeeded, False otherwise
        """
        try:
            logger.info(f"Starting full backup for database: {context.database_config.database}")
            
            # Step 1: Create database adapter
            db_adapter = get_database_adapter(context.database_config)
            
            # Step 2: Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_name = context.database_config.database
            filename = f"{db_name}_{timestamp}.sql"
            
            # Step 3: Create temp directory and dump path
            temp_dir = Path(tempfile.mkdtemp())
            dump_file = temp_dir / filename
            
            logger.info(f"Dumping database to: {dump_file}")
            
            # Step 4: Perform database dump
            database_name = context.database_config.database
            success = db_adapter.backup_database(database_name, str(dump_file))
            if not success:
                error_msg = "Database dump failed"
                logger.error(error_msg)
                context.fail(error_msg)
                return False
            
            # Step 5: Get dump size
            dump_size = dump_file.stat().st_size
            context.set_backup_file(dump_file)
            context.set_backup_size(dump_size)
            
            logger.info(f"Database dumped successfully ({dump_size} bytes)")
            
            # Step 6: Compress if configured
            file_to_upload = dump_file
            if context.backup_config.compression:
                compressed_file = self._compress_backup(dump_file, context)
                if compressed_file:
                    file_to_upload = compressed_file
                    compressed_size = compressed_file.stat().st_size
                    context.set_compressed_size(compressed_size)
                    logger.info(f"Compressed to {compressed_size} bytes (ratio: {context.get_compression_ratio():.2f})")
            
            # Step 7: Upload to storage
            storage = get_storage_adapter(context.storage_config)
            storage_filename = file_to_upload.name
            
            logger.info(f"Uploading to storage: {storage_filename}")
            
            upload_success = storage.upload(str(file_to_upload), storage_filename)
            if not upload_success:
                error_msg = "Storage upload failed"
                logger.error(error_msg)
                context.fail(error_msg)
                return False
            
            # Step 8: Update context
            context.set_storage_location(storage_filename)
            context.complete()
            
            logger.info(f"Backup completed successfully: {storage_filename}")
            return True
            
        except Exception as e:
            error_msg = f"Backup failed with exception: {str(e)}"
            logger.error(error_msg, exc_info=True)
            context.fail(error_msg)
            return False
    
    def _compress_backup(self, dump_file: Path, context: BackupContext) -> Optional[Path]:
        """
        Compress the backup file.
        
        Args:
            dump_file: Path to the dump file
            context: BackupContext with compression settings
            
        Returns:
            Path to compressed file or None if compression failed
        """
        try:
            compression_method = context.backup_config.compression
            compressed_file = dump_file.parent / f"{dump_file.name}.{compression_method[:2]}"
            
            logger.info(f"Compressing with {compression_method}: {dump_file}")
            
            success = compress_file(
                str(dump_file),
                str(compressed_file),
                method=compression_method
            )
            
            if success:
                return compressed_file
            else:
                logger.warning("Compression failed, will upload uncompressed file")
                return None
                
        except Exception as e:
            logger.warning(f"Compression failed: {e}, will upload uncompressed file")
            return None


class BackupStrategyFactory:
    """Factory for creating backup strategies."""
    
    _strategies = {
        "full": FullBackupStrategy,
    }
    
    @classmethod
    def create(cls, strategy_name: str) -> BackupStrategy:
        """
        Create a backup strategy by name.
        
        Args:
            strategy_name: Name of the strategy (case-insensitive)
            
        Returns:
            BackupStrategy instance
            
        Raises:
            ValueError: If strategy name is unknown
        """
        if not strategy_name:
            raise ValueError("Strategy name cannot be empty or None")
        
        strategy_name_lower = strategy_name.lower()
        
        if strategy_name_lower not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown backup strategy: {strategy_name}. "
                f"Available strategies: {available}"
            )
        
        strategy_class = cls._strategies[strategy_name_lower]
        return strategy_class()
    
    @classmethod
    def get_available_strategies(cls) -> list:
        """Get list of available strategy names."""
        return list(cls._strategies.keys())
    
    @classmethod
    def is_available(cls, strategy_name: str) -> bool:
        """Check if a strategy is available."""
        if not strategy_name:
            return False
        return strategy_name.lower() in cls._strategies
