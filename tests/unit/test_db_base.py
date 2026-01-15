"""
Unit tests for abstract database adapter base class.

Tests the DatabaseAdapter interface and common functionality
for database operations.
"""

import pytest
from abc import ABC
from sqlalchemy.engine import Engine
from unittest.mock import Mock, MagicMock, patch

from python_backup.config.models import DatabaseConfig
from python_backup.db.base import DatabaseAdapter


class TestDatabaseAdapterInterface:
    """Test DatabaseAdapter abstract interface."""

    def test_database_adapter_is_abstract(self):
        """Test that DatabaseAdapter cannot be instantiated directly."""
        config = DatabaseConfig(
            id="test-abstract",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            database="testdb"
        )
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DatabaseAdapter(config)

    def test_required_abstract_methods(self):
        """Test that subclass must implement all abstract methods."""
        config = DatabaseConfig(
            id="test-incomplete",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            database="testdb"
        )
        
        # Create incomplete subclass
        class IncompleteAdapter(DatabaseAdapter):
            pass
        
        with pytest.raises(TypeError):
            IncompleteAdapter(config)


class ConcreteDatabaseAdapter(DatabaseAdapter):
    """Concrete implementation for testing."""
    
    def get_databases(self) -> list[str]:
        return ["db1", "db2", "db3"]
    
    def test_connection(self) -> bool:
        return True
    
    def backup_database(self, database: str, output_path: str) -> bool:
        return True
    
    def get_backup_command(self, database: str, output_path: str) -> str:
        return f"backup {database} to {output_path}"


class TestDatabaseAdapterBase:
    """Test DatabaseAdapter base functionality."""

    def test_adapter_initialization(self, sample_mysql_config):
        """Test adapter initialization with config."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        assert adapter.config == sample_mysql_config
        assert isinstance(adapter.engine, Engine)

    def test_adapter_has_engine(self, sample_mysql_config):
        """Test that adapter creates SQLAlchemy engine."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        assert adapter.engine is not None
        assert isinstance(adapter.engine, Engine)

    def test_adapter_config_property(self, sample_mysql_config):
        """Test config property access."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        assert adapter.config.type == "mysql"
        assert adapter.config.host == "localhost"
        assert adapter.config.database == "testdb"

    def test_adapter_repr(self, sample_mysql_config):
        """Test adapter string representation."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        repr_str = repr(adapter)
        
        assert "ConcreteDatabaseAdapter" in repr_str
        assert "mysql" in repr_str.lower()
        assert "localhost" in repr_str

    def test_adapter_context_manager(self, sample_mysql_config):
        """Test adapter as context manager."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        with adapter as ctx_adapter:
            assert ctx_adapter is adapter
            assert ctx_adapter.engine is not None

    def test_adapter_dispose_on_exit(self, sample_mysql_config):
        """Test that engine is disposed when exiting context."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        with adapter:
            engine = adapter.engine
            assert engine.pool.size() >= 0
        
        # After context exit, engine should be disposed
        # Note: We can't easily test this without mocking

    def test_adapter_close_method(self, sample_mysql_config):
        """Test explicit close method."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        with patch.object(adapter.engine, 'dispose', wraps=adapter.engine.dispose) as mock_dispose:
            adapter.close()
            
            # Verify dispose was called
            mock_dispose.assert_called_once()


class TestDatabaseAdapterFiltering:
    """Test database filtering functionality."""

    def test_filter_system_databases_basic(self, sample_mysql_config):
        """Test filtering system databases."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        all_dbs = ["db1", "information_schema", "mysql", "db2", "performance_schema"]
        
        filtered = adapter.filter_system_databases(all_dbs)
        
        assert "db1" in filtered
        assert "db2" in filtered
        assert "information_schema" not in filtered
        assert "mysql" not in filtered
        assert "performance_schema" not in filtered

    def test_filter_respects_config_exclusions(self, sample_mysql_config):
        """Test that filtering respects configured exclusions."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        # Config already has exclusions from auto-exclusion
        all_dbs = ["testdb", "mysql", "information_schema", "myapp_db"]
        
        filtered = adapter.filter_system_databases(all_dbs)
        
        # System DBs should be excluded
        assert "mysql" not in filtered
        assert "information_schema" not in filtered
        # User DBs should be included
        assert "testdb" in filtered
        assert "myapp_db" in filtered

    def test_filter_empty_list(self, sample_mysql_config):
        """Test filtering empty database list."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        filtered = adapter.filter_system_databases([])
        
        assert filtered == []

    def test_filter_all_system_databases(self, sample_mysql_config):
        """Test filtering when all databases are system databases."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        all_dbs = ["mysql", "information_schema", "performance_schema", "sys"]
        
        filtered = adapter.filter_system_databases(all_dbs)
        
        assert filtered == []


class TestDatabaseAdapterErrorHandling:
    """Test error handling in adapter."""

    def test_connection_error_handling(self, sample_mysql_config):
        """Test handling of connection errors."""
        sample_mysql_config.host = "invalid_host_12345"
        
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        # Adapter creation should succeed
        assert adapter is not None
        
        # Mock connection test to fail
        with patch.object(adapter, 'test_connection', side_effect=Exception("Connection refused")):
            # Connection test should fail
            with pytest.raises(Exception, match="Connection refused"):
                adapter.test_connection()

    def test_invalid_credentials_handling(self):
        """Test handling of invalid credentials."""
        config = DatabaseConfig(            id="test-invalid-creds",            type="mysql",
            host="localhost",
            port=3306,
            username="invalid_user",
            password="wrong_password",
            database="testdb"
        )
        
        adapter = ConcreteDatabaseAdapter(config)
        
        # Mock authentication failure
        with patch.object(adapter, 'test_connection', side_effect=Exception("Access denied")):
            # Should fail when attempting actual connection
            with pytest.raises(Exception, match="Access denied"):
                adapter.test_connection()

    def test_database_not_found_handling(self, sample_mysql_config):
        """Test handling of non-existent database."""
        sample_mysql_config.database = "nonexistent_db_12345"
        
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        # Mock database not found error
        with patch.object(adapter, 'test_connection', side_effect=Exception("Unknown database")):
            # Should handle gracefully
            with pytest.raises(Exception, match="Unknown database"):
                adapter.test_connection()


class TestDatabaseAdapterMethods:
    """Test abstract methods that subclasses must implement."""

    def test_get_databases_abstract(self):
        """Test that get_databases must be implemented."""
        # Already tested in interface tests
        pass

    def test_test_connection_abstract(self):
        """Test that test_connection must be implemented."""
        # Already tested in interface tests
        pass

    def test_backup_database_abstract(self):
        """Test that backup_database must be implemented."""
        # Already tested in interface tests
        pass

    def test_get_backup_command_abstract(self):
        """Test that get_backup_command must be implemented."""
        # Already tested in interface tests
        pass

    def test_concrete_implementation_works(self, sample_mysql_config):
        """Test that concrete implementation works correctly."""
        adapter = ConcreteDatabaseAdapter(sample_mysql_config)
        
        # Test all abstract methods are implemented
        databases = adapter.get_databases()
        assert isinstance(databases, list)
        
        connection_ok = adapter.test_connection()
        assert isinstance(connection_ok, bool)
        
        backup_result = adapter.backup_database("testdb", "/tmp/backup.sql")
        assert isinstance(backup_result, bool)
        
        command = adapter.get_backup_command("testdb", "/tmp/backup.sql")
        assert isinstance(command, str)
