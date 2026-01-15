"""Unit tests for configuration module"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from python_backup.config import (
    AppConfig,
    DatabaseConfig,
    LoggingConfig,
    RetentionConfig,
    StorageConfig,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig model"""

    def test_valid_mysql_config(self) -> None:
        """Test valid MySQL configuration"""
        config = DatabaseConfig(
            id="test-mysql",
            type="mysql",
            host="localhost",
            port=3306,
            username="testuser",
            password="testpass",
        )
        assert config.id == "test-mysql"
        assert config.type == "mysql"
        assert config.enabled is True
        # Should auto-add MySQL system databases
        assert "mysql" in config.exclude_databases
        assert "information_schema" in config.exclude_databases

    def test_valid_postgresql_config(self) -> None:
        """Test valid PostgreSQL configuration"""
        config = DatabaseConfig(
            id="test-pg",
            type="postgresql",
            host="localhost",
            port=5432,
            username="testuser",
            password="testpass",
        )
        assert config.type == "postgresql"
        # Should auto-add PostgreSQL system databases
        assert "postgres" in config.exclude_databases
        assert "template0" in config.exclude_databases

    def test_invalid_port(self) -> None:
        """Test invalid port number"""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                id="test",
                type="mysql",
                host="localhost",
                port=99999,  # Invalid port
                username="testuser",
                password="testpass",
            )

    def test_custom_exclude_databases(self) -> None:
        """Test custom exclude databases with system databases"""
        config = DatabaseConfig(
            id="test",
            type="mysql",
            host="localhost",
            port=3306,
            username="testuser",
            password="testpass",
            exclude_databases=["custom_db"],
        )
        # Should have both custom and system databases
        assert "custom_db" in config.exclude_databases
        assert "mysql" in config.exclude_databases


class TestStorageConfig:
    """Tests for StorageConfig model"""

    def test_default_storage_config(self) -> None:
        """Test default storage configuration"""
        config = StorageConfig()
        assert config.base_path == Path("/var/backups/vya_backupdb")
        assert config.compression_level == 6
        assert config.checksum_algorithm == "sha256"

    def test_custom_storage_config(self) -> None:
        """Test custom storage configuration"""
        config = StorageConfig(
            base_path="/custom/path",
            compression_level=9,
            checksum_algorithm="md5",
        )
        assert config.base_path == Path("/custom/path")
        assert config.compression_level == 9
        assert config.checksum_algorithm == "md5"

    def test_invalid_compression_level(self) -> None:
        """Test invalid compression level"""
        with pytest.raises(ValidationError):
            StorageConfig(compression_level=10)


class TestRetentionConfig:
    """Tests for RetentionConfig model"""

    def test_default_gfs_retention(self) -> None:
        """Test default GFS retention policy"""
        config = RetentionConfig()
        assert config.strategy == "gfs"
        assert config.daily_keep == 7
        assert config.weekly_keep == 4
        assert config.monthly_keep == 12
        assert config.cleanup_enabled is True


class TestLoggingConfig:
    """Tests for LoggingConfig model"""

    def test_default_logging_config(self) -> None:
        """Test default logging configuration"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.output == "file"


class TestAppConfig:
    """Tests for AppConfig model"""

    def test_valid_app_config(self, sample_config_dict: dict) -> None:
        """Test valid application configuration"""
        config = AppConfig(**sample_config_dict)
        assert config.application_name == "vya-backupdb"
        assert config.version == "2.0.0"
        assert len(config.databases) == 1
        assert config.databases[0].id == "test-mysql-01"

    def test_missing_required_field(self) -> None:
        """Test missing required field (databases)"""
        with pytest.raises(ValidationError):
            AppConfig(
                application_name="test",
                version="1.0.0",
                # Missing required 'databases' field
            )

    def test_from_yaml(self, tmp_config_dir: Path, sample_config_dict: dict) -> None:
        """Test loading configuration from YAML file"""
        yaml_path = tmp_config_dir / "config.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(sample_config_dict, f)

        config = AppConfig.from_yaml(yaml_path)
        assert config.application_name == "vya-backupdb"
        assert len(config.databases) == 1

    def test_environment_values(self) -> None:
        """Test different environment values"""
        for env in ["dev", "staging", "production"]:
            config = AppConfig(
                environment=env,
                databases=[
                    {
                        "id": "test",
                        "type": "mysql",
                        "host": "localhost",
                        "port": 3306,
                        "username": "testuser",
                        "password": "testpass",
                        "database": "testdb",
                    }
                ],
            )
            assert config.environment == env
