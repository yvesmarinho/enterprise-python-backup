"""
Unit tests for restore.context module.

Tests the RestoreContext class that holds all configuration and state
for a restore operation.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock

from vya_backupbd.restore.context import RestoreContext
from vya_backupbd.config.models import DatabaseConfig, StorageConfig


class TestRestoreContextCreation:
    """Test RestoreContext creation and initialization."""

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

        context = RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="testdb_20260112_140530.sql.gz"
        )

        assert context.database_config == db_config
        assert context.storage_config == storage_config
        assert context.backup_file == "testdb_20260112_140530.sql.gz"
        assert context.start_time is None
        assert context.end_time is None
        assert context.status == "pending"

    def test_context_with_target_database(self):
        """Test context with specific target database."""
        db_config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="sourcedb"
        )
        storage_config = StorageConfig(type="local", path="/backups")

        context = RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql",
            target_database="targetdb"
        )

        assert context.target_database == "targetdb"

    def test_context_with_decompression(self):
        """Test context detects compression from filename."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")

        context = RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql.gz"
        )

        assert context.needs_decompression() is True
        assert context.get_compression_type() == "gzip"

    def test_context_with_bzip2_compression(self):
        """Test context detects bzip2 compression."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")

        context = RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql.bz2"
        )

        assert context.needs_decompression() is True
        assert context.get_compression_type() == "bzip2"


class TestRestoreContextState:
    """Test RestoreContext state management."""

    def test_start_restore_sets_state(self):
        """Test that starting restore sets timestamp and status."""
        context = self._create_simple_context()
        
        before_time = datetime.now()
        context.start()
        after_time = datetime.now()

        assert context.start_time is not None
        assert before_time <= context.start_time <= after_time
        assert context.status == "running"
        assert context.end_time is None

    def test_complete_restore_sets_state(self):
        """Test that completing restore sets timestamp and status."""
        context = self._create_simple_context()
        context.start()
        
        before_time = datetime.now()
        context.complete()
        after_time = datetime.now()

        assert context.end_time is not None
        assert before_time <= context.end_time <= after_time
        assert context.status == "completed"

    def test_fail_restore_sets_state(self):
        """Test that failing restore sets timestamp, status, and error."""
        context = self._create_simple_context()
        context.start()
        
        error_msg = "Database not found"
        context.fail(error_msg)

        assert context.end_time is not None
        assert context.status == "failed"
        assert context.error_message == error_msg

    def test_duration_calculation(self):
        """Test duration calculation between start and end."""
        context = self._create_simple_context()
        context.start()
        
        import time
        time.sleep(0.1)
        
        context.complete()
        duration = context.get_duration()

        assert duration is not None
        assert duration.total_seconds() >= 0.1

    def test_duration_before_start_returns_none(self):
        """Test that duration is None before restore starts."""
        context = self._create_simple_context()
        assert context.get_duration() is None

    def _create_simple_context(self):
        """Helper to create a simple context for testing."""
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


class TestRestoreContextMetadata:
    """Test RestoreContext metadata management."""

    def test_set_downloaded_file(self):
        """Test setting the downloaded backup file path."""
        context = self._create_simple_context()
        
        file_path = Path("/tmp/backup.sql")
        context.set_downloaded_file(file_path)

        assert context.downloaded_file == file_path

    def test_set_decompressed_file(self):
        """Test setting the decompressed file path."""
        context = self._create_simple_context()
        
        file_path = Path("/tmp/backup.sql")
        context.set_decompressed_file(file_path)

        assert context.decompressed_file == file_path

    def test_set_restored_size(self):
        """Test setting the restored data size."""
        context = self._create_simple_context()
        
        size_bytes = 1024 * 1024 * 100  # 100 MB
        context.set_restored_size(size_bytes)

        assert context.restored_size == size_bytes

    def test_set_download_size(self):
        """Test setting the download size."""
        context = self._create_simple_context()
        
        size_bytes = 1024 * 1024 * 10  # 10 MB
        context.set_download_size(size_bytes)

        assert context.download_size == size_bytes

    def _create_simple_context(self):
        """Helper to create a simple context for testing."""
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


class TestRestoreContextSerialization:
    """Test RestoreContext serialization to dict."""

    def test_to_dict_basic(self):
        """Test converting context to dictionary."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb"
        )
        storage_config = StorageConfig(type="local", path="/backups")
        
        context = RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql"
        )

        data = context.to_dict()

        assert data["database_config"]["type"] == "postgresql"
        assert data["database_config"]["database"] == "testdb"
        assert data["storage_config"]["type"] == "local"
        assert data["backup_file"] == "backup.sql"
        assert data["status"] == "pending"

    def test_to_dict_with_times(self):
        """Test dictionary includes timestamps."""
        context = self._create_simple_context()
        context.start()
        context.complete()

        data = context.to_dict()

        assert "start_time" in data
        assert "end_time" in data
        assert "duration" in data

    def test_to_dict_with_metadata(self):
        """Test dictionary includes restore metadata."""
        context = self._create_simple_context()
        context.set_downloaded_file(Path("/tmp/backup.sql.gz"))
        context.set_decompressed_file(Path("/tmp/backup.sql"))
        context.set_download_size(1024 * 1024 * 10)
        context.set_restored_size(1024 * 1024 * 100)

        data = context.to_dict()

        assert data["downloaded_file"] == "/tmp/backup.sql.gz"
        assert data["decompressed_file"] == "/tmp/backup.sql"
        assert data["download_size"] == 1024 * 1024 * 10
        assert data["restored_size"] == 1024 * 1024 * 100

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
        
        context = RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql"
        )

        data = context.to_dict()

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
        
        return RestoreContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_file="backup.sql"
        )
