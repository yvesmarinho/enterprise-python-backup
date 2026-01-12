"""
Unit tests for restore.executor module.

Tests the RestoreExecutor orchestration layer.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from time import sleep

from vya_backupbd.restore.executor import RestoreExecutor
from vya_backupbd.restore.context import RestoreContext
from vya_backupbd.config.models import DatabaseConfig, StorageConfig


class TestRestoreExecutorCreation:
    """Test RestoreExecutor initialization."""

    def test_create_executor_with_defaults(self):
        """Test creating executor with default parameters."""
        executor = RestoreExecutor()
        
        assert executor.strategy_name == "full"
        assert executor.max_retries == 0
        assert executor.retry_delay == 5.0
        assert executor.progress_callback is None
        assert executor.cleanup_temp is True

    def test_create_executor_with_custom_params(self):
        """Test creating executor with custom parameters."""
        callback = Mock()
        executor = RestoreExecutor(
            strategy_name="full",
            max_retries=3,
            retry_delay=10.0,
            progress_callback=callback,
            cleanup_temp=False
        )
        
        assert executor.strategy_name == "full"
        assert executor.max_retries == 3
        assert executor.retry_delay == 10.0
        assert executor.progress_callback == callback
        assert executor.cleanup_temp is False

    def test_create_executor_with_invalid_retries(self):
        """Test that negative retries raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            RestoreExecutor(max_retries=-1)
        
        assert "max_retries" in str(exc_info.value).lower()


class TestRestoreExecutorExecution:
    """Test RestoreExecutor.execute() method."""

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_restore_success(self, mock_factory):
        """Test successful restore execution."""
        # Setup mock strategy
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor()

        result = executor.execute(context)

        assert result is True
        assert context.status == "completed"
        strategy.execute.assert_called_once_with(context)

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_restore_failure(self, mock_factory):
        """Test failed restore execution."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor()

        result = executor.execute(context)

        assert result is False
        assert context.status == "failed"

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_sets_context_times(self, mock_factory):
        """Test that execution sets start and end times."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor()

        assert context.start_time is None
        assert context.end_time is None

        executor.execute(context)

        assert context.start_time is not None
        assert context.end_time is not None

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_with_progress_callback(self, mock_factory):
        """Test that progress callback is called."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        callback = Mock()
        context = self._create_context()
        executor = RestoreExecutor(progress_callback=callback)

        executor.execute(context)

        # Should be called at least for start and complete
        assert callback.call_count >= 2

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_creates_correct_strategy(self, mock_factory):
        """Test that executor creates correct strategy type."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor(strategy_name="full")

        executor.execute(context)

        mock_factory.create.assert_called_once_with("full")

    def _create_context(self):
        """Helper to create a restore context."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")

        return RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql"
        )


class TestRestoreExecutorValidation:
    """Test RestoreExecutor.validate() method."""

    def test_validate_with_valid_context(self):
        """Test validation passes with valid context."""
        context = self._create_context()
        executor = RestoreExecutor()

        result = executor.validate(context)

        assert result is True

    def test_validate_missing_database_config(self):
        """Test validation fails without database config."""
        context = RestoreContext(
            database_config=None,
            storage_config=StorageConfig(type="local", path="/backups"),
            backup_file="backup.sql"
        )
        executor = RestoreExecutor()

        result = executor.validate(context)

        assert result is False

    def test_validate_missing_storage_config(self):
        """Test validation fails without storage config."""
        context = RestoreContext(
            database_config=DatabaseConfig(type="postgresql", host="localhost", port=5432, database="db"),
            storage_config=None,
            backup_file="backup.sql"
        )
        executor = RestoreExecutor()

        result = executor.validate(context)

        assert result is False

    def test_validate_missing_backup_file(self):
        """Test validation fails without backup file."""
        db_config = DatabaseConfig(type="postgresql", host="localhost", port=5432, database="db")
        storage_config = StorageConfig(type="local", path="/backups")
        
        context = RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file=""
        )
        executor = RestoreExecutor()

        result = executor.validate(context)

        assert result is False

    def _create_context(self):
        """Helper to create a restore context."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")

        return RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql"
        )


class TestRestoreExecutorRetry:
    """Test RestoreExecutor retry logic."""

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_first_attempt_success(self, mock_factory):
        """Test that successful first attempt doesn't retry."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor(max_retries=3)

        result = executor.execute(context)

        assert result is True
        # Only one attempt should be made
        assert strategy.execute.call_count == 1

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    @patch('vya_backupbd.restore.executor.sleep')
    def test_execute_with_retry_success(self, mock_sleep, mock_factory):
        """Test successful restore after retries."""
        strategy = MagicMock()
        # Fail first 2 attempts, succeed on third
        strategy.execute.side_effect = [False, False, True]
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor(max_retries=3, retry_delay=1.0)

        result = executor.execute(context)

        assert result is True
        assert strategy.execute.call_count == 3
        # Sleep should be called between attempts
        assert mock_sleep.call_count == 2

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_with_retry_all_attempts_fail(self, mock_factory):
        """Test all retry attempts fail."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor(max_retries=3)

        result = executor.execute(context)

        assert result is False
        # All 3 attempts should be made
        assert strategy.execute.call_count == 3

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    @patch('vya_backupbd.restore.executor.sleep')
    def test_execute_retry_delays(self, mock_sleep, mock_factory):
        """Test that retry delays are applied."""
        strategy = MagicMock()
        strategy.execute.side_effect = [False, False, True]
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor(max_retries=3, retry_delay=5.0)

        executor.execute(context)

        # Should sleep between retries
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(5.0), call(5.0)])

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_execute_retry_disabled(self, mock_factory):
        """Test that retry is disabled with max_retries=0."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        context = self._create_context()
        executor = RestoreExecutor(max_retries=0)

        result = executor.execute(context)

        assert result is False
        # No retries, only one attempt
        assert strategy.execute.call_count == 1

    def _create_context(self):
        """Helper to create a restore context."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")

        return RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql"
        )


class TestRestoreExecutorCleanup:
    """Test RestoreExecutor cleanup functionality."""

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_cleanup_temp_files_on_success(self, mock_factory):
        """Test that temp files are cleaned up on successful restore."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        context = self._create_context()
        
        # Simulate files being created during restore
        downloaded = MagicMock(spec=Path)
        decompressed = MagicMock(spec=Path)
        context.downloaded_file = downloaded
        context.decompressed_file = decompressed

        executor = RestoreExecutor(cleanup_temp=True)
        executor.execute(context)

        # Both temp files should be cleaned up
        downloaded.unlink.assert_called_once()
        decompressed.unlink.assert_called_once()

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_cleanup_temp_files_on_failure(self, mock_factory):
        """Test that temp files are cleaned up even on failure."""
        strategy = MagicMock()
        strategy.execute.return_value = False
        mock_factory.create.return_value = strategy

        context = self._create_context()
        
        # Simulate partial files from failed restore
        downloaded = MagicMock(spec=Path)
        context.downloaded_file = downloaded

        executor = RestoreExecutor(cleanup_temp=True)
        executor.execute(context)

        # Should cleanup even on failure
        downloaded.unlink.assert_called_once()

    @patch('vya_backupbd.restore.executor.RestoreStrategyFactory')
    def test_cleanup_disabled(self, mock_factory):
        """Test that cleanup can be disabled."""
        strategy = MagicMock()
        strategy.execute.return_value = True
        mock_factory.create.return_value = strategy

        context = self._create_context()
        
        downloaded = MagicMock(spec=Path)
        context.downloaded_file = downloaded

        executor = RestoreExecutor(cleanup_temp=False)
        executor.execute(context)

        # Cleanup should not be called
        downloaded.unlink.assert_not_called()

    def _create_context(self):
        """Helper to create a restore context for testing."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")

        return RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql"
        )

