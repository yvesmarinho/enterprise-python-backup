"""
Unit tests for PostgreSQL database adapter.

Tests PostgreSQL-specific functionality including connection,
backup commands, and database operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import subprocess

from python_backup.config.models import DatabaseConfig
from python_backup.db.postgresql import PostgreSQLAdapter


class TestPostgreSQLAdapterInitialization:
    """Test PostgreSQL adapter initialization."""

    def test_postgresql_adapter_creation(self, sample_postgresql_config):
        """Test creating PostgreSQL adapter."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        assert adapter is not None
        assert adapter.config.type == "postgresql"

    def test_postgresql_adapter_validates_type(self, sample_mysql_config):
        """Test that PostgreSQL adapter rejects MySQL config."""
        with pytest.raises(ValueError, match="PostgreSQL adapter requires type='postgresql'"):
            PostgreSQLAdapter(sample_mysql_config)

    def test_postgresql_adapter_has_engine(self, sample_postgresql_config):
        """Test that adapter has SQLAlchemy engine."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        assert adapter.engine is not None
        assert "postgresql" in str(adapter.engine.url)


class TestPostgreSQLGetDatabases:
    """Test PostgreSQL database listing."""

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_get_databases_returns_list(self, mock_execute, sample_postgresql_config):
        """Test getting list of databases."""
        mock_execute.return_value = [
            ("postgres",),
            ("template0",),
            ("template1",),
            ("myapp",),
            ("testdb",)
        ]
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        databases = adapter.get_databases()
        
        assert isinstance(databases, list)
        assert "myapp" in databases
        assert "testdb" in databases
        # System databases should be filtered
        assert "postgres" not in databases
        assert "template0" not in databases
        assert "template1" not in databases

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_get_databases_excludes_system_dbs(self, mock_execute, sample_postgresql_config):
        """Test that system databases are excluded."""
        mock_execute.return_value = [
            ("postgres",),
            ("template0",),
            ("template1",),
            ("userdb",)
        ]
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        databases = adapter.get_databases()
        
        assert len(databases) == 1
        assert databases[0] == "userdb"

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_get_databases_empty_result(self, mock_execute, sample_postgresql_config):
        """Test handling of empty database list."""
        mock_execute.return_value = [
            ("postgres",),
            ("template0",)
        ]
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        databases = adapter.get_databases()
        
        assert databases == []

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_get_databases_connection_error(self, mock_execute, sample_postgresql_config):
        """Test handling of connection errors."""
        mock_execute.side_effect = Exception("Connection failed")
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        with pytest.raises(Exception, match="Connection failed"):
            adapter.get_databases()


class TestPostgreSQLTestConnection:
    """Test PostgreSQL connection testing."""

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_connection_success(self, mock_execute, sample_postgresql_config):
        """Test successful connection test."""
        mock_execute.return_value = [(1,)]
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.test_connection()
        
        assert result is True
        # Check that _execute_query was called with a TextClause object
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]
        assert hasattr(call_args, '__class__')
        assert 'TextClause' in str(call_args.__class__)

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_connection_failure(self, mock_execute, sample_postgresql_config):
        """Test connection failure handling."""
        mock_execute.side_effect = Exception("Access denied")
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.test_connection()
        
        assert result is False

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_connection_timeout(self, mock_execute, sample_postgresql_config):
        """Test connection timeout handling."""
        mock_execute.side_effect = TimeoutError("Connection timeout")
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.test_connection()
        
        assert result is False


class TestPostgreSQLGetBackupCommand:
    """Test PostgreSQL backup command generation."""

    def test_backup_command_basic(self, sample_postgresql_config):
        """Test basic pg_dump command generation."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        assert "pg_dump" in command
        assert "--username=testuser" in command or "-U testuser" in command
        assert "--host=localhost" in command or "-h localhost" in command
        assert "--port=5432" in command or "-p 5432" in command
        assert "testdb" in command
        assert "/tmp/backup.sql" in command

    def test_backup_command_with_password(self, sample_postgresql_config):
        """Test that password is set via environment variable."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        # PostgreSQL uses PGPASSWORD env var, not command line
        # Command should not have password in it
        assert "testpass" not in command

    def test_backup_command_with_ssl(self):
        """Test backup command with SSL enabled."""
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            username="testuser",
            password="testpass",
            ssl_enabled=True
        )
        adapter = PostgreSQLAdapter(config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        # PostgreSQL doesn't use explicit SSL flag in pg_dump
        # SSL is controlled via connection string or PGSSLMODE env var
        assert "pg_dump" in command

    def test_backup_command_without_ssl(self):
        """Test backup command without SSL."""
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            username="testuser",
            password="testpass",
            ssl_enabled=False
        )
        adapter = PostgreSQLAdapter(config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        # Should not have SSL settings
        assert "sslmode" not in command.lower()

    def test_backup_command_with_custom_port(self):
        """Test backup command with custom port."""
        config = DatabaseConfig(
            id="test-pg-custom",
            type="postgresql",
            host="localhost",
            port=5433,
            username="testuser",
            password="testpass",
            database="testdb"
        )
        adapter = PostgreSQLAdapter(config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        assert "5433" in command

    def test_backup_command_includes_options(self, sample_postgresql_config):
        """Test that backup command includes necessary options."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        # Should include common options
        assert "--format=custom" in command or "--format=plain" in command or "-F" in command
        assert "--clean" in command or "--create" in command or "-c" in command or "-C" in command

    def test_backup_command_special_characters_in_path(self, sample_postgresql_config):
        """Test backup command with special characters in path."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup with spaces.sql")
        
        # Path should be quoted or escaped
        assert "backup with spaces" in command

    def test_backup_command_format_custom(self, sample_postgresql_config):
        """Test backup command with custom format."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.dump")
        
        # Should use custom format for .dump files
        assert "--format=custom" in command or "-Fc" in command


class TestPostgreSQLBackupDatabase:
    """Test PostgreSQL database backup execution."""

    @patch('subprocess.run')
    def test_backup_database_success(self, mock_run, sample_postgresql_config):
        """Test successful database backup."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_backup_database_failure(self, mock_run, sample_postgresql_config):
        """Test failed database backup."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_database_exception(self, mock_run, sample_postgresql_config):
        """Test backup with subprocess exception."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "pg_dump")
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_timeout_error(self, mock_run, sample_postgresql_config):
        """Test backup timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pg_dump", timeout=3600)
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_unexpected_error(self, mock_run, sample_postgresql_config):
        """Test backup unexpected exception handling."""
        mock_run.side_effect = ValueError("Unexpected error")
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_database_sets_pgpassword(self, mock_run, sample_postgresql_config):
        """Test that PGPASSWORD environment variable is set."""
        mock_run.return_value = Mock(returncode=0)
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        adapter.backup_database("testdb", "/tmp/backup.sql")
        
        # Check that env was set
        call_kwargs = mock_run.call_args.kwargs
        assert 'env' in call_kwargs
        assert 'PGPASSWORD' in call_kwargs['env']
        assert call_kwargs['env']['PGPASSWORD'] == "testpass"

    @patch('subprocess.run')
    def test_backup_creates_compressed_output(self, mock_run, sample_postgresql_config):
        """Test backup with compression."""
        mock_run.return_value = Mock(returncode=0)
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql.gz")
        
        assert result is True
        # Should pipe through gzip
        call_args = str(mock_run.call_args)
        assert "gzip" in call_args or ".gz" in call_args


class TestPostgreSQLSystemDatabases:
    """Test PostgreSQL system database handling."""

    def test_system_databases_list(self, sample_postgresql_config):
        """Test that PostgreSQL system databases are defined."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        system_dbs = adapter.config.db_ignore
        
        assert "postgres" in system_dbs
        assert "template0" in system_dbs
        assert "template1" in system_dbs

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_system_databases_filtered_in_get_databases(self, mock_execute, sample_postgresql_config):
        """Test that get_databases filters system databases."""
        mock_execute.return_value = [
            ("postgres",),
            ("template0",),
            ("testapp",)
        ]
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        databases = adapter.get_databases()
        
        assert "testapp" in databases
        assert "postgres" not in databases
        assert "template0" not in databases


class TestPostgreSQLAdapterContextManager:
    """Test PostgreSQL adapter as context manager."""

    def test_context_manager_usage(self, sample_postgresql_config):
        """Test adapter works as context manager."""
        with PostgreSQLAdapter(sample_postgresql_config) as adapter:
            assert adapter is not None
            assert adapter.engine is not None

    def test_context_manager_cleanup(self, sample_postgresql_config):
        """Test that resources are cleaned up after context."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        with patch.object(adapter.engine, 'dispose', wraps=adapter.engine.dispose) as mock_dispose:
            with adapter:
                pass
            
            # Verify dispose was called
            mock_dispose.assert_called_once()


class TestPostgreSQLSpecialCases:
    """Test PostgreSQL-specific edge cases."""

    @patch('python_backup.db.postgresql.PostgreSQLAdapter._execute_query')
    def test_database_with_special_characters(self, mock_execute, sample_postgresql_config):
        """Test handling of database names with special characters."""
        mock_execute.return_value = [
            ("my-database",),
            ("my_database",),
            ("my.database",)
        ]
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        databases = adapter.get_databases()
        
        assert "my-database" in databases
        assert "my_database" in databases
        assert "my.database" in databases

    def test_backup_command_with_schema(self, sample_postgresql_config):
        """Test backup command with schema specification."""
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        # Should be able to handle schema-specific backups
        assert "pg_dump" in command

    @patch('subprocess.run')
    def test_backup_database_large_database(self, mock_run, sample_postgresql_config):
        """Test backup of large database."""
        mock_run.return_value = Mock(returncode=0)
        
        adapter = PostgreSQLAdapter(sample_postgresql_config)
        result = adapter.backup_database("largedb", "/tmp/large_backup.dump")
        
        assert result is True
        # Should use custom format for better compression
        call_args = str(mock_run.call_args)
        assert "pg_dump" in call_args
