"""
End-to-end integration tests for backup engine.

Tests the complete backup workflow from database dump to storage upload.
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from python_backup.backup.executor import BackupExecutor
from python_backup.backup.context import BackupContext
from python_backup.config.models import DatabaseConfig, StorageConfig, BackupConfig


@pytest.fixture
def temp_backup_dir():
    """Create a temporary directory for backups."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


class TestBackupE2EPostgreSQL:
    """End-to-end tests for PostgreSQL backups."""

    @patch('python_backup.backup.strategy.get_database_adapter')
    def test_full_backup_postgresql_to_local_storage(
        self, mock_get_adapter, temp_backup_dir, temp_storage_dir
    ):
        """Test complete PostgreSQL backup to local storage."""
        # Mock adapter to create backup file
        adapter = MagicMock()
        
        def create_backup(database, path):
            Path(path).touch()
            Path(path).write_text("-- PostgreSQL backup\nCREATE TABLE test (id INT);")
            return True
        
        adapter.backup_database.side_effect = create_backup
        mock_get_adapter.return_value = adapter

        # Configure backup
        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="postgres",
            password="password"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(retention_days=7)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        # Execute backup
        executor = BackupExecutor()
        result = executor.execute(context)

        # Verify
        assert result is True
        assert context.status == "completed"
        assert context.backup_file is not None
        assert context.start_time is not None
        assert context.end_time is not None

    @patch('python_backup.db.postgresql.subprocess.run')
    def test_full_backup_postgresql_with_compression(
        self, mock_run, temp_backup_dir, temp_storage_dir
    ):
        """Test PostgreSQL backup with gzip compression."""
        # Mock pg_dump success
        mock_run.return_value = MagicMock(returncode=0)

        # Create backup file
        backup_file = temp_backup_dir / "testdb.sql"
        backup_file.write_text("-- PostgreSQL backup\n" * 1000)  # Larger file

        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="postgres",
            password="password"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(
            retention_days=7,
            compression="gzip"
        )

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        executor = BackupExecutor()
        
        with patch('python_backup.backup.strategy.tempfile.mkdtemp', return_value=str(temp_backup_dir)):
            result = executor.execute(context)

        assert result is True
        assert context.compressed_size is not None
        assert context.compressed_size < context.backup_size


class TestBackupE2EMySQL:
    """End-to-end tests for MySQL backups."""

    @patch('python_backup.db.mysql.subprocess.run')
    def test_full_backup_mysql_to_local_storage(
        self, mock_run, temp_backup_dir, temp_storage_dir
    ):
        """Test complete MySQL backup to local storage."""
        # Mock mysqldump success
        mock_run.return_value = MagicMock(returncode=0)

        # Create backup file
        backup_file = temp_backup_dir / "testdb.sql"
        backup_file.write_text("-- MySQL dump\nCREATE TABLE test (id INT);")

        db_config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            username="root",
            password="password"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(retention_days=7)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        executor = BackupExecutor()
        
        with patch('python_backup.backup.strategy.tempfile.mkdtemp', return_value=str(temp_backup_dir)):
            result = executor.execute(context)

        assert result is True
        assert context.status == "completed"

    @patch('python_backup.db.mysql.subprocess.run')
    def test_full_backup_mysql_with_bzip2_compression(
        self, mock_run, temp_backup_dir, temp_storage_dir
    ):
        """Test MySQL backup with bzip2 compression."""
        # Mock mysqldump success
        mock_run.return_value = MagicMock(returncode=0)

        # Create backup file
        backup_file = temp_backup_dir / "testdb.sql"
        backup_file.write_text("-- MySQL dump\n" * 1000)

        db_config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            username="root",
            password="password"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(
            retention_days=7,
            compression="bzip2"
        )

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        executor = BackupExecutor()
        
        with patch('python_backup.backup.strategy.tempfile.mkdtemp', return_value=str(temp_backup_dir)):
            result = executor.execute(context)

        assert result is True
        assert context.backup_config.compression == "bzip2"


class TestBackupE2ES3Storage:
    """End-to-end tests for S3 storage."""

    @patch('python_backup.db.postgresql.subprocess.run')
    @patch('boto3.client')
    def test_full_backup_to_s3_storage(
        self, mock_boto_client, mock_run, temp_backup_dir
    ):
        """Test complete backup to S3 storage."""
        # Mock pg_dump success
        mock_run.return_value = MagicMock(returncode=0)

        # Mock S3 client
        s3_client = MagicMock()
        s3_client.upload_file.return_value = None
        mock_boto_client.return_value = s3_client

        # Create backup file
        backup_file = temp_backup_dir / "testdb.sql"
        backup_file.write_text("-- PostgreSQL backup\nCREATE TABLE test (id INT);")

        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="postgres",
            password="password"
        )
        storage_config = StorageConfig(
            type="s3",
            bucket="my-backups",
            region="us-east-1",
            prefix="db-backups/",
            access_key="AKIAEXAMPLE",
            secret_key="secret123"
        )
        backup_config = BackupConfig(retention_days=30)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        executor = BackupExecutor()
        
        with patch('python_backup.backup.strategy.tempfile.mkdtemp', return_value=str(temp_backup_dir)):
            result = executor.execute(context)

        assert result is True
        assert context.storage_config.type == "s3"
        s3_client.upload_file.assert_called_once()


class TestBackupE2EErrorHandling:
    """End-to-end tests for error handling."""

    @patch('python_backup.db.postgresql.subprocess.run')
    def test_backup_fails_when_database_dump_fails(
        self, mock_run, temp_storage_dir
    ):
        """Test backup fails gracefully when database dump fails."""
        # Mock pg_dump failure
        mock_run.return_value = MagicMock(returncode=1, stderr="Connection refused")

        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="postgres",
            password="password"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(retention_days=7)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        executor = BackupExecutor()
        result = executor.execute(context)

        assert result is False
        assert context.status == "failed"
        assert context.error_message is not None

    @patch('python_backup.db.postgresql.subprocess.run')
    def test_backup_retry_on_transient_failure(
        self, mock_run, temp_backup_dir, temp_storage_dir
    ):
        """Test backup retries on transient failures."""
        # First call fails, second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="Temporary error"),
            MagicMock(returncode=0)
        ]

        # Create backup file for second attempt
        backup_file = temp_backup_dir / "testdb.sql"
        backup_file.write_text("-- PostgreSQL backup\nCREATE TABLE test (id INT);")

        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="postgres",
            password="password"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(retention_days=7)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        executor = BackupExecutor(max_retries=2)
        
        with patch('python_backup.backup.strategy.tempfile.mkdtemp', return_value=str(temp_backup_dir)):
            result = executor.execute(context)

        assert result is True
        assert context.status == "completed"
        assert mock_run.call_count == 2


class TestBackupE2EProgressTracking:
    """End-to-end tests for progress tracking."""

    @patch('python_backup.db.postgresql.subprocess.run')
    def test_backup_reports_progress(
        self, mock_run, temp_backup_dir, temp_storage_dir
    ):
        """Test backup reports progress through callback."""
        # Mock pg_dump success
        mock_run.return_value = MagicMock(returncode=0)

        # Create backup file
        backup_file = temp_backup_dir / "testdb.sql"
        backup_file.write_text("-- PostgreSQL backup\nCREATE TABLE test (id INT);")

        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="postgres",
            password="password"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(retention_days=7)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        # Track progress
        progress_events = []
        
        def progress_callback(message, context=None):
            progress_events.append(message)

        executor = BackupExecutor(progress_callback=progress_callback)
        
        with patch('python_backup.backup.strategy.tempfile.mkdtemp', return_value=str(temp_backup_dir)):
            executor.execute(context)

        # Verify progress was reported
        assert len(progress_events) >= 2
        assert any("start" in event.lower() for event in progress_events)
        assert any("complet" in event.lower() for event in progress_events)


class TestBackupE2ECredentials:
    """End-to-end tests with encrypted credentials."""

    @patch('python_backup.db.postgresql.subprocess.run')
    @patch('python_backup.security.credentials.CredentialManager')
    def test_backup_with_encrypted_credentials(
        self, mock_cred_manager, mock_run, temp_backup_dir, temp_storage_dir
    ):
        """Test backup using encrypted credentials."""
        # Mock credential retrieval
        cred_manager_instance = MagicMock()
        cred_manager_instance.get_credentials.return_value = {
            'username': 'postgres',
            'password': 'decrypted_password'
        }
        mock_cred_manager.return_value = cred_manager_instance

        # Mock pg_dump success
        mock_run.return_value = MagicMock(returncode=0)

        # Create backup file
        backup_file = temp_backup_dir / "testdb.sql"
        backup_file.write_text("-- PostgreSQL backup\nCREATE TABLE test (id INT);")

        db_config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            credential_name="prod_postgres"
        )
        storage_config = StorageConfig(
            type="local",
            path=str(temp_storage_dir)
        )
        backup_config = BackupConfig(retention_days=7)

        context = BackupContext(
            database_config=db_config,
            storage_config=storage_config,
            backup_config=backup_config
        )

        executor = BackupExecutor()
        
        with patch('python_backup.backup.strategy.tempfile.mkdtemp', return_value=str(temp_backup_dir)):
            result = executor.execute(context)

        assert result is True
        cred_manager_instance.get_credentials.assert_called_once()
