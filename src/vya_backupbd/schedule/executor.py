"""
Job executor for scheduled backup jobs.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Callable, Any

from vya_backupbd.schedule.config import ScheduleConfig
from vya_backupbd.schedule.manager import ScheduleManager
from vya_backupbd.backup.executor import BackupExecutor
from vya_backupbd.backup.context import BackupContext

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """Wrapper for scheduled job state."""
    
    schedule: ScheduleConfig
    is_running: bool = False
    last_run_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def mark_running(self) -> None:
        """Mark job as currently running."""
        self.is_running = True
        self.last_run_time = datetime.now()
    
    def mark_completed(self) -> None:
        """Mark job as successfully completed."""
        self.is_running = False
        self.last_success_time = datetime.now()
        self.last_error = None
    
    def mark_failed(self, error: str) -> None:
        """Mark job as failed."""
        self.is_running = False
        self.last_error = error


class JobExecutor:
    """
    Executor for scheduled backup jobs.
    
    Integrates schedule management with backup execution.
    """
    
    def __init__(
        self,
        schedule_manager: Optional[ScheduleManager] = None,
        config_provider: Optional[Callable[[str], Dict[str, Any]]] = None
    ):
        """
        Initialize job executor.
        
        Args:
            schedule_manager: Schedule manager instance
            config_provider: Function to get configs for database ID
        """
        self.schedule_manager = schedule_manager or ScheduleManager()
        self.config_provider = config_provider
        
        # Callbacks
        self.on_job_start: Optional[Callable[[ScheduleConfig], None]] = None
        self.on_job_success: Optional[Callable[[ScheduleConfig, BackupContext], None]] = None
        self.on_job_failure: Optional[Callable[[ScheduleConfig, str], None]] = None
    
    def execute_job(self, schedule: ScheduleConfig) -> bool:
        """
        Execute a scheduled backup job.
        
        Args:
            schedule: Schedule configuration
            
        Returns:
            True if backup successful, False otherwise
        """
        logger.info(f"Executing scheduled job: {schedule.name}")
        
        # Notify start
        if self.on_job_start:
            try:
                self.on_job_start(schedule)
            except Exception as e:
                logger.warning(f"Job start callback failed: {e}")
        
        # Get configurations
        if not self.config_provider:
            logger.error("No config provider configured")
            if self.on_job_failure:
                self.on_job_failure(schedule, "No config provider")
            return False
        
        try:
            configs = self.config_provider(schedule.database_id)
            database_config = configs.get("database")
            storage_config = configs.get("storage")
            backup_config = configs.get("backup")
            
            if not database_config or not storage_config or not backup_config:
                logger.error(f"Missing configuration for database: {schedule.database_id}")
                if self.on_job_failure:
                    self.on_job_failure(schedule, "Missing configuration")
                return False
            
            # Apply schedule-specific overrides
            if schedule.compression:
                backup_config.compression = schedule.compression
            if schedule.retention_days:
                backup_config.retention_days = schedule.retention_days
            if schedule.storage_type:
                storage_config.type = schedule.storage_type
            
            # Create backup context
            context = BackupContext(
                database_config=database_config,
                storage_config=storage_config,
                backup_config=backup_config
            )
            
            # Execute backup
            executor = BackupExecutor(
                strategy_name="full",
                max_retries=3,
                retry_delay=60.0
            )
            
            success = executor.execute(context)
            
            if success:
                logger.info(f"Job {schedule.name} completed successfully")
                if self.on_job_success:
                    try:
                        self.on_job_success(schedule, context)
                    except Exception as e:
                        logger.warning(f"Job success callback failed: {e}")
                return True
            else:
                error_msg = context.error_message or "Backup failed"
                logger.error(f"Job {schedule.name} failed: {error_msg}")
                if self.on_job_failure:
                    try:
                        self.on_job_failure(schedule, error_msg)
                    except Exception as e:
                        logger.warning(f"Job failure callback failed: {e}")
                return False
                
        except Exception as e:
            error_msg = f"Job execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if self.on_job_failure:
                try:
                    self.on_job_failure(schedule, error_msg)
                except Exception as cb_error:
                    logger.warning(f"Job failure callback failed: {cb_error}")
            return False
    
    def execute_jobs(self, schedules: list[ScheduleConfig]) -> Dict[str, bool]:
        """
        Execute multiple scheduled jobs.
        
        Args:
            schedules: List of schedule configurations
            
        Returns:
            Dictionary mapping schedule names to success status
        """
        results = {}
        
        for schedule in schedules:
            try:
                success = self.execute_job(schedule)
                results[schedule.name] = success
            except Exception as e:
                logger.error(f"Failed to execute job {schedule.name}: {e}")
                results[schedule.name] = False
        
        return results
    
    def execute_due_jobs(self, current_time: Optional[datetime] = None) -> Dict[str, bool]:
        """
        Execute all jobs that are currently due.
        
        Args:
            current_time: Time to check (default: now)
            
        Returns:
            Dictionary mapping schedule names to success status
        """
        due_schedules = self.schedule_manager.get_due_schedules(current_time)
        
        if not due_schedules:
            logger.info("No jobs are due at this time")
            return {}
        
        logger.info(f"Found {len(due_schedules)} due jobs")
        return self.execute_jobs(due_schedules)
