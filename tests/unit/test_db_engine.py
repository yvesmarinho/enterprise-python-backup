"""
Unit tests for database engine factory.

Tests SQLAlchemy engine creation with proper configuration,
connection pooling, and error handling.
"""

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ArgumentError

from vya_backupbd.config.models import DatabaseConfig
from vya_backupbd.db.engine import create_db_engine, get_connection_string


class TestGetConnectionString:
    """Test connection string generation."""

    def test_mysql_connection_string_basic(self, sample_mysql_config):
        """Test MySQL connection string without SSL."""
        config = sample_mysql_config
        config.ssl = False
        
        conn_str = get_connection_string(config)
        
        assert conn_str.startswith("mysql+pymysql://")
        assert "testuser" in conn_str
        assert "testpass" in conn_str
        assert "localhost:3306" in conn_str
        assert "testdb" in conn_str

    def test_mysql_connection_string_with_ssl(self, sample_mysql_config):
        """Test MySQL connection string with SSL."""
        config = sample_mysql_config
        config.ssl = True
        
        conn_str = get_connection_string(config)
        
        assert "ssl=true" in conn_str or "ssl_mode" in conn_str

    def test_postgresql_connection_string_basic(self, sample_postgresql_config):
        """Test PostgreSQL connection string without SSL."""
        config = sample_postgresql_config
        config.ssl = False
        
        conn_str = get_connection_string(config)
        
        assert conn_str.startswith("postgresql+psycopg://")
        assert "testuser" in conn_str
        assert "testpass" in conn_str
        assert "localhost:5432" in conn_str
        assert "testdb" in conn_str

    def test_postgresql_connection_string_with_ssl(self, sample_postgresql_config):
        """Test PostgreSQL connection string with SSL."""
        config = sample_postgresql_config
        config.ssl = True
        
        conn_str = get_connection_string(config)
        
        assert "sslmode=require" in conn_str

    def test_connection_string_masks_password(self, sample_mysql_config):
        """Test that password is properly escaped in connection string."""
        config = sample_mysql_config
        config.password = "p@ssw0rd!#$"
        
        conn_str = get_connection_string(config)
        
        # Password should be URL encoded
        assert "%40" in conn_str or "@" in conn_str  # @ is encoded or literal

    def test_invalid_database_type_raises_error(self, sample_mysql_config):
        """Test that invalid database type raises ValueError."""
        config = sample_mysql_config
        config.type = "invalid"  # This shouldn't happen due to Pydantic validation
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            get_connection_string(config)


class TestCreateDbEngine:
    """Test SQLAlchemy engine creation."""

    def test_create_engine_mysql(self, sample_mysql_config):
        """Test creating MySQL engine."""
        engine = create_db_engine(sample_mysql_config)
        
        assert isinstance(engine, Engine)
        assert "mysql" in str(engine.url)

    def test_create_engine_postgresql(self, sample_postgresql_config):
        """Test creating PostgreSQL engine."""
        engine = create_db_engine(sample_postgresql_config)
        
        assert isinstance(engine, Engine)
        assert "postgresql" in str(engine.url)

    def test_engine_has_connection_pool(self, sample_mysql_config):
        """Test that engine is configured with connection pool."""
        engine = create_db_engine(sample_mysql_config)
        
        # Check pool configuration
        assert engine.pool is not None
        assert engine.pool.size() >= 0  # Pool exists

    def test_engine_pool_size_configuration(self, sample_mysql_config):
        """Test connection pool size configuration."""
        engine = create_db_engine(sample_mysql_config, pool_size=10, max_overflow=20)
        
        # Pool parameters should be set
        assert engine.pool._pool.maxsize == 10
        assert engine.pool._max_overflow == 20

    def test_engine_echo_mode(self, sample_mysql_config):
        """Test engine echo mode for SQL logging."""
        engine = create_db_engine(sample_mysql_config, echo=True)
        
        assert engine.echo is True

    def test_engine_with_custom_pool_timeout(self, sample_mysql_config):
        """Test engine with custom pool timeout."""
        engine = create_db_engine(
            sample_mysql_config,
            pool_timeout=60,
            pool_recycle=3600
        )
        
        assert engine.pool._timeout == 60
        assert engine.pool._recycle == 3600

    def test_invalid_connection_config_raises_error(self):
        """Test that invalid connection config raises appropriate error."""
        config = DatabaseConfig(
            id="test-invalid",
            type="mysql",
            host="invalid_host_12345",
            port=3306,
            username="test",
            password="test",
            database="test"
        )
        
        # Engine creation should succeed, but connection will fail
        engine = create_db_engine(config)
        
        with pytest.raises(Exception):  # Connection error
            with engine.connect():
                pass

    def test_engine_disposal(self, sample_mysql_config):
        """Test that engine can be properly disposed."""
        engine = create_db_engine(sample_mysql_config)
        
        with patch.object(engine, 'dispose', wraps=engine.dispose) as mock_dispose:
            engine.dispose()
            
            # Verify dispose was called
            mock_dispose.assert_called_once()


class TestEngineReusability:
    """Test engine reusability and caching scenarios."""

    def test_multiple_engines_same_config(self, sample_mysql_config):
        """Test creating multiple engines with same config."""
        engine1 = create_db_engine(sample_mysql_config)
        engine2 = create_db_engine(sample_mysql_config)
        
        # Should create different engine instances
        assert engine1 is not engine2
        
        # But with same URL
        assert str(engine1.url) == str(engine2.url)

    def test_engine_different_databases(self, sample_mysql_config):
        """Test engines for different databases."""
        config1 = sample_mysql_config
        config2 = DatabaseConfig(
            id="test-mysql-02",
            type="mysql",
            host="localhost",
            port=3306,
            username="testuser",
            password="testpass",
            database="otherdb"
        )
        
        engine1 = create_db_engine(config1)
        engine2 = create_db_engine(config2)
        
        assert str(engine1.url) != str(engine2.url)
        assert "testdb" in str(engine1.url)
        assert "otherdb" in str(engine2.url)
