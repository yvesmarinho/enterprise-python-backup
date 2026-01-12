"""
Unit tests for schedule.executor module.

Tests scheduled job execution and orchestration.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from vya_backupbd.schedule.executor import JobExecutor, ScheduledJob
from vya_backupbd.schedule.config import ScheduleConfig
from vya_backupbd.config.models import DatabaseConfig, StorageConfig, BackupConfig


class TestScheduledJob:
    """Test ScheduledJob wrapper."""

    def test_create_scheduled_job(self):
        """Test creating a scheduled job."""
        schedule = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        
        job = ScheduledJob(schedule)
        
        assert job.schedule == schedule
        assert job.is_running is False

    def test_job_mark_running(self):
        """Test marking job as running."""
        schedule = ScheduleConfig(
            name="test",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        job = ScheduledJob(schedule)
        
        job.mark_running()
        
        assert job.is_running is True
        assert job.last_run_time is not None

    def test_job_mark_completed(self):
        """Test marking job as completed."""
        schedule = ScheduleConfig(
            name="test",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        job = ScheduledJob(schedule)
        
        job.mark_running()
        job.mark_completed()
        
        assert job.is_running is False
        assert job.last_success_time is not None

    def test_job_mark_failed(self):
        """Test marking job as failed."""
        schedule = ScheduleConfig(
            name="test",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        job = ScheduledJob(schedule)
        
        job.mark_running()
        job.mark_failed("Error message")
        
        assert job.is_running is False
        assert job.last_error == "Error message"


class TestJobExecutorCreation:
    """Test JobExecutor initialization."""

    def test_create_executor(self):
        """Test creating job executor."""
        executor = JobExecutor()
        
        assert executor is not None

    @patch('vya_backupbd.schedule.executor.ScheduleManager')
    def test_executor_with_schedule_manager(self, mock_manager_class):
        """Test executor with injected schedule manager."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        
        executor = JobExecutor(schedule_manager=mock_manager)
        
        assert executor.schedule_manager == mock_manager

    def test_executor_with_config_provider(self):
        """Test executor with config provider function."""
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        
        executor = JobExecutor(config_provider=config_provider)
        
        assert executor.config_provider == config_provider


class TestJobExecutorExecution:
    """Test job execution logic."""

    @pytest.fixture
    def executor(self):
        """Create executor for testing."""
        return JobExecutor()

    @pytest.fixture
    def schedule(self):
        """Create test schedule."""
        return ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_execute_job_success(self, mock_backup_executor_class, executor, schedule):
        """Test successful job execution."""
        # Setup mock backup executor
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True
        mock_backup_executor_class.return_value = mock_executor
        
        # Mock config provider
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        executor.config_provider = config_provider
        
        result = executor.execute_job(schedule)
        
        assert result is True
        mock_executor.execute.assert_called_once()

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_execute_job_failure(self, mock_backup_executor_class, executor, schedule):
        """Test failed job execution."""
        mock_executor = MagicMock()
        mock_executor.execute.return_value = False
        mock_backup_executor_class.return_value = mock_executor
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        executor.config_provider = config_provider
        
        result = executor.execute_job(schedule)
        
        assert result is False

    def test_execute_job_missing_config(self, executor, schedule):
        """Test execution fails gracefully without config."""
        executor.config_provider = None
        
        result = executor.execute_job(schedule)
        
        assert result is False

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_execute_job_with_compression(self, mock_backup_executor_class, executor):
        """Test job execution with compression."""
        schedule = ScheduleConfig(
            name="compressed_backup",
            cron_expression="0 2 * * *",
            database_id="db1",
            compression="gzip"
        )
        
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True
        mock_backup_executor_class.return_value = mock_executor
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7, compression="gzip")
            }
        executor.config_provider = config_provider
        
        result = executor.execute_job(schedule)
        
        assert result is True

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_execute_job_with_custom_retention(self, mock_backup_executor_class, executor):
        """Test job execution with custom retention."""
        schedule = ScheduleConfig(
            name="retention_backup",
            cron_expression="0 2 * * *",
            database_id="db1",
            retention_days=30
        )
        
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True
        mock_backup_executor_class.return_value = mock_executor
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=30)
            }
        executor.config_provider = config_provider
        
        result = executor.execute_job(schedule)
        
        assert result is True


class TestJobExecutorCallbacks:
    """Test job execution callbacks."""

    @pytest.fixture
    def executor(self):
        """Create executor for testing."""
        return JobExecutor()

    @pytest.fixture
    def schedule(self):
        """Create test schedule."""
        return ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_on_job_start_callback(self, mock_backup_executor_class, executor, schedule):
        """Test job start callback is called."""
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True
        mock_backup_executor_class.return_value = mock_executor
        
        on_start = Mock()
        executor.on_job_start = on_start
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        executor.config_provider = config_provider
        
        executor.execute_job(schedule)
        
        on_start.assert_called_once_with(schedule)

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_on_job_success_callback(self, mock_backup_executor_class, executor, schedule):
        """Test job success callback is called."""
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True
        mock_backup_executor_class.return_value = mock_executor
        
        on_success = Mock()
        executor.on_job_success = on_success
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        executor.config_provider = config_provider
        
        executor.execute_job(schedule)
        
        on_success.assert_called_once()

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_on_job_failure_callback(self, mock_backup_executor_class, executor, schedule):
        """Test job failure callback is called."""
        mock_executor = MagicMock()
        mock_executor.execute.return_value = False
        mock_backup_executor_class.return_value = mock_executor
        
        on_failure = Mock()
        executor.on_job_failure = on_failure
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        executor.config_provider = config_provider
        
        executor.execute_job(schedule)
        
        on_failure.assert_called_once()


class TestJobExecutorBatchExecution:
    """Test executing multiple jobs."""

    @pytest.fixture
    def executor(self):
        """Create executor for testing."""
        return JobExecutor()

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_execute_multiple_jobs(self, mock_backup_executor_class, executor):
        """Test executing multiple jobs in batch."""
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True
        mock_backup_executor_class.return_value = mock_executor
        
        schedules = [
            ScheduleConfig(name="backup1", cron_expression="0 2 * * *", database_id="db1"),
            ScheduleConfig(name="backup2", cron_expression="0 2 * * *", database_id="db2"),
        ]
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        executor.config_provider = config_provider
        
        results = executor.execute_jobs(schedules)
        
        assert len(results) == 2
        assert all(results.values())

    @patch('vya_backupbd.schedule.executor.BackupExecutor')
    def test_execute_jobs_with_failures(self, mock_backup_executor_class, executor):
        """Test executing jobs with some failures."""
        mock_executor = MagicMock()
        # First succeeds, second fails
        mock_executor.execute.side_effect = [True, False]
        mock_backup_executor_class.return_value = mock_executor
        
        schedules = [
            ScheduleConfig(name="backup1", cron_expression="0 2 * * *", database_id="db1"),
            ScheduleConfig(name="backup2", cron_expression="0 2 * * *", database_id="db2"),
        ]
        
        def config_provider(db_id):
            return {
                "database": DatabaseConfig(type="postgresql", host="localhost", port=5432, database=db_id),
                "storage": StorageConfig(type="local", path="/backups"),
                "backup": BackupConfig(retention_days=7)
            }
        executor.config_provider = config_provider
        
        results = executor.execute_jobs(schedules)
        
        assert len(results) == 2
        assert results["backup1"] is True
        assert results["backup2"] is False

    def test_execute_empty_job_list(self, executor):
        """Test executing empty job list."""
        results = executor.execute_jobs([])
        
        assert results == {}


class TestJobExecutorRetention:
    """Test backup retention enforcement."""

    @pytest.fixture
    def executor(self):
        """Create executor for testing."""
        return JobExecutor()

    def test_executor_retention_placeholder(self, executor):
        """Placeholder test for retention integration."""
        # Retention policy will be applied through BackupExecutor
        # and storage cleanup - integration tested separately
        assert executor is not None
