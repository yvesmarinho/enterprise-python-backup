"""
Unit tests for backup.strategy module.

Tests the Strategy pattern implementation for different backup strategies:
- Full backup strategy
- Incremental backup strategy (future)
- Differential backup strategy (future)
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call

from python_backup.backup.strategy import (
    BackupStrategy,
    FullBackupStrategy,
    BackupStrategyFactory
)
from python_backup.backup.context import BackupContext
from python_backup.config.models import DatabaseConfig, StorageConfig, BackupConfig


class TestBackupStrategyInterface:
    """Test BackupStrategy abstract base class."""

    def test_backup_strategy_is_abstract(self):
        """Test that BackupStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BackupStrategy()

    def test_strategy_requires_execute_method(self):
        """Test that subclasses must implement execute method."""
        class IncompleteStrategy(BackupStrategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()


class TestFullBackupStrategy:
    """Test FullBackupStrategy implementation."""

    def test_create_full_backup_strategy(self):
        """Test creating a full backup strategy."""
        strategy = FullBackupStrategy()
        assert strategy is not None
        assert isinstance(strategy, BackupStrategy)

    def test_get_strategy_name(self):
        """Test getting strategy name."""
        strategy = FullBackupStrategy()
        assert strategy.get_name() == "full"

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    @patch('vya_backupbd.backup.strategy.get_storage_adapter')
    def test_execute_full_backup_success(self, mock_get_storage, mock_get_adapter):
        """Test executing a successful full backup."""
        # Setup mocks
        db_adapter = MagicMock()
        
        # Mock dump to create the file
        def create_dump_file(database, path):
            Path(path).touch()
            Path(path).write_text("SQL dump data")
            return True
        
        db_adapter.backup_database.side_effect = create_dump_file
        db_adapter.get_dump_size.return_value = 1024 * 1024 * 10  # 10 MB
        mock_get_adapter.return_value = db_adapter

        storage = MagicMock()
        storage.upload.return_value = True
        mock_get_storage.return_value = storage

        # Create context
        context = self._create_context()
        strategy = FullBackupStrategy()

        # Execute backup
        result = strategy.execute(context)

        assert result is True
        assert context.status == "completed"
        assert context.backup_size > 0

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    def test_execute_full_backup_dump_failure(self, mock_get_adapter):
        """Test handling database dump failure."""
        # Setup mock to fail
        db_adapter = MagicMock()
        db_adapter.backup_database.return_value = False
        mock_get_adapter.return_value = db_adapter

        context = self._create_context()
        strategy = FullBackupStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"
        assert "dump" in context.error_message.lower()

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    @patch('vya_backupbd.backup.strategy.get_storage_adapter')
    def test_execute_full_backup_upload_failure(self, mock_get_storage, mock_get_adapter):
        """Test handling storage upload failure."""
        # Setup mocks
        db_adapter = MagicMock()
        
        def create_dump_file(database, path):
            Path(path).touch()
            Path(path).write_text("SQL dump data")
            return True
        
        db_adapter.backup_database.side_effect = create_dump_file
        db_adapter.get_dump_size.return_value = 1024 * 1024 * 10
        mock_get_adapter.return_value = db_adapter

        storage = MagicMock()
        storage.upload.return_value = False
        mock_get_storage.return_value = storage

        context = self._create_context()
        strategy = FullBackupStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"
        assert "upload" in context.error_message.lower()

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    @patch('vya_backupbd.backup.strategy.get_storage_adapter')
    @patch('vya_backupbd.backup.strategy.compress_file')
    def test_execute_with_compression(self, mock_compress, mock_get_storage, mock_get_adapter):
        """Test backup execution with compression enabled."""
        # Setup mocks
        db_adapter = MagicMock()
        
        def create_dump_file(database, path):
            dump_path = Path(path)
            dump_path.touch()
            # Write 50 MB of data
            dump_path.write_bytes(b"X" * (1024 * 1024 * 50))
            return True
        
        def create_compressed_file(source, dest, method=None):
            comp_path = Path(dest)
            comp_path.touch()
            # Write 10 MB of compressed data
            comp_path.write_bytes(b"C" * (1024 * 1024 * 10))
            return True
        
        db_adapter.backup_database.side_effect = create_dump_file
        db_adapter.get_dump_size.return_value = 1024 * 1024 * 50  # 50 MB
        mock_get_adapter.return_value = db_adapter

        mock_compress.side_effect = create_compressed_file
        
        storage = MagicMock()
        storage.upload.return_value = True
        mock_get_storage.return_value = storage

        # Create context with compression
        context = self._create_context(compression="gzip")
        strategy = FullBackupStrategy()

        result = strategy.execute(context)

        assert result is True
        mock_compress.assert_called_once()
        assert context.compressed_size == 1024 * 1024 * 10
        assert context.get_compression_ratio() == 5.0  # 50/10

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    @patch('vya_backupbd.backup.strategy.get_storage_adapter')
    def test_execute_generates_backup_filename(self, mock_get_storage, mock_get_adapter):
        """Test that backup generates proper filename."""
        # Setup mocks
        db_adapter = MagicMock()
        
        def create_dump_file(database, path):
            Path(path).touch()
            Path(path).write_text("SQL")
            return True
        
        db_adapter.backup_database.side_effect = create_dump_file
        db_adapter.get_dump_size.return_value = 1024
        mock_get_adapter.return_value = db_adapter

        storage = MagicMock()
        storage.upload.return_value = True
        mock_get_storage.return_value = storage

        context = self._create_context()
        strategy = FullBackupStrategy()

        with patch('vya_backupbd.backup.strategy.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 12, 14, 30, 45)
            result = strategy.execute(context)

        assert result is True
        assert context.backup_file is not None
        filename = context.backup_file.name
        assert "testdb" in filename
        assert "20260112" in filename
        assert filename.endswith(".sql")

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    @patch('vya_backupbd.backup.strategy.get_storage_adapter')
    def test_execute_calls_adapter_with_credentials(self, mock_get_storage, mock_get_adapter):
        """Test that database adapter is called with credentials."""
        db_adapter = MagicMock()
        db_adapter.dump.return_value = True
        db_adapter.get_dump_size.return_value = 1024
        mock_get_adapter.return_value = db_adapter

        storage = MagicMock()
        storage.upload.return_value = True
        mock_get_storage.return_value = storage

        context = self._create_context(username="admin", password="secret")
        strategy = FullBackupStrategy()

        strategy.execute(context)

        # Verify adapter was created with correct credentials
        mock_get_adapter.assert_called_once()
        call_args = mock_get_adapter.call_args
        assert call_args[0][0].username == "admin"
        assert call_args[0][0].password == "secret"

    def _create_context(self, compression=None, username=None, password=None):
        """Helper to create a backup context for testing."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username=username,
            password=password
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(
            retention_days=7,
            compression=compression
        )

        return BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )


class TestBackupStrategyFactory:
    """Test BackupStrategyFactory for creating strategies."""

    def test_create_full_backup_strategy(self):
        """Test factory creates full backup strategy."""
        strategy = BackupStrategyFactory.create("full")
        assert isinstance(strategy, FullBackupStrategy)

    def test_create_strategy_case_insensitive(self):
        """Test factory is case-insensitive."""
        strategy1 = BackupStrategyFactory.create("full")
        strategy2 = BackupStrategyFactory.create("FULL")
        strategy3 = BackupStrategyFactory.create("Full")

        assert isinstance(strategy1, FullBackupStrategy)
        assert isinstance(strategy2, FullBackupStrategy)
        assert isinstance(strategy3, FullBackupStrategy)

    def test_create_unknown_strategy_raises_error(self):
        """Test that unknown strategy type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BackupStrategyFactory.create("incremental")
        
        assert "unknown" in str(exc_info.value).lower()
        assert "incremental" in str(exc_info.value).lower()

    def test_create_empty_strategy_raises_error(self):
        """Test that empty strategy type raises ValueError."""
        with pytest.raises(ValueError):
            BackupStrategyFactory.create("")

    def test_create_none_strategy_raises_error(self):
        """Test that None strategy type raises ValueError."""
        with pytest.raises(ValueError):
            BackupStrategyFactory.create(None)

    def test_get_available_strategies(self):
        """Test getting list of available strategies."""
        strategies = BackupStrategyFactory.get_available_strategies()
        
        assert isinstance(strategies, list)
        assert "full" in strategies
        assert len(strategies) >= 1

    def test_is_strategy_available(self):
        """Test checking if a strategy is available."""
        assert BackupStrategyFactory.is_available("full") is True
        assert BackupStrategyFactory.is_available("FULL") is True
        assert BackupStrategyFactory.is_available("incremental") is False
        assert BackupStrategyFactory.is_available("differential") is False


class TestBackupStrategyEdgeCases:
    """Test edge cases and error handling."""

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    def test_execute_with_exception_in_dump(self, mock_get_adapter):
        """Test handling exception during database dump."""
        db_adapter = MagicMock()
        db_adapter.backup_database.side_effect = Exception("Connection timeout")
        mock_get_adapter.return_value = db_adapter

        context = self._create_context()
        strategy = FullBackupStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"
        assert "exception" in context.error_message.lower() or "error" in context.error_message.lower()

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    @patch('vya_backupbd.backup.strategy.get_storage_adapter')
    def test_execute_with_exception_in_upload(self, mock_get_storage, mock_get_adapter):
        """Test handling exception during storage upload."""
        db_adapter = MagicMock()
        
        def create_dump_file(database, path):
            Path(path).touch()
            Path(path).write_text("SQL")
            return True
        
        db_adapter.backup_database.side_effect = create_dump_file
        db_adapter.get_dump_size.return_value = 1024
        mock_get_adapter.return_value = db_adapter

        storage = MagicMock()
        storage.upload.side_effect = Exception("Network error")
        mock_get_storage.return_value = storage

        context = self._create_context()
        strategy = FullBackupStrategy()

        result = strategy.execute(context)

        assert result is False
        assert context.status == "failed"

    @patch('vya_backupbd.backup.strategy.get_database_adapter')
    @patch('vya_backupbd.backup.strategy.get_storage_adapter')
    @patch('vya_backupbd.backup.strategy.compress_file')
    def test_execute_compression_failure_continues(self, mock_compress, mock_get_storage, mock_get_adapter):
        """Test that compression failure doesn't stop backup."""
        db_adapter = MagicMock()
        
        def create_dump_file(database, path):
            Path(path).touch()
            Path(path).write_text("SQL")
            return True
        
        db_adapter.backup_database.side_effect = create_dump_file
        db_adapter.get_dump_size.return_value = 1024
        mock_get_adapter.return_value = db_adapter

        mock_compress.return_value = False  # Compression fails

        storage = MagicMock()
        storage.upload.return_value = True
        mock_get_storage.return_value = storage

        context = self._create_context(compression="gzip")
        strategy = FullBackupStrategy()

        result = strategy.execute(context)

        # Should upload uncompressed file as fallback
        assert result is True
        assert context.compressed_size is None

    def _create_context(self, compression=None):
        """Helper to create a backup context for testing."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(
            retention_days=7,
            compression=compression
        )

        return BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )
