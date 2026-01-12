"""
Integration tests for MySQL database connection.

Uses testcontainers to spin up real MySQL instance for testing.
These tests verify actual database connectivity and operations.
"""

import pytest
from testcontainers.mysql import MySqlContainer

from vya_backupbd.config.models import DatabaseConfig
from vya_backupbd.db.mysql import MySQLAdapter


@pytest.fixture(scope="module")
def mysql_container():
    """Start MySQL container for integration tests."""
    container = MySqlContainer("mysql:8.0")
    container.start()
    
    yield container
    
    container.stop()


@pytest.fixture(scope="module")
def mysql_config(mysql_container):
    """Create DatabaseConfig from running container."""
    return DatabaseConfig(
        id="test-mysql-integration",
        type="mysql",
        host=mysql_container.get_container_host_ip(),
        port=int(mysql_container.get_exposed_port(3306)),
        username=mysql_container.username,
        password=mysql_container.password,
        database=mysql_container.dbname,
        exclude_databases=["information_schema", "mysql", "performance_schema", "sys"]
    )


class TestMySQLRealConnection:
    """Test real MySQL connection using testcontainers."""

    def test_container_is_running(self, mysql_container):
        """Verify MySQL container is running."""
        assert mysql_container.get_container_host_ip() is not None
        assert mysql_container.get_exposed_port(3306) is not None

    def test_connection_successful(self, mysql_config):
        """Test successful connection to real MySQL."""
        adapter = MySQLAdapter(mysql_config)
        
        with adapter:
            result = adapter.test_connection()
            assert result is True

    def test_get_databases_real(self, mysql_config):
        """Test getting databases from real MySQL."""
        adapter = MySQLAdapter(mysql_config)
        
        with adapter:
            databases = adapter.get_databases()
            
            # Should return at least the test database
            assert isinstance(databases, list)
            assert len(databases) >= 1
            assert mysql_config.database in databases
            
            # System databases should be filtered out
            assert "information_schema" not in databases
            assert "mysql" not in databases

    def test_create_and_query_table(self, mysql_config):
        """Test creating table and querying data."""
        adapter = MySQLAdapter(mysql_config)
        
        with adapter:
            # Create test table
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INT PRIMARY KEY, name VARCHAR(50))"))
                conn.execute(text("INSERT INTO test_table VALUES (1, 'test')"))
                conn.commit()
                
                # Query data
                result = conn.execute(text("SELECT * FROM test_table"))
                rows = result.fetchall()
                
                assert len(rows) == 1
                assert rows[0][0] == 1
                assert rows[0][1] == "test"
                
                # Cleanup
                conn.execute(text("DROP TABLE test_table"))
                conn.commit()

    def test_backup_command_generation(self, mysql_config):
        """Test backup command generation with real config."""
        adapter = MySQLAdapter(mysql_config)
        
        command = adapter.get_backup_command(mysql_config.database, "/tmp/test.sql")
        
        assert "mysqldump" in command
        assert mysql_config.database in command
        assert f"--port={mysql_config.port}" in command or f"-P {mysql_config.port}" in command
        assert "--single-transaction" in command

    def test_connection_pool_works(self, mysql_config):
        """Test that connection pooling works correctly."""
        adapter = MySQLAdapter(mysql_config)
        
        with adapter:
            # Make multiple queries to test pool
            for i in range(5):
                result = adapter.test_connection()
                assert result is True
            
            # Verify pool is working
            assert adapter.engine.pool.size() > 0


class TestMySQLErrorHandling:
    """Test error handling with real MySQL."""

    def test_invalid_credentials(self, mysql_container):
        """Test handling of invalid credentials."""
        config = DatabaseConfig(
            id="test-invalid",
            type="mysql",
            host=mysql_container.get_container_host_ip(),
            port=int(mysql_container.get_exposed_port(3306)),
            username="invalid_user",
            password="wrong_password",
            database="testdb"
        )
        
        adapter = MySQLAdapter(config)
        
        with adapter:
            result = adapter.test_connection()
            # Should fail gracefully
            assert result is False

    def test_invalid_database(self, mysql_config):
        """Test querying non-existent database."""
        # MySQL doesn't allow connection to non-existent database
        # So we test that get_databases works and doesn't include it
        adapter = MySQLAdapter(mysql_config)
        
        with adapter:
            # Get all databases
            databases = adapter.get_databases()
            assert isinstance(databases, list)
            # Verify a random non-existent database is not in the list
            assert "nonexistent_db_12345" not in databases
            assert "fake_database_xyz" not in databases


class TestMySQLBackupRestore:
    """Test backup and restore operations with real MySQL."""

    def test_backup_creates_file(self, mysql_config, tmp_path):
        """Test that backup creates output file."""
        adapter = MySQLAdapter(mysql_config)
        output_file = tmp_path / "test_backup.sql"
        
        with adapter:
            # Create test data
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS backup_test (id INT)"))
                conn.execute(text("INSERT INTO backup_test VALUES (1), (2), (3)"))
                conn.commit()
            
            # Perform backup
            result = adapter.backup_database(mysql_config.database, str(output_file))
            
            # Verify backup succeeded
            assert result is True
            assert output_file.exists()
            assert output_file.stat().st_size > 0
            
            # Verify backup contains our table
            content = output_file.read_text()
            assert "backup_test" in content
            
            # Cleanup
            with adapter.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS backup_test"))
                conn.commit()

    def test_backup_multiple_tables(self, mysql_config, tmp_path):
        """Test backing up database with multiple tables."""
        adapter = MySQLAdapter(mysql_config)
        output_file = tmp_path / "multi_table_backup.sql"
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                # Create multiple tables
                conn.execute(text("CREATE TABLE IF NOT EXISTS table1 (id INT)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS table2 (name VARCHAR(50))"))
                conn.execute(text("INSERT INTO table1 VALUES (1), (2)"))
                conn.execute(text("INSERT INTO table2 VALUES ('test1'), ('test2')"))
                conn.commit()
            
            # Backup
            result = adapter.backup_database(mysql_config.database, str(output_file))
            
            assert result is True
            assert output_file.exists()
            
            # Verify both tables are in backup
            content = output_file.read_text()
            assert "table1" in content
            assert "table2" in content
            
            # Cleanup
            with adapter.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS table1"))
                conn.execute(text("DROP TABLE IF EXISTS table2"))
                conn.commit()
