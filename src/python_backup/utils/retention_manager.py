"""
Retention Manager for automated backup cleanup.

Manages backup file retention based on age policies, with support for
dry-run mode, detailed logging, and integration with BackupManager.
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from python_backup.utils.backup_manager import BackupManager, BackupMetadata

logger = logging.getLogger(__name__)


@dataclass
class RetentionStats:
    """Statistics from retention cleanup operation."""
    total_backups: int = 0
    kept_backups: int = 0
    deleted_backups: int = 0
    freed_space_bytes: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def freed_space_mb(self) -> float:
        """Get freed space in megabytes."""
        return self.freed_space_bytes / (1024 * 1024)
    
    @property
    def freed_space_gb(self) -> float:
        """Get freed space in gigabytes."""
        return self.freed_space_bytes / (1024 * 1024 * 1024)


class RetentionManager:
    """
    Manages retention policies and cleanup of old backups.
    
    Features:
    - Age-based retention (days)
    - Dry-run mode for safe testing
    - Detailed logging and statistics
    - Integration with BackupManager
    - Error handling and recovery
    """
    
    def __init__(self, backup_dir: Path, retention_days: int = 7):
        """
        Initialize retention manager.
        
        Args:
            backup_dir: Directory containing backup files
            retention_days: Number of days to keep backups (default: 7)
        """
        logger.debug(f"=== Função: __init__ (RetentionManager) ===")
        logger.debug(f"==> PARAM: backup_dir TYPE: {type(backup_dir)}, CONTENT: {backup_dir}")
        logger.debug(f"==> PARAM: retention_days TYPE: {type(retention_days)}, CONTENT: {retention_days}")
        
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.backup_manager = BackupManager(self.backup_dir)
        
        if not self.backup_dir.exists():
            logger.warning(f"Backup directory does not exist: {self.backup_dir}")
        
        logger.debug(f"=== Término Função: __init__ (RetentionManager) ===")
    
    def get_expired_backups(
        self,
        dbms_type: Optional[str] = None,
        database: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> List[BackupMetadata]:
        """
        Get list of backups that have expired based on retention policy.
        
        Args:
            dbms_type: Filter by database type (mysql, postgresql, files)
            database: Filter by database name
            reference_time: Time to use for age calculation (default: now)
            
        Returns:
            List of expired backup metadata objects
        """
        logger.debug(f"=== Função: get_expired_backups (RetentionManager) ===")
        logger.debug(f"==> PARAM: dbms_type={dbms_type}, database={database}")
        
        if reference_time is None:
            reference_time = datetime.now()
        
        cutoff_time = reference_time - timedelta(days=self.retention_days)
        logger.info(f"Retention cutoff: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} ({self.retention_days} days)")
        
        # Get all backups
        all_backups = self.backup_manager.list_backups(
            dbms_type=dbms_type,
            database=database
        )
        
        # Filter expired backups
        expired = []
        for backup in all_backups:
            if backup.timestamp < cutoff_time:
                age_days = (reference_time - backup.timestamp).days
                logger.debug(f"Expired: {backup.filename} (age: {age_days} days)")
                expired.append(backup)
        
        logger.info(f"Found {len(expired)} expired backups (out of {len(all_backups)} total)")
        logger.debug(f"=== Término Função: get_expired_backups (RetentionManager) ===")
        
        return expired
    
    def cleanup(
        self,
        dry_run: bool = False,
        dbms_type: Optional[str] = None,
        database: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> RetentionStats:
        """
        Perform retention cleanup operation.
        
        Args:
            dry_run: If True, only simulate deletion without removing files
            dbms_type: Filter by database type (mysql, postgresql, files)
            database: Filter by database name  
            reference_time: Time to use for age calculation (default: now)
            
        Returns:
            RetentionStats object with cleanup statistics
        """
        logger.debug(f"=== Função: cleanup (RetentionManager) ===")
        logger.info("=" * 80)
        logger.info(f"Starting retention cleanup (dry_run={dry_run})")
        logger.info(f"Retention policy: {self.retention_days} days")
        logger.info(f"Backup directory: {self.backup_dir}")
        
        stats = RetentionStats()
        
        try:
            # Get expired backups
            expired_backups = self.get_expired_backups(
                dbms_type=dbms_type,
                database=database,
                reference_time=reference_time
            )
            
            # Get all backups for statistics
            all_backups = self.backup_manager.list_backups(
                dbms_type=dbms_type,
                database=database
            )
            
            stats.total_backups = len(all_backups)
            stats.deleted_backups = len(expired_backups)
            stats.kept_backups = stats.total_backups - stats.deleted_backups
            
            if not expired_backups:
                logger.info("No expired backups found")
                logger.info("=" * 80)
                logger.debug(f"=== Término Função: cleanup (RetentionManager) ===")
                return stats
            
            # Delete expired backups
            for backup in expired_backups:
                try:
                    file_path = self.backup_dir / backup.filename
                    
                    if not file_path.exists():
                        logger.warning(f"File not found: {file_path}")
                        stats.errors.append(f"File not found: {backup.filename}")
                        continue
                    
                    file_size = file_path.stat().st_size
                    stats.freed_space_bytes += file_size
                    
                    if dry_run:
                        logger.info(f"[DRY-RUN] Would delete: {backup.filename} ({file_size / (1024*1024):.2f} MB)")
                    else:
                        file_path.unlink()
                        logger.info(f"Deleted: {backup.filename} ({file_size / (1024*1024):.2f} MB)")
                        
                except Exception as e:
                    error_msg = f"Error deleting {backup.filename}: {str(e)}"
                    logger.error(error_msg)
                    stats.errors.append(error_msg)
            
            # Log summary
            logger.info("=" * 80)
            logger.info("Retention cleanup completed")
            logger.info(f"Total backups: {stats.total_backups}")
            logger.info(f"Kept: {stats.kept_backups}")
            logger.info(f"Deleted: {stats.deleted_backups}")
            logger.info(f"Freed space: {stats.freed_space_mb:.2f} MB ({stats.freed_space_gb:.2f} GB)")
            if stats.errors:
                logger.warning(f"Errors: {len(stats.errors)}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Retention cleanup failed: {e}", exc_info=True)
            stats.errors.append(f"Cleanup failed: {str(e)}")
        
        logger.debug(f"=== Término Função: cleanup (RetentionManager) ===")
        return stats
    
    def get_retention_summary(
        self,
        dbms_type: Optional[str] = None,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of current backup retention status.
        
        Args:
            dbms_type: Filter by database type
            database: Filter by database name
            
        Returns:
            Dictionary with retention summary statistics
        """
        logger.debug(f"=== Função: get_retention_summary (RetentionManager) ===")
        
        all_backups = self.backup_manager.list_backups(
            dbms_type=dbms_type,
            database=database
        )
        
        expired_backups = self.get_expired_backups(
            dbms_type=dbms_type,
            database=database
        )
        
        # Calculate total sizes
        total_size = 0
        expired_size = 0
        
        for backup in all_backups:
            file_path = self.backup_dir / backup.filename
            if file_path.exists():
                size = file_path.stat().st_size
                total_size += size
                
                if backup in expired_backups:
                    expired_size += size
        
        # Get oldest and newest backup
        oldest = min(all_backups, key=lambda b: b.timestamp) if all_backups else None
        newest = max(all_backups, key=lambda b: b.timestamp) if all_backups else None
        
        summary = {
            'total_backups': len(all_backups),
            'active_backups': len(all_backups) - len(expired_backups),
            'expired_backups': len(expired_backups),
            'total_size_mb': total_size / (1024 * 1024),
            'expired_size_mb': expired_size / (1024 * 1024),
            'retention_days': self.retention_days,
            'oldest_backup': oldest.timestamp.strftime('%Y-%m-%d %H:%M:%S') if oldest else None,
            'newest_backup': newest.timestamp.strftime('%Y-%m-%d %H:%M:%S') if newest else None,
        }
        
        logger.debug(f"=== Término Função: get_retention_summary (RetentionManager) ===")
        return summary
