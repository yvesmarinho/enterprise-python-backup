"""
RestoreExecutor for orchestrating database restore operations.
"""

import logging
from time import sleep
from typing import Optional, Callable

from python_backup.restore.context import RestoreContext
from python_backup.restore.strategy import RestoreStrategyFactory
from python_backup.monitoring.metrics import MetricsCollector
from python_backup.monitoring.alerts import AlertManager
from python_backup.monitoring.notifications import NotificationManager, NotificationType

logger = logging.getLogger(__name__)


class RestoreExecutor:
    """
    Executor for orchestrating database restore operations.
    
    Handles validation, retry logic, progress reporting, and cleanup.
    """
    
    def __init__(
        self,
        strategy_name: str = "full",
        max_retries: int = 0,
        retry_delay: float = 5.0,
        progress_callback: Optional[Callable[[str, RestoreContext], None]] = None,
        cleanup_temp: bool = True,
        metrics_collector: Optional[MetricsCollector] = None,
        alert_manager: Optional[AlertManager] = None,
        notification_manager: Optional[NotificationManager] = None
    ):
        """
        Initialize RestoreExecutor.
        
        Args:
            strategy_name: Name of restore strategy to use
            max_retries: Maximum number of restore attempts (0 = no retries)
            retry_delay: Delay in seconds between retry attempts
            progress_callback: Optional callback for progress updates
            cleanup_temp: Whether to clean up temporary files after restore
            metrics_collector: Optional MetricsCollector for recording metrics
            alert_manager: Optional AlertManager for evaluating alerts
            notification_manager: Optional NotificationManager for sending notifications
            
        Raises:
            ValueError: If max_retries is negative
        """
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        
        self.strategy_name = strategy_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.progress_callback = progress_callback
        self.cleanup_temp = cleanup_temp
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        self.notification_manager = notification_manager
    
    def execute(self, context: RestoreContext) -> bool:
        """
        Execute the restore operation.
        
        Args:
            context: RestoreContext with configuration and state
            
        Returns:
            bool: True if restore successful, False otherwise
        """
        # Validate context
        if not self.validate(context):
            logger.error("Context validation failed")
            context.fail("Invalid restore context")
            return False
        
        # Start restore
        context.start()
        self._notify_progress("Starting restore operation", context)
        logger.info(f"Starting restore with strategy: {self.strategy_name}")
        
        # Retry loop
        attempts = self.max_retries if self.max_retries > 0 else 1
        
        for attempt in range(1, attempts + 1):
            if attempt > 1:
                logger.info(f"Retry attempt {attempt}/{attempts}")
                self._notify_progress(f"Retry attempt {attempt}/{attempts}", context)
                sleep(self.retry_delay)
            
            try:
                # Create strategy
                strategy = RestoreStrategyFactory.create(self.strategy_name)
                
                # Execute restore
                success = strategy.execute(context)
                
                if success:
                    # Ensure context is marked complete
                    if context.status != "completed":
                        context.complete()
                    
                    logger.info("Restore completed successfully")
                    self._notify_progress("Restore completed", context)
                    
                    # Record metrics
                    self._record_restore_metrics(context, success=True)
                    
                    # Evaluate alerts
                    self._evaluate_alerts(context)
                    
                    # Send success notification
                    self._send_notification(context, success=True)
                    
                    # Cleanup temp files
                    if self.cleanup_temp:
                        self._cleanup_temp_files(context)
                    
                    return True
                else:
                    logger.warning(f"Restore attempt {attempt} failed")
                    
            except Exception as e:
                logger.error(f"Restore attempt {attempt} raised exception: {e}", exc_info=True)
                context.fail(str(e))
        
        # All attempts failed
        logger.error(f"All {attempts} restore attempts failed")
        context.fail(f"Restore failed after {attempts} attempts")
        self._notify_progress("Restore failed", context)
        
        # Record metrics
        self._record_restore_metrics(context, success=False)
        
        # Evaluate alerts
        self._evaluate_alerts(context)
        
        # Send failure notification
        self._send_notification(context, success=False)
        
        # Cleanup temp files even on failure
        if self.cleanup_temp:
            self._cleanup_temp_files(context)
        
        return False
    
    def validate(self, context: RestoreContext) -> bool:
        """
        Validate restore context.
        
        Args:
            context: RestoreContext to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not context.database_config:
            logger.error("Missing database configuration")
            return False
        
        if not context.storage_config:
            logger.error("Missing storage configuration")
            return False
        
        if not context.backup_file:
            logger.error("Missing backup file path")
            return False
        
        return True
    
    def _notify_progress(self, message: str, context: RestoreContext) -> None:
        """
        Notify progress via callback.
        
        Args:
            message: Progress message
            context: Current restore context
        """
        if self.progress_callback:
            try:
                self.progress_callback(message, context)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def _cleanup_temp_files(self, context: RestoreContext) -> None:
        """
        Clean up temporary files created during restore.
        
        Args:
            context: RestoreContext with file references
        """
        try:
            # Clean up downloaded file
            if context.downloaded_file:
                try:
                    context.downloaded_file.unlink()
                    logger.info(f"Cleaned up downloaded file: {context.downloaded_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup downloaded file: {e}")
            
            # Clean up decompressed file
            if context.decompressed_file:
                try:
                    context.decompressed_file.unlink()
                    logger.info(f"Cleaned up decompressed file: {context.decompressed_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup decompressed file: {e}")
                    
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def _record_restore_metrics(self, context: RestoreContext, success: bool) -> None:
        """
        Record restore metrics if metrics collector is configured.
        
        Args:
            context: RestoreContext with operation data
            success: Whether restore succeeded
        """
        if not self.metrics_collector:
            return
        
        try:
            instance_name = context.database_config.host if context.database_config else "unknown"
            database_name = context.database_config.database if context.database_config else "unknown"
            duration = context.get_duration().total_seconds() if context.start_time else 0
            size = context.backup_file.stat().st_size if context.backup_file and context.backup_file.exists() else 0
            error = context.error_message if not success else None
            
            self.metrics_collector.record_restore(
                instance_name=instance_name,
                database_name=database_name,
                duration_seconds=duration,
                restore_size_bytes=size,
                success=success,
                error_message=error
            )
            logger.debug(f"Recorded restore metrics: success={success}, duration={duration}s, size={size}")
        except Exception as e:
            logger.warning(f"Failed to record restore metrics: {e}")
    
    def _evaluate_alerts(self, context: RestoreContext) -> None:
        """
        Evaluate alert rules against restore metrics.
        
        Args:
            context: RestoreContext with operation data
        """
        if not self.alert_manager or not self.metrics_collector:
            return
        
        try:
            # Get recent restore metrics
            restore_metrics = self.metrics_collector.get_restore_metrics()
            
            # Evaluate alerts
            triggers = self.alert_manager.evaluate_metrics(restore_metrics)
            
            # Send alert notifications
            if triggers and self.notification_manager:
                for trigger in triggers:
                    self.notification_manager.send_alert_notification(trigger)
                    logger.info(f"Alert triggered: {trigger.rule_name} - {trigger.message}")
        except Exception as e:
            logger.warning(f"Failed to evaluate alerts: {e}")
    
    def _send_notification(self, context: RestoreContext, success: bool) -> None:
        """
        Send notification about restore result.
        
        Args:
            context: RestoreContext with operation data
            success: Whether restore succeeded
        """
        if not self.notification_manager:
            return
        
        try:
            notification_type = NotificationType.SUCCESS if success else NotificationType.FAILURE
            
            instance = context.database_config.host if context.database_config else "unknown"
            database = context.database_config.database if context.database_config else "unknown"
            
            if success:
                subject = f"Restore Success: {database}@{instance}"
                duration = context.get_duration().total_seconds() if context.start_time else 0
                size = context.backup_file.stat().st_size if context.backup_file and context.backup_file.exists() else 0
                body = f"Restore completed successfully.\nDuration: {duration:.2f}s\nSize: {size} bytes"
            else:
                subject = f"Restore Failed: {database}@{instance}"
                body = f"Restore failed.\nError: {context.error_message or 'Unknown error'}"
            
            metadata = {
                "instance": instance,
                "database": database,
                "success": success,
                "duration": context.get_duration().total_seconds() if context.start_time else 0,
                "error": context.error_message
            }
            
            self.notification_manager.send_notification(
                notification_type=notification_type,
                subject=subject,
                body=body,
                metadata=metadata
            )
            logger.debug(f"Sent {notification_type.value} notification for restore")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
