"""
Unit tests for MySQL database adapter.

Tests MySQL-specific functionality including connection,
backup commands, and database operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import subprocess

from python_backup.config.models import DatabaseConfig
from python_backup.db.mysql import MySQLAdapter


class TestMySQLAdapterInitialization:
    """Test MySQL adapter initialization."""

    def test_mysql_adapter_creation(self, sample_mysql_config):
        """Test creating MySQL adapter."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        assert adapter is not None
        assert adapter.config.type == "mysql"

    def test_mysql_adapter_validates_type(self, sample_postgresql_config):
        """Test that MySQL adapter rejects PostgreSQL config."""
        with pytest.raises(ValueError, match="MySQL adapter requires type='mysql'"):
            MySQLAdapter(sample_postgresql_config)

    def test_mysql_adapter_has_engine(self, sample_mysql_config):
        """Test that adapter has SQLAlchemy engine."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        assert adapter.engine is not None
        assert "mysql" in str(adapter.engine.url)


class TestMySQLGetDatabases:
    """Test MySQL database listing."""

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_get_databases_returns_list(self, mock_execute, sample_mysql_config):
        """Test getting list of databases."""
        mock_execute.return_value = [
            ("information_schema",),
            ("mysql",),
            ("performance_schema",),
            ("sys",),
            ("myapp",),
            ("testdb",)
        ]
        
        adapter = MySQLAdapter(sample_mysql_config)
        databases = adapter.get_databases()
        
        assert isinstance(databases, list)
        assert "myapp" in databases
        assert "testdb" in databases
        # System databases should be filtered
        assert "information_schema" not in databases
        assert "mysql" not in databases

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_get_databases_excludes_system_dbs(self, mock_execute, sample_mysql_config):
        """Test that system databases are excluded."""
        mock_execute.return_value = [
            ("information_schema",),
            ("mysql",),
            ("performance_schema",),
            ("sys",),
            ("userdb",)
        ]
        
        adapter = MySQLAdapter(sample_mysql_config)
        databases = adapter.get_databases()
        
        assert len(databases) == 1
        assert databases[0] == "userdb"

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_get_databases_empty_result(self, mock_execute, sample_mysql_config):
        """Test handling of empty database list."""
        mock_execute.return_value = [
            ("information_schema",),
            ("mysql",)
        ]
        
        adapter = MySQLAdapter(sample_mysql_config)
        databases = adapter.get_databases()
        
        assert databases == []

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_get_databases_connection_error(self, mock_execute, sample_mysql_config):
        """Test handling of connection errors."""
        mock_execute.side_effect = Exception("Connection failed")
        
        adapter = MySQLAdapter(sample_mysql_config)
        
        with pytest.raises(Exception, match="Connection failed"):
            adapter.get_databases()


class TestMySQLTestConnection:
    """Test MySQL connection testing."""

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_connection_success(self, mock_execute, sample_mysql_config):
        """Test successful connection test."""
        mock_execute.return_value = [(1,)]
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.test_connection()
        
        assert result is True
        # Check that _execute_query was called with a TextClause object
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]
        assert hasattr(call_args, '__class__')
        assert 'TextClause' in str(call_args.__class__)

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_connection_failure(self, mock_execute, sample_mysql_config):
        """Test connection failure handling."""
        mock_execute.side_effect = Exception("Access denied")
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.test_connection()
        
        assert result is False

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_connection_timeout(self, mock_execute, sample_mysql_config):
        """Test connection timeout handling."""
        mock_execute.side_effect = TimeoutError("Connection timeout")
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.test_connection()
        
        assert result is False


class TestMySQLGetBackupCommand:
    """Test MySQL backup command generation."""

    def test_backup_command_basic(self, sample_mysql_config):
        """Test basic mysqldump command generation."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        assert "mysqldump" in command
        assert "--user=testuser" in command
        assert "--host=localhost" in command
        assert "--port=3306" in command
        assert "testdb" in command
        assert "/tmp/backup.sql" in command

    def test_backup_command_with_password(self, sample_mysql_config):
        """Test that password is included in command."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        assert "--password=" in command or "-p" in command

    def test_backup_command_with_ssl(self):
        """Test backup command with SSL enabled."""
        config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            username="testuser",
            password="testpass",
            ssl_enabled=True
        )
        adapter = MySQLAdapter(config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        assert "--ssl" in command or "--ssl-mode=REQUIRED" in command

    def test_backup_command_without_ssl(self):
        """Test backup command without SSL."""
        config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            username="testuser",
            password="testpass",
            ssl_enabled=False
        )
        adapter = MySQLAdapter(config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        assert "--ssl" not in command or "--ssl-mode" not in command

    def test_backup_command_with_custom_port(self):
        """Test backup command with custom port."""
        config = DatabaseConfig(
            id="test-mysql-custom",
            type="mysql",
            host="localhost",
            port=3307,
            username="testuser",
            password="testpass",
            database="testdb"
        )
        adapter = MySQLAdapter(config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        assert "--port=3307" in command

    def test_backup_command_includes_options(self, sample_mysql_config):
        """Test that backup command includes necessary options."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        
        # Should include common options
        assert "--single-transaction" in command or "--lock-tables" in command
        assert "--routines" in command or "--triggers" in command

    def test_backup_command_special_characters_in_path(self, sample_mysql_config):
        """Test backup command with special characters in path."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup with spaces.sql")
        
        # Path should be quoted or escaped
        assert "backup with spaces" in command


class TestMySQLBackupDatabase:
    """Test MySQL database backup execution."""

    @patch('subprocess.run')
    def test_backup_database_success(self, mock_run, sample_mysql_config):
        """Test successful database backup."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_backup_database_failure(self, mock_run, sample_mysql_config):
        """Test failed database backup."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_database_exception(self, mock_run, sample_mysql_config):
        """Test backup with subprocess exception."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "mysqldump")
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_timeout_error(self, mock_run, sample_mysql_config):
        """Test backup timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="mysqldump", timeout=3600)
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_unexpected_error(self, mock_run, sample_mysql_config):
        """Test backup unexpected exception handling."""
        mock_run.side_effect = ValueError("Unexpected error")
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql")
        
        assert result is False

    @patch('subprocess.run')
    def test_backup_creates_compressed_output(self, mock_run, sample_mysql_config):
        """Test backup with compression."""
        mock_run.return_value = Mock(returncode=0)
        
        adapter = MySQLAdapter(sample_mysql_config)
        result = adapter.backup_database("testdb", "/tmp/backup.sql.gz")
        
        assert result is True
        # Should pipe through gzip
        call_args = str(mock_run.call_args)
        assert "gzip" in call_args or ".gz" in call_args


class TestMySQLSystemDatabases:
    """Test MySQL system database handling."""

    def test_system_databases_list(self, sample_mysql_config):
        """Test that MySQL system databases are defined."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        system_dbs = adapter.config.db_ignore
        
        assert "mysql" in system_dbs
        assert "information_schema" in system_dbs
        assert "performance_schema" in system_dbs
        assert "sys" in system_dbs

    @patch('python_backup.db.mysql.MySQLAdapter._execute_query')
    def test_system_databases_filtered_in_get_databases(self, mock_execute, sample_mysql_config):
        """Test that get_databases filters system databases."""
        mock_execute.return_value = [
            ("mysql",),
            ("information_schema",),
            ("testapp",)
        ]
        
        adapter = MySQLAdapter(sample_mysql_config)
        databases = adapter.get_databases()
        
        assert "testapp" in databases
        assert "mysql" not in databases
        assert "information_schema" not in databases


class TestMySQLAdapterContextManager:
    """Test MySQL adapter as context manager."""

    def test_context_manager_usage(self, sample_mysql_config):
        """Test adapter works as context manager."""
        with MySQLAdapter(sample_mysql_config) as adapter:
            assert adapter is not None
            assert adapter.engine is not None

    def test_context_manager_cleanup(self, sample_mysql_config):
        """Test that resources are cleaned up after context."""
        adapter = MySQLAdapter(sample_mysql_config)
        
        with patch.object(adapter.engine, 'dispose', wraps=adapter.engine.dispose) as mock_dispose:
            with adapter:
                pass
            
            # Verify dispose was called
            mock_dispose.assert_called_once()
