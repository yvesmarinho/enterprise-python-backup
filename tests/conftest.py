"""Pytest configuration and fixtures"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def tmp_config_dir() -> Generator[Path, None, None]:
    """Create temporary directory for config files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tmp_backup_dir() -> Generator[Path, None, None]:
    """Create temporary directory for backup files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dict() -> dict:
    """Sample configuration dictionary"""
    return {
        "application_name": "vya-backupdb",
        "version": "2.0.0",
        "environment": "dev",
        "databases": [
            {
                "id": "test-mysql-01",
                "type": "mysql",
                "host": "localhost",
                "port": 3306,
                "username": "testuser",
                "password": "testpass",
                "database": "testdb",
                "enabled": True,
                "exclude_databases": [],
                "ssl": False,
                "ssl_enabled": False,
            }
        ],
        "storage": {
            "base_path": "/tmp/backups",
            "structure": "{hostname}/{db_id}/{db_name}/{date}",
            "compression_level": 6,
            "checksum_algorithm": "sha256",
        },
        "retention": {
            "strategy": "gfs",
            "daily_keep": 7,
            "weekly_keep": 4,
            "monthly_keep": 12,
            "cleanup_enabled": True,
        },
        "logging": {
            "level": "INFO",
            "format": "json",
            "output": "console",
            "file_path": "/tmp/app.log",
        },
    }


@pytest.fixture
def sample_mysql_config():
    """Sample MySQL database configuration."""
    from python_backup.config.models import DatabaseConfig
    
    return DatabaseConfig(
        id="test-mysql-01",
        type="mysql",
        host="localhost",
        port=3306,
        username="testuser",
        password="testpass",
        database="testdb",
        ssl=False,
        ssl_enabled=False
    )


@pytest.fixture
def sample_postgresql_config():
    """Sample PostgreSQL database configuration."""
    from python_backup.config.models import DatabaseConfig
    
    return DatabaseConfig(
        id="test-pg-01",
        type="postgresql",
        host="localhost",
        port=5432,
        username="testuser",
        password="testpass",
        database="testdb",
        ssl=False,
        ssl_enabled=False
    )

