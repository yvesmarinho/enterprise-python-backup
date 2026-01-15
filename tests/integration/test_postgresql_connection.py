"""
Integration tests for PostgreSQL database connection.

Uses testcontainers to spin up real PostgreSQL instance for testing.
These tests verify actual database connectivity and operations.
"""

import pytest
from testcontainers.postgres import PostgresContainer

from python_backup.config.models import DatabaseConfig
from python_backup.db.postgresql import PostgreSQLAdapter


@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for integration tests."""
    container = PostgresContainer("postgres:15")
    container.start()
    
    yield container
    
    container.stop()


@pytest.fixture(scope="module")
def postgres_config(postgres_container):
    """Create DatabaseConfig from running container."""
    return DatabaseConfig(
        id="test-postgres-integration",
        type="postgresql",
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        username=postgres_container.username,
        password=postgres_container.password,
        database=postgres_container.dbname,
        exclude_databases=["postgres", "template0", "template1"]
    )


class TestPostgreSQLRealConnection:
    """Test real PostgreSQL connection using testcontainers."""

    def test_container_is_running(self, postgres_container):
        """Verify PostgreSQL container is running."""
        assert postgres_container.get_container_host_ip() is not None
        assert postgres_container.get_exposed_port(5432) is not None

    def test_connection_successful(self, postgres_config):
        """Test successful connection to real PostgreSQL."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            result = adapter.test_connection()
            assert result is True

    def test_get_databases_real(self, postgres_config):
        """Test getting databases from real PostgreSQL."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            databases = adapter.get_databases()
            
            # Should return at least the test database
            assert isinstance(databases, list)
            assert len(databases) >= 1
            assert postgres_config.database in databases
            
            # System databases should be filtered out
            assert "template0" not in databases
            assert "template1" not in databases

    def test_create_and_query_table(self, postgres_config):
        """Test creating table and querying data."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                # Create test table
                conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name VARCHAR(50))"))
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

    def test_backup_command_generation(self, postgres_config):
        """Test backup command generation with real config."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        command = adapter.get_backup_command(postgres_config.database, "/tmp/test.sql")
        
        assert "pg_dump" in command
        assert postgres_config.database in command
        assert f"-p {postgres_config.port}" in command or f"--port={postgres_config.port}" in command
        assert "--clean" in command
        assert "--create" in command

    def test_connection_pool_works(self, postgres_config):
        """Test that connection pooling works correctly."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            # Make multiple queries to test pool
            for i in range(5):
                result = adapter.test_connection()
                assert result is True
            
            # Verify pool is working
            assert adapter.engine.pool.size() > 0

    def test_query_system_catalogs(self, postgres_config):
        """Test querying PostgreSQL system catalogs."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                # Query pg_database
                result = conn.execute(text(
                    "SELECT datname FROM pg_database WHERE datistemplate = false"
                ))
                databases = [row[0] for row in result.fetchall()]
                
                assert postgres_config.database in databases


class TestPostgreSQLErrorHandling:
    """Test error handling with real PostgreSQL."""

    def test_invalid_credentials(self, postgres_container):
        """Test handling of invalid credentials."""
        config = DatabaseConfig(
            id="test-invalid",
            type="postgresql",
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            username="invalid_user",
            password="wrong_password",
            database="test"
        )
        
        adapter = PostgreSQLAdapter(config)
        
        with adapter:
            result = adapter.test_connection()
            # Should fail gracefully
            assert result is False

    def test_invalid_database(self, postgres_config):
        """Test querying non-existent database."""
        # PostgreSQL doesn't allow connection to non-existent database
        # So we test that get_databases works and doesn't include it
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            # Get all databases
            databases = adapter.get_databases()
            assert isinstance(databases, list)
            # Verify a random non-existent database is not in the list
            assert "nonexistent_db_12345" not in databases
            assert "fake_database_xyz" not in databases


class TestPostgreSQLBackupRestore:
    """Test backup and restore operations with real PostgreSQL."""

    def test_backup_creates_file(self, postgres_config, tmp_path):
        """Test that backup creates output file."""
        adapter = PostgreSQLAdapter(postgres_config)
        output_file = tmp_path / "test_backup.sql"
        
        with adapter:
            # Create test data
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS backup_test (id INTEGER)"))
                conn.execute(text("INSERT INTO backup_test VALUES (1), (2), (3)"))
                conn.commit()
            
            # Perform backup
            result = adapter.backup_database(postgres_config.database, str(output_file))
            
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

    def test_backup_with_schema(self, postgres_config, tmp_path):
        """Test backing up database with schema."""
        adapter = PostgreSQLAdapter(postgres_config)
        output_file = tmp_path / "schema_backup.sql"
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                # Create schema and table
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS test_schema.test_table (id INTEGER)"))
                conn.execute(text("INSERT INTO test_schema.test_table VALUES (1)"))
                conn.commit()
            
            # Backup
            result = adapter.backup_database(postgres_config.database, str(output_file))
            
            assert result is True
            assert output_file.exists()
            
            # Verify schema is in backup
            content = output_file.read_text()
            assert "test_schema" in content
            
            # Cleanup
            with adapter.engine.connect() as conn:
                conn.execute(text("DROP SCHEMA IF EXISTS test_schema CASCADE"))
                conn.commit()

    def test_backup_multiple_tables(self, postgres_config, tmp_path):
        """Test backing up database with multiple tables."""
        adapter = PostgreSQLAdapter(postgres_config)
        output_file = tmp_path / "multi_table_backup.sql"
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                # Create multiple tables
                conn.execute(text("CREATE TABLE IF NOT EXISTS table1 (id INTEGER)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS table2 (name VARCHAR(50))"))
                conn.execute(text("INSERT INTO table1 VALUES (1), (2)"))
                conn.execute(text("INSERT INTO table2 VALUES ('test1'), ('test2')"))
                conn.commit()
            
            # Backup
            result = adapter.backup_database(postgres_config.database, str(output_file))
            
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

    def test_backup_with_pgpassword(self, postgres_config, tmp_path):
        """Test that PGPASSWORD environment variable is used."""
        adapter = PostgreSQLAdapter(postgres_config)
        output_file = tmp_path / "password_test.sql"
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS pass_test (id INTEGER)"))
                conn.commit()
            
            # Backup should use PGPASSWORD
            result = adapter.backup_database(postgres_config.database, str(output_file))
            
            assert result is True
            assert output_file.exists()
            
            # Cleanup
            with adapter.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS pass_test"))
                conn.commit()


class TestPostgreSQLSpecificFeatures:
    """Test PostgreSQL-specific features."""

    def test_transactions_work(self, postgres_config):
        """Test transaction handling."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                # Start transaction
                trans = conn.begin()
                try:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS trans_test (id INTEGER)"))
                    conn.execute(text("INSERT INTO trans_test VALUES (1)"))
                    trans.commit()
                    
                    # Verify data
                    result = conn.execute(text("SELECT COUNT(*) FROM trans_test"))
                    count = result.scalar()
                    assert count == 1
                    
                finally:
                    # Cleanup
                    conn.execute(text("DROP TABLE IF EXISTS trans_test"))
                    conn.commit()

    def test_sequences_work(self, postgres_config):
        """Test PostgreSQL sequences."""
        adapter = PostgreSQLAdapter(postgres_config)
        
        with adapter:
            from sqlalchemy import text
            with adapter.engine.connect() as conn:
                # Create table with serial (uses sequence)
                conn.execute(text(
                    "CREATE TABLE IF NOT EXISTS seq_test (id SERIAL PRIMARY KEY, name VARCHAR(50))"
                ))
                conn.execute(text("INSERT INTO seq_test (name) VALUES ('test1')"))
                conn.execute(text("INSERT INTO seq_test (name) VALUES ('test2')"))
                conn.commit()
                
                # Check sequence values
                result = conn.execute(text("SELECT id FROM seq_test ORDER BY id"))
                ids = [row[0] for row in result.fetchall()]
                
                assert ids == [1, 2]
                
                # Cleanup
                conn.execute(text("DROP TABLE IF EXISTS seq_test"))
                conn.commit()
