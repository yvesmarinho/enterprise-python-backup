"""
Unit tests for backup.executor module.

Tests the BackupExecutor class that orchestrates the entire backup process.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call

from vya_backupbd.backup.executor import BackupExecutor
from vya_backupbd.backup.context import BackupContext
from vya_backupbd.config.models import DatabaseConfig, StorageConfig, BackupConfig


class TestBackupExecutorCreation:
    """Test BackupExecutor initialization."""

    def test_create_executor_default(self):
        """Test creating executor with default settings."""
        executor = BackupExecutor()
        assert executor is not None

    def test_create_executor_with_strategy(self):
        """Test creating executor with specific strategy."""
        executor = BackupExecutor(strategy_name="full")
        assert executor is not None

    def test_create_executor_with_callback(self):
        """Test creating executor with progress callback."""
        callback = Mock()
        executor = BackupExecutor(progress_callback=callback)
        assert executor is not None


class TestBackupExecutorExecution:
    """Test BackupExecutor backup execution."""

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_backup_success(self, mock_factory):
        """Test successful backup execution."""
        # Setup strategy mock
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        executor = BackupExecutor()
        context = self._create_context()

        result = executor.execute(context)

        assert result is True
        assert context.status == "completed"
        strategy.execute.assert_called_once_with(context)

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_backup_failure(self, mock_factory):
        """Test backup execution failure."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        executor = BackupExecutor()
        context = self._create_context()

        result = executor.execute(context)

        assert result is False
        assert context.status == "failed"

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_sets_context_times(self, mock_factory):
        """Test that execution sets start and end times."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        executor = BackupExecutor()
        context = self._create_context()

        executor.execute(context)

        assert context.start_time is not None
        assert context.end_time is not None
        assert context.get_duration() is not None

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_with_progress_callback(self, mock_factory):
        """Test that progress callbacks are called."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        callback = Mock()
        executor = BackupExecutor(progress_callback=callback)
        context = self._create_context()

        executor.execute(context)

        # Should be called at least for start and complete
        assert callback.call_count >= 2
        
        # Check for "started" and "completed" in calls
        call_messages = [str(call[0]) for call in callback.call_args_list]
        has_started = any("start" in msg.lower() for msg in call_messages)
        has_completed = any("complet" in msg.lower() for msg in call_messages)
        
        assert has_started
        assert has_completed

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_with_exception_handling(self, mock_factory):
        """Test that exceptions are caught and handled."""
        strategy = MagicMock()
        strategy.execute.side_effect = Exception("Unexpected error")
        mock_factory.create.return_value = strategy

        executor = BackupExecutor()
        context = self._create_context()

        result = executor.execute(context)

        assert result is False
        assert context.status == "failed"
        assert context.error_message is not None

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_uses_specified_strategy(self, mock_factory):
        """Test that executor uses the specified strategy."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(strategy_name="full")
        context = self._create_context()

        executor.execute(context)

        mock_factory.create.assert_called_once_with("full")

    def _create_context(self):
        """Helper to create a backup context."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)

        return BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )


class TestBackupExecutorValidation:
    """Test BackupExecutor validation."""

    def test_validate_context_valid(self):
        """Test validation passes for valid context."""
        executor = BackupExecutor()
        context = self._create_context()

        # Should not raise any exception
        result = executor.validate(context)
        assert result is True

    def test_validate_context_missing_database(self):
        """Test validation fails without database config."""
        executor = BackupExecutor()
        
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)
        
        context = BackupContext(
            database_config=None,
            storage_config=storage_config,
            backup_config=backup_config
        )

        result = executor.validate(context)
        assert result is False

    def test_validate_context_missing_storage(self):
        """Test validation fails without storage config."""
        executor = BackupExecutor()
        
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        backup_config = BackupConfig(retention_days=7)
        
        context = BackupContext(
            database_config=db_config,
            storage_config=None,
            backup_config=backup_config
        )

        result = executor.validate(context)
        assert result is False

    def test_validate_context_missing_backup_config(self):
        """Test validation fails without backup config."""
        executor = BackupExecutor()
        
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        
        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=None
        )

        result = executor.validate(context)
        assert result is False

    def _create_context(self):
        """Helper to create a valid backup context."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)

        return BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )


class TestBackupExecutorRetry:
    """Test BackupExecutor retry logic."""

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_with_retry_success_first_attempt(self, mock_factory):
        """Test retry logic when first attempt succeeds."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(max_retries=3)
        context = self._create_context()

        result = executor.execute(context)

        assert result is True
        assert strategy.execute.call_count == 1  # Only called once

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_with_retry_success_second_attempt(self, mock_factory):
        """Test retry logic succeeds on second attempt."""
        strategy = MagicMock()
        strategy.execute.side_effect = [False, True]  # Fail first, succeed second
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(max_retries=3)
        context = self._create_context()

        result = executor.execute(context)

        assert result is True
        assert strategy.execute.call_count == 2

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_with_retry_all_attempts_fail(self, mock_factory):
        """Test retry logic when all attempts fail."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(max_retries=3)
        context = self._create_context()

        result = executor.execute(context)

        assert result is False
        assert strategy.execute.call_count == 3  # Retried 3 times

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    @patch('time.sleep')
    def test_execute_retry_delays(self, mock_sleep, mock_factory):
        """Test that retry includes delay between attempts."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(max_retries=3, retry_delay=1.0)
        context = self._create_context()

        executor.execute(context)

        # Should sleep between retries (3 attempts = 2 sleeps)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(1.0)

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    def test_execute_no_retry_when_disabled(self, mock_factory):
        """Test that retry can be disabled."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(max_retries=0)  # Disable retry
        context = self._create_context()

        result = executor.execute(context)

        assert result is False
        assert strategy.execute.call_count == 1  # No retries

    def _create_context(self):
        """Helper to create a backup context."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)

        return BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )


class TestBackupExecutorCleanup:
    """Test BackupExecutor cleanup after backup."""

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    @patch('pathlib.Path.unlink')
    def test_cleanup_temp_files_on_success(self, mock_unlink, mock_factory):
        """Test that temporary files are cleaned up after success."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(cleanup_temp=True)
        context = self._create_context()
        context.set_backup_file(Path("/tmp/backup.sql"))

        executor.execute(context)

        # Temp file should be deleted after upload
        mock_unlink.assert_called_once()

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    @patch('pathlib.Path.unlink')
    def test_cleanup_temp_files_on_failure(self, mock_unlink, mock_factory):
        """Test that temporary files are cleaned up even on failure."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(cleanup_temp=True)
        context = self._create_context()
        context.set_backup_file(Path("/tmp/backup.sql"))

        executor.execute(context)

        # Temp file should be deleted even on failure
        mock_unlink.assert_called_once()

    @patch('vya_backupbd.backup.executor.BackupStrategyFactory')
    @patch('pathlib.Path.unlink')
    def test_no_cleanup_when_disabled(self, mock_unlink, mock_factory):
        """Test that cleanup can be disabled."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        executor = BackupExecutor(cleanup_temp=False)
        context = self._create_context()
        context.set_backup_file(Path("/tmp/backup.sql"))

        executor.execute(context)

        # Temp file should NOT be deleted
        mock_unlink.assert_not_called()

    def _create_context(self):
        """Helper to create a backup context."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)

        return BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )
