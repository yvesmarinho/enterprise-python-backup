"""
Unit tests for restore.strategy module.

Tests the Strategy pattern implementation for restore strategies.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from vya_backupbd.restore.strategy import (
    RestoreStrategy,
    FullRestoreStrategy,
    RestoreStrategyFactory
)
from vya_backupbd.restore.context import RestoreContext
from vya_backupbd.config.models import DatabaseConfig, StorageConfig


class TestRestoreStrategyInterface:
    """Test RestoreStrategy abstract base class."""

    def test_restore_strategy_is_abstract(self):
        """Test that RestoreStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RestoreStrategy()

    def test_strategy_requires_execute_method(self):
        """Test that subclasses must implement execute method."""
        class IncompleteStrategy(RestoreStrategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()


class TestFullRestoreStrategy:
    """Test FullRestoreStrategy implementation."""

    def test_create_full_restore_strategy(self):
        """Test creating a full restore strategy."""
        strategy = FullRestoreStrategy()
        assert strategy is not None
        assert isinstance(strategy, RestoreStrategy)

    def test_get_strategy_name(self):
        """Test getting strategy name."""
        strategy = FullRestoreStrategy()
        assert strategy.get_name() == "full"

    @patch('vya_backupbd.restore.strategy.get_database_adapter')
    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    def test_execute_full_restore_success(self, mock_get_storage, mock_get_adapter):
        """Test executing a successful full restore."""
        # Setup mocks
        storage = MagicMock()
        
        def download_file(source, dest):
            Path(dest).touch()
            Path(dest).write_text("SQL backup data")
            return True
        
        storage.download.side_effect = download_file
        mock_get_storage.return_value = storage

        db_adapter = MagicMock()
        
        def restore_db(database, file_path):
            return True
        
        db_adapter.restore_database.side_effect = restore_db
        mock_get_adapter.return_value = db_adapter

        # Create context
        context = self._create_context()
        strategy = FullRestoreStrategy()

        # Execute restore
        result = strategy.execute(context)

        assert result is True
        assert context.status == "completed"

    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    def test_execute_restore_download_failure(self, mock_get_storage):
        """Test handling download failure."""
        storage = MagicMock()
        storage.download.return_value = False
        mock_get_storage.return_value = storage

        context = self._create_context()
        strategy = FullRestoreStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"
        assert "download" in context.error_message.lower()

    @patch('vya_backupbd.restore.strategy.get_database_adapter')
    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    def test_execute_restore_database_failure(self, mock_get_storage, mock_get_adapter):
        """Test handling database restore failure."""
        storage = MagicMock()
        
        def download_file(source, dest):
            Path(dest).touch()
            Path(dest).write_text("SQL data")
            return True
        
        storage.download.side_effect = download_file
        mock_get_storage.return_value = storage

        db_adapter = MagicMock()
        db_adapter.restore_database.return_value = False
        mock_get_adapter.return_value = db_adapter

        context = self._create_context()
        strategy = FullRestoreStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"
        assert "restore" in context.error_message.lower()

    @patch('vya_backupbd.restore.strategy.get_database_adapter')
    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    @patch('vya_backupbd.restore.strategy.decompress_file')
    def test_execute_with_decompression(self, mock_decompress, mock_get_storage, mock_get_adapter):
        """Test restore with compressed backup."""
        # Setup storage mock
        storage = MagicMock()
        
        def download_file(source, dest):
            Path(dest).touch()
            Path(dest).write_bytes(b"compressed data" * 100)
            return True
        
        storage.download.side_effect = download_file
        mock_get_storage.return_value = storage

        # Setup decompress mock
        def decompress(source, dest, method=None):
            Path(dest).touch()
            Path(dest).write_text("SQL backup data")
            return True
        
        mock_decompress.side_effect = decompress

        # Setup database adapter mock
        db_adapter = MagicMock()
        db_adapter.restore_database.return_value = True
        mock_get_adapter.return_value = db_adapter

        # Create context with compressed file
        context = self._create_context(backup_file="backup.sql.gz")
        strategy = FullRestoreStrategy()

        result = strategy.execute(context)

        assert result is True
        mock_decompress.assert_called_once()
        assert context.decompressed_file is not None

    @patch('vya_backupbd.restore.strategy.get_database_adapter')
    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    def test_execute_with_target_database(self, mock_get_storage, mock_get_adapter):
        """Test restore to specific target database."""
        storage = MagicMock()
        
        def download_file(source, dest):
            Path(dest).touch()
            Path(dest).write_text("SQL data")
            return True
        
        storage.download.side_effect = download_file
        mock_get_storage.return_value = storage

        db_adapter = MagicMock()
        db_adapter.restore_database.return_value = True
        mock_get_adapter.return_value = db_adapter

        context = self._create_context(target_database="targetdb")
        strategy = FullRestoreStrategy()

        strategy.execute(context)

        # Verify restore was called with target database
        db_adapter.restore_database.assert_called_once()
        call_args = db_adapter.restore_database.call_args
        assert call_args[0][0] == "targetdb"

    def _create_context(self, backup_file="backup.sql", target_database=None):
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
            backup_file=backup_file,
            target_database=target_database
        )


class TestRestoreStrategyFactory:
    """Test RestoreStrategyFactory for creating strategies."""

    def test_create_full_restore_strategy(self):
        """Test factory creates full restore strategy."""
        strategy = RestoreStrategyFactory.create("full")
        assert isinstance(strategy, FullRestoreStrategy)

    def test_create_strategy_case_insensitive(self):
        """Test factory is case-insensitive."""
        strategy1 = RestoreStrategyFactory.create("full")
        strategy2 = RestoreStrategyFactory.create("FULL")
        strategy3 = RestoreStrategyFactory.create("Full")

        assert isinstance(strategy1, FullRestoreStrategy)
        assert isinstance(strategy2, FullRestoreStrategy)
        assert isinstance(strategy3, FullRestoreStrategy)

    def test_create_unknown_strategy_raises_error(self):
        """Test that unknown strategy type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            RestoreStrategyFactory.create("partial")
        
        assert "unknown" in str(exc_info.value).lower()

    def test_create_empty_strategy_raises_error(self):
        """Test that empty strategy type raises ValueError."""
        with pytest.raises(ValueError):
            RestoreStrategyFactory.create("")

    def test_get_available_strategies(self):
        """Test getting list of available strategies."""
        strategies = RestoreStrategyFactory.get_available_strategies()
        
        assert isinstance(strategies, list)
        assert "full" in strategies

    def test_is_strategy_available(self):
        """Test checking if a strategy is available."""
        assert RestoreStrategyFactory.is_available("full") is True
        assert RestoreStrategyFactory.is_available("FULL") is True
        assert RestoreStrategyFactory.is_available("partial") is False


class TestRestoreStrategyEdgeCases:
    """Test edge cases and error handling."""

    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    def test_execute_with_exception_in_download(self, mock_get_storage):
        """Test handling exception during download."""
        storage = MagicMock()
        storage.download.side_effect = Exception("Network timeout")
        mock_get_storage.return_value = storage

        context = self._create_context()
        strategy = FullRestoreStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"
        assert context.error_message is not None

    @patch('vya_backupbd.restore.strategy.get_database_adapter')
    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    def test_execute_with_exception_in_restore(self, mock_get_storage, mock_get_adapter):
        """Test handling exception during database restore."""
        storage = MagicMock()
        
        def download_file(source, dest):
            Path(dest).touch()
            return True
        
        storage.download.side_effect = download_file
        mock_get_storage.return_value = storage

        db_adapter = MagicMock()
        db_adapter.restore_database.side_effect = Exception("SQL error")
        mock_get_adapter.return_value = db_adapter

        context = self._create_context()
        strategy = FullRestoreStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"

    @patch('vya_backupbd.restore.strategy.get_database_adapter')
    @patch('vya_backupbd.restore.strategy.get_storage_adapter')
    @patch('vya_backupbd.restore.strategy.decompress_file')
    def test_execute_decompression_failure_stops_restore(self, mock_decompress, mock_get_storage, mock_get_adapter):
        """Test that decompression failure stops restore."""
        storage = MagicMock()
        
        def download_file(source, dest):
            Path(dest).touch()
            return True
        
        storage.download.side_effect = download_file
        mock_get_storage.return_value = storage

        mock_decompress.return_value = False

        db_adapter = MagicMock()
        mock_get_adapter.return_value = db_adapter

        context = self._create_context(backup_file="backup.sql.gz")
        strategy = FullRestoreStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"
        # Database restore should not be called
        db_adapter.restore_database.assert_not_called()

    def _create_context(self, backup_file="backup.sql"):
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
            backup_file=backup_file
        )
