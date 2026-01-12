"""
Metrics collection system (phase9.2).

Collects backup/restore metrics and exports them in Prometheus format.
Focuses on operational metrics for monitoring backup/restore operations.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


class MetricType(str, Enum):
    """Metric type enumeration."""

    BACKUP = "backup"
    RESTORE = "restore"
    SCHEDULE = "schedule"
    STORAGE = "storage"


@dataclass
class BackupMetrics:
    """Backup operation metrics."""

    instance_name: str
    database_name: str
    duration_seconds: float
    backup_size_bytes: int
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instance_name": self.instance_name,
            "database_name": self.database_name,
            "duration_seconds": self.duration_seconds,
            "backup_size_bytes": self.backup_size_bytes,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
        }


@dataclass
class RestoreMetrics:
    """Restore operation metrics."""

    instance_name: str
    database_name: str
    duration_seconds: float
    restore_size_bytes: int
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instance_name": self.instance_name,
            "database_name": self.database_name,
            "duration_seconds": self.duration_seconds,
            "restore_size_bytes": self.restore_size_bytes,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
        }


@dataclass
class ScheduleMetrics:
    """Schedule execution metrics."""

    schedule_name: str
    last_run_timestamp: datetime
    next_run_timestamp: datetime
    execution_delay_seconds: float
    last_run_success: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schedule_name": self.schedule_name,
            "last_run_timestamp": self.last_run_timestamp.isoformat(),
            "next_run_timestamp": self.next_run_timestamp.isoformat(),
            "execution_delay_seconds": self.execution_delay_seconds,
            "last_run_success": self.last_run_success,
        }


@dataclass
class StorageMetrics:
    """Storage backend metrics."""

    storage_backend: str  # "s3", "filesystem", etc.
    bucket_name: str
    total_backups: int
    total_size_bytes: int
    oldest_backup_age_days: int
    newest_backup_age_days: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "storage_backend": self.storage_backend,
            "bucket_name": self.bucket_name,
            "total_backups": self.total_backups,
            "total_size_bytes": self.total_size_bytes,
            "oldest_backup_age_days": self.oldest_backup_age_days,
            "newest_backup_age_days": self.newest_backup_age_days,
        }


class MetricsCollector:
    """
    Collect and export metrics in Prometheus format.

    Responsibilities:
    - Record backup/restore operations
    - Track schedule execution
    - Monitor storage usage
    - Export metrics in Prometheus format for scraping
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._backup_metrics: List[BackupMetrics] = []
        self._restore_metrics: List[RestoreMetrics] = []
        self._schedule_metrics: Dict[str, ScheduleMetrics] = {}
        self._storage_metrics: Optional[StorageMetrics] = None

    def record_backup(
        self,
        instance_name: str,
        database_name: str,
        duration_seconds: float,
        backup_size_bytes: int,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record backup operation metrics.

        Args:
            instance_name: Database instance name
            database_name: Database name
            duration_seconds: Backup duration
            backup_size_bytes: Backup file size
            success: Whether backup succeeded
            error_message: Error message if failed
        """
        metrics = BackupMetrics(
            instance_name=instance_name,
            database_name=database_name,
            duration_seconds=duration_seconds,
            backup_size_bytes=backup_size_bytes,
            success=success,
            timestamp=datetime.now(),
            error_message=error_message,
        )
        self._backup_metrics.append(metrics)

    def record_restore(
        self,
        instance_name: str,
        database_name: str,
        duration_seconds: float,
        restore_size_bytes: int,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record restore operation metrics.

        Args:
            instance_name: Database instance name
            database_name: Database name
            duration_seconds: Restore duration
            restore_size_bytes: Restored file size
            success: Whether restore succeeded
            error_message: Error message if failed
        """
        metrics = RestoreMetrics(
            instance_name=instance_name,
            database_name=database_name,
            duration_seconds=duration_seconds,
            restore_size_bytes=restore_size_bytes,
            success=success,
            timestamp=datetime.now(),
            error_message=error_message,
        )
        self._restore_metrics.append(metrics)

    def record_schedule_execution(
        self,
        schedule_name: str,
        last_run_timestamp: datetime,
        next_run_timestamp: datetime,
        execution_delay_seconds: float,
        last_run_success: bool,
    ) -> None:
        """
        Record schedule execution metrics.

        Args:
            schedule_name: Schedule name
            last_run_timestamp: When schedule last ran
            next_run_timestamp: When schedule will run next
            execution_delay_seconds: Delay from expected time
            last_run_success: Whether last run succeeded
        """
        metrics = ScheduleMetrics(
            schedule_name=schedule_name,
            last_run_timestamp=last_run_timestamp,
            next_run_timestamp=next_run_timestamp,
            execution_delay_seconds=execution_delay_seconds,
            last_run_success=last_run_success,
        )
        self._schedule_metrics[schedule_name] = metrics

    def record_storage_metrics(
        self,
        storage_backend: str,
        bucket_name: str,
        total_backups: int,
        total_size_bytes: int,
        oldest_backup_age_days: int,
        newest_backup_age_days: int,
    ) -> None:
        """
        Record storage metrics.

        Args:
            storage_backend: Storage type (s3, filesystem)
            bucket_name: Bucket or directory name
            total_backups: Number of backups
            total_size_bytes: Total storage used
            oldest_backup_age_days: Age of oldest backup
            newest_backup_age_days: Age of newest backup
        """
        self._storage_metrics = StorageMetrics(
            storage_backend=storage_backend,
            bucket_name=bucket_name,
            total_backups=total_backups,
            total_size_bytes=total_size_bytes,
            oldest_backup_age_days=oldest_backup_age_days,
            newest_backup_age_days=newest_backup_age_days,
        )

    def get_backup_metrics(self) -> List[BackupMetrics]:
        """Get all backup metrics."""
        return self._backup_metrics.copy()

    def get_restore_metrics(self) -> List[RestoreMetrics]:
        """Get all restore metrics."""
        return self._restore_metrics.copy()

    def get_schedule_metrics(self) -> List[ScheduleMetrics]:
        """Get all schedule metrics."""
        return list(self._schedule_metrics.values())

    def get_storage_metrics(self) -> Optional[StorageMetrics]:
        """Get storage metrics."""
        return self._storage_metrics

    def get_metrics_by_type(self, metric_type: MetricType) -> List[Any]:
        """
        Get metrics by type.

        Args:
            metric_type: Type of metrics to retrieve

        Returns:
            List of metrics of specified type
        """
        if metric_type == MetricType.BACKUP:
            return self.get_backup_metrics()
        elif metric_type == MetricType.RESTORE:
            return self.get_restore_metrics()
        elif metric_type == MetricType.SCHEDULE:
            return self.get_schedule_metrics()
        elif metric_type == MetricType.STORAGE:
            storage = self.get_storage_metrics()
            return [storage] if storage else []
        return []

    def get_metrics_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[Any]:
        """
        Get metrics within time range.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of metrics within time range
        """
        metrics = []

        # Backup metrics
        for metric in self._backup_metrics:
            if start_time <= metric.timestamp <= end_time:
                metrics.append(metric)

        # Restore metrics
        for metric in self._restore_metrics:
            if start_time <= metric.timestamp <= end_time:
                metrics.append(metric)

        return metrics

    def to_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        # Backup metrics
        if self._backup_metrics:
            lines.append("# HELP vya_backup_duration_seconds Backup duration in seconds")
            lines.append("# TYPE vya_backup_duration_seconds gauge")
            for metric in self._backup_metrics:
                lines.append(
                    f'vya_backup_duration_seconds{{instance="{metric.instance_name}",'
                    f'database="{metric.database_name}"}} {metric.duration_seconds}'
                )

            lines.append("# HELP vya_backup_size_bytes Backup size in bytes")
            lines.append("# TYPE vya_backup_size_bytes gauge")
            for metric in self._backup_metrics:
                lines.append(
                    f'vya_backup_size_bytes{{instance="{metric.instance_name}",'
                    f'database="{metric.database_name}"}} {metric.backup_size_bytes}'
                )

            # Count success/failure
            success_count = sum(1 for m in self._backup_metrics if m.success)
            failure_count = len(self._backup_metrics) - success_count

            lines.append("# HELP vya_backup_total Total number of backups")
            lines.append("# TYPE vya_backup_total counter")
            lines.append(f'vya_backup_total{{success="true"}} {success_count}')
            lines.append(f'vya_backup_total{{success="false"}} {failure_count}')

        # Restore metrics
        if self._restore_metrics:
            lines.append(
                "# HELP vya_restore_duration_seconds Restore duration in seconds"
            )
            lines.append("# TYPE vya_restore_duration_seconds gauge")
            for metric in self._restore_metrics:
                lines.append(
                    f'vya_restore_duration_seconds{{instance="{metric.instance_name}",'
                    f'database="{metric.database_name}"}} {metric.duration_seconds}'
                )

            lines.append("# HELP vya_restore_size_bytes Restore size in bytes")
            lines.append("# TYPE vya_restore_size_bytes gauge")
            for metric in self._restore_metrics:
                lines.append(
                    f'vya_restore_size_bytes{{instance="{metric.instance_name}",'
                    f'database="{metric.database_name}"}} {metric.restore_size_bytes}'
                )

            # Count success/failure
            success_count = sum(1 for m in self._restore_metrics if m.success)
            failure_count = len(self._restore_metrics) - success_count

            lines.append("# HELP vya_restore_total Total number of restores")
            lines.append("# TYPE vya_restore_total counter")
            lines.append(f'vya_restore_total{{success="true"}} {success_count}')
            lines.append(f'vya_restore_total{{success="false"}} {failure_count}')

        # Schedule metrics
        if self._schedule_metrics:
            lines.append(
                "# HELP vya_schedule_last_run_timestamp Last schedule run timestamp"
            )
            lines.append("# TYPE vya_schedule_last_run_timestamp gauge")
            for metric in self._schedule_metrics.values():
                lines.append(
                    f'vya_schedule_last_run_timestamp{{schedule="{metric.schedule_name}"}} '
                    f"{metric.last_run_timestamp.timestamp()}"
                )

            lines.append(
                "# HELP vya_schedule_execution_delay_seconds Schedule execution delay"
            )
            lines.append("# TYPE vya_schedule_execution_delay_seconds gauge")
            for metric in self._schedule_metrics.values():
                lines.append(
                    f'vya_schedule_execution_delay_seconds{{schedule="{metric.schedule_name}"}} '
                    f"{metric.execution_delay_seconds}"
                )

        # Storage metrics
        if self._storage_metrics:
            metric = self._storage_metrics
            lines.append("# HELP vya_storage_total_backups Total number of backups in storage")
            lines.append("# TYPE vya_storage_total_backups gauge")
            lines.append(
                f'vya_storage_total_backups{{backend="{metric.storage_backend}",'
                f'bucket="{metric.bucket_name}"}} {metric.total_backups}'
            )

            lines.append("# HELP vya_storage_size_bytes Total storage size in bytes")
            lines.append("# TYPE vya_storage_size_bytes gauge")
            lines.append(
                f'vya_storage_size_bytes{{backend="{metric.storage_backend}",'
                f'bucket="{metric.bucket_name}"}} {metric.total_size_bytes}'
            )

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all metrics."""
        self._backup_metrics.clear()
        self._restore_metrics.clear()
        self._schedule_metrics.clear()
        self._storage_metrics = None
