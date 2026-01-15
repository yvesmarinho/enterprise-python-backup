"""
Unit tests for metrics collection system (phase9.2).

Tests metrics collection, Prometheus format, and metric types.
"""

from datetime import datetime, timedelta
from pathlib import Path
import pytest
from python_backup.monitoring.metrics import (
    MetricsCollector,
    BackupMetrics,
    RestoreMetrics,
    ScheduleMetrics,
    StorageMetrics,
    MetricType,
)


class TestBackupMetrics:
    """Test backup metrics model."""

    def test_create_backup_metrics(self):
        """Test creating backup metrics."""
        metrics = BackupMetrics(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=120.5,
            backup_size_bytes=1024 * 1024 * 500,  # 500MB
            success=True,
            timestamp=datetime.now(),
        )

        assert metrics.instance_name == "prod-mysql-01"
        assert metrics.database_name == "mydb"
        assert metrics.duration_seconds == 120.5
        assert metrics.backup_size_bytes == 500 * 1024 * 1024
        assert metrics.success is True
        assert metrics.error_message is None

    def test_backup_metrics_with_error(self):
        """Test backup metrics with error."""
        metrics = BackupMetrics(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=10.0,
            backup_size_bytes=0,
            success=False,
            timestamp=datetime.now(),
            error_message="Connection timeout",
        )

        assert metrics.success is False
        assert metrics.error_message == "Connection timeout"
        assert metrics.backup_size_bytes == 0


class TestRestoreMetrics:
    """Test restore metrics model."""

    def test_create_restore_metrics(self):
        """Test creating restore metrics."""
        metrics = RestoreMetrics(
            instance_name="dev-postgres-01",
            database_name="testdb",
            duration_seconds=60.3,
            restore_size_bytes=1024 * 1024 * 250,  # 250MB
            success=True,
            timestamp=datetime.now(),
        )

        assert metrics.instance_name == "dev-postgres-01"
        assert metrics.database_name == "testdb"
        assert metrics.duration_seconds == 60.3
        assert metrics.restore_size_bytes == 250 * 1024 * 1024
        assert metrics.success is True

    def test_restore_metrics_with_error(self):
        """Test restore metrics with error."""
        metrics = RestoreMetrics(
            instance_name="dev-postgres-01",
            database_name="testdb",
            duration_seconds=5.0,
            restore_size_bytes=0,
            success=False,
            timestamp=datetime.now(),
            error_message="Invalid backup file",
        )

        assert metrics.success is False
        assert metrics.error_message == "Invalid backup file"


class TestScheduleMetrics:
    """Test schedule metrics model."""

    def test_create_schedule_metrics(self):
        """Test creating schedule metrics."""
        now = datetime.now()
        next_run = now + timedelta(hours=1)

        metrics = ScheduleMetrics(
            schedule_name="daily-backup",
            last_run_timestamp=now,
            next_run_timestamp=next_run,
            execution_delay_seconds=2.5,
            last_run_success=True,
        )

        assert metrics.schedule_name == "daily-backup"
        assert metrics.last_run_timestamp == now
        assert metrics.next_run_timestamp == next_run
        assert metrics.execution_delay_seconds == 2.5
        assert metrics.last_run_success is True

    def test_schedule_metrics_missed_execution(self):
        """Test schedule metrics with delayed execution."""
        now = datetime.now()
        next_run = now + timedelta(hours=1)

        metrics = ScheduleMetrics(
            schedule_name="hourly-backup",
            last_run_timestamp=now,
            next_run_timestamp=next_run,
            execution_delay_seconds=300.0,  # 5 minutes late
            last_run_success=False,
        )

        assert metrics.execution_delay_seconds == 300.0
        assert metrics.last_run_success is False


class TestStorageMetrics:
    """Test storage metrics model."""

    def test_create_storage_metrics(self):
        """Test creating storage metrics."""
        metrics = StorageMetrics(
            storage_backend="s3",
            bucket_name="my-backups",
            total_backups=150,
            total_size_bytes=1024 * 1024 * 1024 * 50,  # 50GB
            oldest_backup_age_days=90,
            newest_backup_age_days=0,
        )

        assert metrics.storage_backend == "s3"
        assert metrics.bucket_name == "my-backups"
        assert metrics.total_backups == 150
        assert metrics.total_size_bytes == 50 * 1024 * 1024 * 1024
        assert metrics.oldest_backup_age_days == 90
        assert metrics.newest_backup_age_days == 0


class TestMetricsCollector:
    """Test metrics collector."""

    @pytest.fixture
    def collector(self):
        """Create metrics collector."""
        return MetricsCollector()

    def test_record_backup_success(self, collector):
        """Test recording successful backup."""
        collector.record_backup(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=120.0,
            backup_size_bytes=1024 * 1024 * 500,
            success=True,
        )

        metrics = collector.get_backup_metrics()
        assert len(metrics) == 1
        assert metrics[0].instance_name == "prod-mysql-01"
        assert metrics[0].success is True

    def test_record_backup_failure(self, collector):
        """Test recording failed backup."""
        collector.record_backup(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=10.0,
            backup_size_bytes=0,
            success=False,
            error_message="Connection failed",
        )

        metrics = collector.get_backup_metrics()
        assert len(metrics) == 1
        assert metrics[0].success is False
        assert metrics[0].error_message == "Connection failed"

    def test_record_restore_success(self, collector):
        """Test recording successful restore."""
        collector.record_restore(
            instance_name="dev-postgres-01",
            database_name="testdb",
            duration_seconds=60.0,
            restore_size_bytes=1024 * 1024 * 250,
            success=True,
        )

        metrics = collector.get_restore_metrics()
        assert len(metrics) == 1
        assert metrics[0].instance_name == "dev-postgres-01"
        assert metrics[0].success is True

    def test_record_restore_failure(self, collector):
        """Test recording failed restore."""
        collector.record_restore(
            instance_name="dev-postgres-01",
            database_name="testdb",
            duration_seconds=5.0,
            restore_size_bytes=0,
            success=False,
            error_message="Invalid file format",
        )

        metrics = collector.get_restore_metrics()
        assert len(metrics) == 1
        assert metrics[0].success is False
        assert metrics[0].error_message == "Invalid file format"

    def test_get_prometheus_metrics(self, collector):
        """Test Prometheus metrics format."""
        # Record some metrics
        collector.record_backup(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=120.0,
            backup_size_bytes=1024 * 1024 * 500,
            success=True,
        )

        collector.record_restore(
            instance_name="dev-postgres-01",
            database_name="testdb",
            duration_seconds=60.0,
            restore_size_bytes=1024 * 1024 * 250,
            success=True,
        )

        # Get Prometheus format
        prometheus_output = collector.to_prometheus()

        # Check format
        assert "# HELP" in prometheus_output
        assert "# TYPE" in prometheus_output
        assert "vya_backup_duration_seconds" in prometheus_output
        assert "vya_backup_size_bytes" in prometheus_output
        assert "vya_restore_duration_seconds" in prometheus_output
        assert "vya_restore_size_bytes" in prometheus_output

    def test_backup_success_counter(self, collector):
        """Test backup success counter."""
        # Record multiple backups
        for i in range(5):
            collector.record_backup(
                instance_name="prod-mysql-01",
                database_name=f"db{i}",
                duration_seconds=100.0,
                backup_size_bytes=1024 * 1024,
                success=True,
            )

        # Record 2 failures
        for i in range(2):
            collector.record_backup(
                instance_name="prod-mysql-01",
                database_name=f"db{i}",
                duration_seconds=10.0,
                backup_size_bytes=0,
                success=False,
                error_message="Error",
            )

        prometheus_output = collector.to_prometheus()
        assert "vya_backup_total{success=\"true\"}" in prometheus_output or \
               "vya_backup_total{success=true}" in prometheus_output

    def test_clear_metrics(self, collector):
        """Test clearing metrics."""
        collector.record_backup(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=120.0,
            backup_size_bytes=1024 * 1024,
            success=True,
        )

        assert len(collector.get_backup_metrics()) == 1

        collector.clear()
        assert len(collector.get_backup_metrics()) == 0

    def test_get_metric_by_type(self, collector):
        """Test getting metrics by type."""
        collector.record_backup(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=120.0,
            backup_size_bytes=1024 * 1024,
            success=True,
        )

        backup_metrics = collector.get_metrics_by_type(MetricType.BACKUP)
        assert len(backup_metrics) == 1

        restore_metrics = collector.get_metrics_by_type(MetricType.RESTORE)
        assert len(restore_metrics) == 0

    def test_get_metrics_time_range(self, collector):
        """Test getting metrics within time range."""
        now = datetime.now()
        
        # Record metric from 1 hour ago
        collector.record_backup(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=120.0,
            backup_size_bytes=1024 * 1024,
            success=True,
        )
        
        # Manually adjust timestamp for testing
        if collector._backup_metrics:
            collector._backup_metrics[0].timestamp = now - timedelta(hours=1)
        
        # Get metrics from last 30 minutes (should be empty)
        recent_metrics = collector.get_metrics_time_range(
            start_time=now - timedelta(minutes=30),
            end_time=now,
        )
        assert len(recent_metrics) == 0
        
        # Get metrics from last 2 hours (should include the metric)
        all_metrics = collector.get_metrics_time_range(
            start_time=now - timedelta(hours=2),
            end_time=now,
        )
        assert len(all_metrics) == 1
