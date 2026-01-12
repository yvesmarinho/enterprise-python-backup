"""
BackupExecutor - orchestrates the entire backup process.

Handles:
- Validation
- Strategy execution
- Retry logic
- Progress callbacks
- Cleanup
"""

import logging
import time
from pathlib import Path
from typing import Optional, Callable

from vya_backupbd.backup.context import BackupContext
from vya_backupbd.backup.strategy import BackupStrategyFactory
from vya_backupbd.monitoring.metrics import MetricsCollector
from vya_backupbd.monitoring.alerts import AlertManager
from vya_backupbd.monitoring.notifications import NotificationManager, NotificationType

logger = logging.getLogger(__name__)


class BackupExecutor:
    """
    Orchestrates the complete backup process.
    
    Responsibilities:
    - Validate backup configuration
    - Execute backup strategy
    - Handle retries on failure
    - Track progress with callbacks
    - Clean up temporary files
    """
    
    def __init__(
        self,
        strategy_name: str = "full",
        max_retries: int = 0,
        retry_delay: float = 5.0,
        progress_callback: Optional[Callable] = None,
        cleanup_temp: bool = True,
        metrics_collector: Optional[MetricsCollector] = None,
        alert_manager: Optional[AlertManager] = None,
        notification_manager: Optional[NotificationManager] = None
    ):
        """
        Initialize BackupExecutor.
        
        Args:
            strategy_name: Name of backup strategy to use
            max_retries: Maximum number of retry attempts on failure
            retry_delay: Delay in seconds between retries
            progress_callback: Optional callback for progress updates
            cleanup_temp: Whether to cleanup temporary files after backup
            metrics_collector: Optional MetricsCollector for recording metrics
            alert_manager: Optional AlertManager for evaluating alerts
            notification_manager: Optional NotificationManager for sending notifications
        """
        self.strategy_name = strategy_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.progress_callback = progress_callback
        self.cleanup_temp = cleanup_temp
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        self.notification_manager = notification_manager
    
    def execute(self, context: BackupContext) -> bool:
        """
        Execute the backup process.
        
        Args:
            context: BackupContext with configuration
            
        Returns:
            True if backup succeeded, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate(context):
                logger.error("Backup configuration validation failed")
                context.fail("Invalid backup configuration")
                return False
            
            # Notify start
            context.start()
            self._notify_progress("Backup started", context)
            
            # Execute with retries
            # max_retries is the TOTAL number of attempts (not additional retries)
            attempts = max(1, self.max_retries) if self.max_retries > 0 else 1
            
            for attempt in range(1, attempts + 1):
                if attempt > 1:
                    logger.info(f"Retry attempt {attempt}/{attempts}")
                    self._notify_progress(f"Retrying backup (attempt {attempt}/{attempts})", context)
                    time.sleep(self.retry_delay)
                
                try:
                    # Create and execute strategy
                    strategy = BackupStrategyFactory.create(self.strategy_name)
                    success = strategy.execute(context)
                    
                    if success:
                        # Ensure context is marked as completed
                        if context.status != "completed":
                            context.complete()
                        
                        self._notify_progress("Backup completed successfully", context)
                        
                        # Record metrics
                        self._record_backup_metrics(context, success=True)
                        
                        # Evaluate alerts
                        self._evaluate_alerts(context)
                        
                        # Send success notification
                        self._send_notification(context, success=True)
                        
                        # Cleanup if configured
                        if self.cleanup_temp and context.backup_file:
                            self._cleanup_temp_files(context)
                        
                        return True
                    
                except Exception as e:
                    logger.error(f"Strategy execution failed: {e}", exc_info=True)
                    context.fail(f"Backup failed: {str(e)}")
                
                # If this wasn't the last attempt, continue to retry
                if attempt < attempts:
                    logger.warning(f"Backup attempt {attempt} failed, will retry")
            
            # All attempts failed
            logger.error(f"Backup failed after {attempts} attempts")
            context.fail(f"Backup failed after {attempts} attempts")
            self._notify_progress("Backup failed", context)
            
            # Record metrics
            self._record_backup_metrics(context, success=False)
            
            # Evaluate alerts
            self._evaluate_alerts(context)
            
            # Send failure notification
            self._send_notification(context, success=False)
            
            # Cleanup even on failure
            if self.cleanup_temp and context.backup_file:
                self._cleanup_temp_files(context)
            
            return False
            
        except Exception as e:
            error_msg = f"Backup executor failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            context.fail(error_msg)
            self._notify_progress(f"Backup failed: {str(e)}", context)
            
            # Record metrics and notify on exception
            self._record_backup_metrics(context, success=False)
            self._send_notification(context, success=False)
            
            return False
    
    def validate(self, context: BackupContext) -> bool:
        """
        Validate backup context configuration.
        
        Args:
            context: BackupContext to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not context.database_config:
            logger.error("Missing database configuration")
            return False
        
        if not context.storage_config:
            logger.error("Missing storage configuration")
            return False
        
        if not context.backup_config:
            logger.error("Missing backup configuration")
            return False
        
        return True
    
    def _notify_progress(self, message: str, context: Optional[BackupContext] = None) -> None:
        """
        Notify progress through callback if configured.
        
        Args:
            message: Progress message
            context: Optional BackupContext
        """
        if self.progress_callback:
            try:
                self.progress_callback(message, context)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def _cleanup_temp_files(self, context: BackupContext) -> None:
        """
        Clean up temporary backup files.
        
        Args:
            context: BackupContext with file information
        """
        try:
            if context.backup_file:
                logger.info(f"Cleaning up temporary file: {context.backup_file}")
                # Try to unlink, but don't fail if file doesn't exist
                try:
                    context.backup_file.unlink(missing_ok=True)
                except (FileNotFoundError, AttributeError):
                    # File doesn't exist or missing_ok not supported, try without it
                    if context.backup_file.exists():
                        context.backup_file.unlink()
                
                # Also cleanup compressed file if exists
                if context.compressed_size:
                    compressed_patterns = [
                        f"{context.backup_file}.gz",
                        f"{context.backup_file}.bz2",
                    ]
                    for pattern in compressed_patterns:
                        compressed_file = Path(pattern)
                        if compressed_file.exists():
                            logger.info(f"Cleaning up compressed file: {compressed_file}")
                            compressed_file.unlink()
                
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary files: {e}")
    
    def _record_backup_metrics(self, context: BackupContext, success: bool) -> None:
        """
        Record backup metrics if metrics collector is configured.
        
        Args:
            context: BackupContext with operation data
            success: Whether backup succeeded
        """
        if not self.metrics_collector:
            return
        
        try:
            instance_name = context.database_config.host if context.database_config else "unknown"
            database_name = context.database_config.database if context.database_config else "unknown"
            duration = context.get_duration().total_seconds() if context.start_time else 0
            size = context.compressed_size or context.backup_size or 0
            error = context.error_message if not success else None
            
            self.metrics_collector.record_backup(
                instance_name=instance_name,
                database_name=database_name,
                duration_seconds=duration,
                backup_size_bytes=size,
                success=success,
                error_message=error
            )
            logger.debug(f"Recorded backup metrics: success={success}, duration={duration}s, size={size}")
        except Exception as e:
            logger.warning(f"Failed to record backup metrics: {e}")
    
    def _evaluate_alerts(self, context: BackupContext) -> None:
        """
        Evaluate alert rules against backup metrics.
        
        Args:
            context: BackupContext with operation data
        """
        if not self.alert_manager or not self.metrics_collector:
            return
        
        try:
            # Get recent backup metrics
            backup_metrics = self.metrics_collector.get_backup_metrics()
            
            # Evaluate alerts
            triggers = self.alert_manager.evaluate_metrics(backup_metrics)
            
            # Send alert notifications
            if triggers and self.notification_manager:
                for trigger in triggers:
                    self.notification_manager.send_alert_notification(trigger)
                    logger.info(f"Alert triggered: {trigger.rule_name} - {trigger.message}")
        except Exception as e:
            logger.warning(f"Failed to evaluate alerts: {e}")
    
    def _send_notification(self, context: BackupContext, success: bool) -> None:
        """
        Send notification about backup result.
        
        Args:
            context: BackupContext with operation data
            success: Whether backup succeeded
        """
        if not self.notification_manager:
            return
        
        try:
            notification_type = NotificationType.SUCCESS if success else NotificationType.FAILURE
            
            instance = context.database_config.host if context.database_config else "unknown"
            database = context.database_config.database if context.database_config else "unknown"
            
            if success:
                subject = f"Backup Success: {database}@{instance}"
                duration = context.get_duration().total_seconds() if context.start_time else 0
                size = context.compressed_size or context.backup_size or 0
                body = f"Backup completed successfully.\nDuration: {duration:.2f}s\nSize: {size} bytes"
            else:
                subject = f"Backup Failed: {database}@{instance}"
                body = f"Backup failed.\nError: {context.error_message or 'Unknown error'}"
            
            metadata = {
                "instance": instance,
                "database": database,
                "success": success,
                "duration": context.get_duration().total_seconds() if context.start_time else 0,
                "size": context.compressed_size or context.backup_size or 0,
                "error": context.error_message
            }
            
            self.notification_manager.send_notification(
                notification_type=notification_type,
                subject=subject,
                body=body,
                metadata=metadata
            )
            logger.debug(f"Sent {notification_type.value} notification for backup")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
