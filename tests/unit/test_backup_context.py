"""
Unit tests for backup.context module.

Tests the BackupContext class that holds all configuration and state
for a backup operation.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock

from python_backup.backup.context import BackupContext
from python_backup.config.models import DatabaseConfig, StorageConfig, BackupConfig


class TestBackupContextCreation:
    """Test BackupContext creation and initialization."""

    def test_create_context_with_required_params(self):
        """Test creating context with minimum required parameters."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(
            type="local",
            path="/backups"
        )
        backup_config = BackupConfig(
            retention_days=7
        )

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        assert context.database_config == db_config
        assert context.storage_config == storage_config
        assert context.backup_config == backup_config
        assert context.start_time is None
        assert context.end_time is None
        assert context.status == "pending"

    def test_context_with_credentials(self):
        """Test context with database credentials."""
        db_config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            username="admin",
            password="secret123"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        assert context.database_config.username == "admin"
        assert context.database_config.password == "secret123"

    def test_context_with_s3_storage(self):
        """Test context with S3 storage configuration."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(
            type="s3",
            bucket="my-backups",
            region="us-east-1",
            prefix="db-backups/"
        )
        backup_config = BackupConfig(retention_days=30)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        assert context.storage_config.type == "s3"
        assert context.storage_config.bucket == "my-backups"
        assert context.storage_config.region == "us-east-1"

    def test_context_with_compression(self):
        """Test context with compression enabled."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(
            retention_days=7,
            compression="gzip"
        )

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        assert context.backup_config.compression == "gzip"


class TestBackupContextState:
    """Test BackupContext state management."""

    def test_start_backup_sets_state(self):
        """Test that starting backup sets timestamp and status."""
        context = self._create_simple_context()
        
        before_time = datetime.now()
        context.start()
        after_time = datetime.now()

        assert context.start_time is not None
        assert before_time <= context.start_time <= after_time
        assert context.status == "running"
        assert context.end_time is None

    def test_complete_backup_sets_state(self):
        """Test that completing backup sets timestamp and status."""
        context = self._create_simple_context()
        context.start()
        
        before_time = datetime.now()
        context.complete()
        after_time = datetime.now()

        assert context.end_time is not None
        assert before_time <= context.end_time <= after_time
        assert context.status == "completed"

    def test_fail_backup_sets_state(self):
        """Test that failing backup sets timestamp, status, and error."""
        context = self._create_simple_context()
        context.start()
        
        error_msg = "Connection refused"
        context.fail(error_msg)

        assert context.end_time is not None
        assert context.status == "failed"
        assert context.error_message == error_msg

    def test_duration_calculation(self):
        """Test duration calculation between start and end."""
        context = self._create_simple_context()
        context.start()
        
        import time
        time.sleep(0.1)  # Sleep for 100ms
        
        context.complete()
        duration = context.get_duration()

        assert duration is not None
        assert duration.total_seconds() >= 0.1
        assert duration.total_seconds() < 1.0

    def test_duration_before_start_returns_none(self):
        """Test that duration is None before backup starts."""
        context = self._create_simple_context()
        assert context.get_duration() is None

    def test_duration_while_running(self):
        """Test duration calculation while backup is running."""
        context = self._create_simple_context()
        context.start()
        
        import time
        time.sleep(0.05)
        
        duration = context.get_duration()
        assert duration is not None
        assert duration.total_seconds() >= 0.05

    def _create_simple_context(self):
        """Helper to create a simple context for testing."""
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


class TestBackupContextMetadata:
    """Test BackupContext metadata management."""

    def test_set_backup_file_path(self):
        """Test setting the backup file path."""
        context = self._create_simple_context()
        
        backup_path = Path("/backups/testdb_20260112_140530.sql.gz")
        context.set_backup_file(backup_path)

        assert context.backup_file == backup_path
        assert context.backup_file.name == "testdb_20260112_140530.sql.gz"

    def test_set_backup_size(self):
        """Test setting the backup file size."""
        context = self._create_simple_context()
        
        size_bytes = 1024 * 1024 * 50  # 50 MB
        context.set_backup_size(size_bytes)

        assert context.backup_size == size_bytes

    def test_set_compressed_size(self):
        """Test setting the compressed backup size."""
        context = self._create_simple_context()
        
        original_size = 1024 * 1024 * 50  # 50 MB
        compressed_size = 1024 * 1024 * 10  # 10 MB
        
        context.set_backup_size(original_size)
        context.set_compressed_size(compressed_size)

        assert context.backup_size == original_size
        assert context.compressed_size == compressed_size

    def test_get_compression_ratio(self):
        """Test calculating compression ratio."""
        context = self._create_simple_context()
        
        context.set_backup_size(1000)
        context.set_compressed_size(200)

        ratio = context.get_compression_ratio()
        assert ratio == 5.0  # 1000 / 200 = 5.0

    def test_compression_ratio_without_compression_returns_none(self):
        """Test that compression ratio is None without compression."""
        context = self._create_simple_context()
        context.set_backup_size(1000)

        assert context.get_compression_ratio() is None

    def test_set_storage_location(self):
        """Test setting storage location (key/path)."""
        context = self._create_simple_context()
        
        location = "db-backups/testdb_20260112_140530.sql.gz"
        context.set_storage_location(location)

        assert context.storage_location == location

    def _create_simple_context(self):
        """Helper to create a simple context for testing."""
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


class TestBackupContextSerialization:
    """Test BackupContext serialization to dict."""

    def test_to_dict_basic(self):
        """Test converting context to dictionary."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)
        
        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        data = context.to_dict()

        assert data["database_type"] == "postgresql"
        assert data["database_name"] == "testdb"
        assert data["storage_type"] == "local"
        assert data["status"] == "pending"

    def test_to_dict_with_times(self):
        """Test dictionary includes timestamps."""
        context = self._create_simple_context()
        context.start()
        context.complete()

        data = context.to_dict()

        assert "start_time" in data
        assert "end_time" in data
        assert "duration_seconds" in data
        assert data["start_time"] is not None
        assert data["end_time"] is not None
        assert data["duration_seconds"] >= 0

    def test_to_dict_with_backup_info(self):
        """Test dictionary includes backup file information."""
        context = self._create_simple_context()
        context.set_backup_file(Path("/backups/test.sql.gz"))
        context.set_backup_size(1024 * 1024 * 50)
        context.set_compressed_size(1024 * 1024 * 10)
        context.set_storage_location("backups/test.sql.gz")

        data = context.to_dict()

        assert data["backup_file"] == "/backups/test.sql.gz"
        assert data["backup_size"] == 1024 * 1024 * 50
        assert data["compressed_size"] == 1024 * 1024 * 10
        assert data["storage_location"] == "backups/test.sql.gz"
        assert data["compression_ratio"] == 5.0

    def test_to_dict_excludes_passwords(self):
        """Test that sensitive data is excluded from dict."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="admin",
            password="secret123"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        backup_config = BackupConfig(retention_days=7)
        
        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        data = context.to_dict()

        # Should have username but not password
        assert "username" not in data or data.get("username") == "admin"
        assert "password" not in data

    def _create_simple_context(self):
        """Helper to create a simple context for testing."""
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
