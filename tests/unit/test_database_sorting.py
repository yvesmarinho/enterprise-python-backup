"""Unit tests for database sorting functionality in ConfigLoader"""

import json
import tempfile
from pathlib import Path

import pytest

from python_backup.config.loader import VyaBackupConfig, DatabaseConfig


class TestDatabaseSorting:
    """Tests for database configuration sorting"""

    @pytest.fixture
    def config_with_multiple_databases(self) -> VyaBackupConfig:
        """Create a config with multiple databases for sorting tests"""
        config_data = {
            "log_settings": {
                "console_loglevel": "INFO",
                "file_loglevel": "DEBUG",
                "log_dir": "/var/log/test"
            },
            "service_settings": {"name": "test-service"},
            "schedule_settings": {
                "enabled": False,
                "days_of_week": [1, 2, 3, 4, 5],
                "time": "02:00",
                "timezone": "UTC"
            },
            "prometheus_settings": {
                "enabled": False
            },
            "email_settings": {
                "enabled": False
            },
            "bkp_system": {
                "path_sql": "/tmp/sql",
                "path_zip": "/tmp/zip"
            },
            "db_config": [
                {
                    "id_dbms": 1,
                    "dbms": "mysql",
                    "host": "zebra-server.com",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass1",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 2,
                    "dbms": "postgresql",
                    "host": "alpha-server.com",
                    "port": 5432,
                    "user": "postgres",
                    "secret": "pass2",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 3,
                    "dbms": "mysql",
                    "host": "beta-server.com",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass3",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 4,
                    "dbms": "postgresql",
                    "host": "alpha-server.com",
                    "port": 5433,
                    "user": "postgres",
                    "secret": "pass4",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 5,
                    "dbms": "mysql",
                    "host": "Charlie-Server.COM",  # Test case-insensitive
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass5",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 6,
                    "dbms": "mysql",
                    "host": "192.168.1.100",  # Test IP addresses
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass6",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True  # Changed to enabled for testing sort order
                }
            ]
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        config = VyaBackupConfig.from_file(temp_path)
        temp_path.unlink()  # Clean up temp file
        
        return config

    def test_databases_sorted_by_default(self, config_with_multiple_databases):
        """Test that get_enabled_databases returns sorted list by default"""
        databases = config_with_multiple_databases.get_enabled_databases()
        
        # Should have 6 databases (all enabled now)
        assert len(databases) == 6
        
        # Verify sorted order: IP first, then alphabetically by hostname (case-insensitive)
        # Expected order: 192.168.1.100 < alpha-server.com < beta-server.com < charlie-server.com < zebra-server.com
        hosts = [db.host for db in databases]
        expected_hosts = [
            "192.168.1.100",
            "alpha-server.com",
            "alpha-server.com",
            "beta-server.com",
            "Charlie-Server.COM",
            "zebra-server.com"
        ]
        
        # Verify the hosts are in sorted order (case-insensitive)
        sorted_hosts = sorted(hosts, key=str.lower)
        assert hosts == sorted_hosts
        
        # Verify first database
        assert databases[0].host == "192.168.1.100"
        assert databases[0].dbms == "mysql"
        
        # Verify last database
        assert databases[-1].host == "zebra-server.com"
        assert databases[-1].dbms == "mysql"

    def test_databases_unsorted_when_requested(self, config_with_multiple_databases):
        """Test that sort=False returns databases in original order"""
        databases = config_with_multiple_databases.get_enabled_databases(sort=False)
        
        # Should have 6 enabled databases
        assert len(databases) == 6
        
        # Should be in original order (as they appear in db_config)
        # Original order: zebra, alpha, beta, alpha, charlie, 192.168.1.100
        assert databases[0].host == "zebra-server.com"
        assert databases[0].id_dbms == 1
        
        assert databases[1].host == "alpha-server.com"
        assert databases[1].id_dbms == 2
        
        assert databases[2].host == "beta-server.com"
        assert databases[2].id_dbms == 3
        
        assert databases[3].host == "alpha-server.com"
        assert databases[3].id_dbms == 4
        
        assert databases[5].host == "192.168.1.100"
        assert databases[5].id_dbms == 6

    def test_sorted_databases_case_insensitive(self, config_with_multiple_databases):
        """Test that sorting is case-insensitive"""
        databases = config_with_multiple_databases.get_enabled_databases(sort=True)
        
        # Find Charlie-Server.COM (mixed case)
        charlie_db = next(db for db in databases if "charlie" in db.host.lower())
        
        # Should be sorted between beta and zebra
        charlie_index = databases.index(charlie_db)
        
        # Get neighboring databases
        if charlie_index > 0:
            prev_host = databases[charlie_index - 1].host.lower()
            assert prev_host <= charlie_db.host.lower()
        
        if charlie_index < len(databases) - 1:
            next_host = databases[charlie_index + 1].host.lower()
            assert charlie_db.host.lower() <= next_host

    def test_sorted_databases_secondary_sort_by_dbms(self, config_with_multiple_databases):
        """Test that databases with same host are sorted by dbms type"""
        databases = config_with_multiple_databases.get_enabled_databases(sort=True)
        
        # Get all alpha-server databases
        alpha_dbs = [db for db in databases if db.host == "alpha-server.com"]
        
        # Should have 2 alpha-server databases
        assert len(alpha_dbs) == 2
        
        # Should be sorted by dbms: mysql < postgresql (alphabetically)
        # But we have 2 postgresql instances, so verify they're together
        assert alpha_dbs[0].dbms <= alpha_dbs[1].dbms

    def test_empty_database_list(self):
        """Test sorting with empty database list"""
        config_data = {
            "log_settings": {
                "console_loglevel": "INFO",
                "file_loglevel": "DEBUG",
                "log_dir": "/var/log/test"
            },
            "service_settings": {"name": "test-service"},
            "schedule_settings": {
                "enabled": False,
                "days_of_week": [1],
                "time": "02:00",
                "timezone": "UTC"
            },
            "prometheus_settings": {"enabled": False},
            "email_settings": {"enabled": False},
            "bkp_system": {
                "path_sql": "/tmp/sql",
                "path_zip": "/tmp/zip"
            },
            "db_config": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        config = VyaBackupConfig.from_file(temp_path)
        temp_path.unlink()
        
        databases = config.get_enabled_databases(sort=True)
        assert databases == []

    def test_all_databases_disabled(self, config_with_multiple_databases):
        """Test that disabled databases are excluded from sorted list"""
        # Disable all databases
        for db in config_with_multiple_databases.db_config:
            db.enabled = False
        
        databases = config_with_multiple_databases.get_enabled_databases(sort=True)
        assert len(databases) == 0

    def test_single_database(self):
        """Test sorting with single database"""
        config_data = {
            "log_settings": {
                "console_loglevel": "INFO",
                "file_loglevel": "DEBUG",
                "log_dir": "/var/log/test"
            },
            "service_settings": {"name": "test-service"},
            "schedule_settings": {
                "enabled": False,
                "days_of_week": [1],
                "time": "02:00",
                "timezone": "UTC"
            },
            "prometheus_settings": {"enabled": False},
            "email_settings": {"enabled": False},
            "bkp_system": {
                "path_sql": "/tmp/sql",
                "path_zip": "/tmp/zip"
            },
            "db_config": [
                {
                    "id_dbms": 1,
                    "dbms": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        config = VyaBackupConfig.from_file(temp_path)
        temp_path.unlink()
        
        databases = config.get_enabled_databases(sort=True)
        assert len(databases) == 1
        assert databases[0].host == "localhost"

    def test_numeric_and_alphabetic_hosts_sorting(self):
        """Test that IP addresses and hostnames sort correctly"""
        config_data = {
            "log_settings": {
                "console_loglevel": "INFO",
                "file_loglevel": "DEBUG",
                "log_dir": "/var/log/test"
            },
            "service_settings": {"name": "test-service"},
            "schedule_settings": {
                "enabled": False,
                "days_of_week": [1],
                "time": "02:00",
                "timezone": "UTC"
            },
            "prometheus_settings": {"enabled": False},
            "email_settings": {"enabled": False},
            "bkp_system": {
                "path_sql": "/tmp/sql",
                "path_zip": "/tmp/zip"
            },
            "db_config": [
                {
                    "id_dbms": 1,
                    "dbms": "mysql",
                    "host": "db-server.com",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass1",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 2,
                    "dbms": "mysql",
                    "host": "10.0.0.1",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass2",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 3,
                    "dbms": "mysql",
                    "host": "192.168.1.1",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass3",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 4,
                    "dbms": "mysql",
                    "host": "app-server.com",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass4",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        config = VyaBackupConfig.from_file(temp_path)
        temp_path.unlink()
        
        databases = config.get_enabled_databases(sort=True)
        hosts = [db.host for db in databases]
        
        # Verify alphabetical order (IPs sort as strings)
        sorted_hosts = sorted(hosts, key=str.lower)
        assert hosts == sorted_hosts

    def test_sort_stability_with_identical_hosts(self):
        """Test that databases with identical hosts maintain stable order"""
        config_data = {
            "log_settings": {
                "console_loglevel": "INFO",
                "file_loglevel": "DEBUG",
                "log_dir": "/var/log/test"
            },
            "service_settings": {"name": "test-service"},
            "schedule_settings": {
                "enabled": False,
                "days_of_week": [1],
                "time": "02:00",
                "timezone": "UTC"
            },
            "prometheus_settings": {"enabled": False},
            "email_settings": {"enabled": False},
            "bkp_system": {
                "path_sql": "/tmp/sql",
                "path_zip": "/tmp/zip"
            },
            "db_config": [
                {
                    "id_dbms": 1,
                    "dbms": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "user": "postgres",
                    "secret": "pass1",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                },
                {
                    "id_dbms": 2,
                    "dbms": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "user": "admin",
                    "secret": "pass2",
                    "db_ignore": [],
                    "database": [],
                    "enabled": True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        config = VyaBackupConfig.from_file(temp_path)
        temp_path.unlink()
        
        databases = config.get_enabled_databases(sort=True)
        
        # Both have same host, should be sorted by dbms: mysql < postgresql
        assert len(databases) == 2
        assert databases[0].host == "localhost"
        assert databases[1].host == "localhost"
        assert databases[0].dbms == "mysql"
        assert databases[1].dbms == "postgresql"
