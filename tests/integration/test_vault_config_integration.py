"""
Integration tests for VaultManager + ConfigLoader integration.

Tests the priority system: Vault as primary source, JSON as fallback.
"""

import json
import tempfile
from pathlib import Path

import pytest

from python_backup.config.loader import VyaBackupConfig
from python_backup.security.vault import VaultManager


@pytest.fixture
def temp_vault_path():
    """Create a temporary vault file path."""
    with tempfile.NamedTemporaryFile(
        suffix=".json.enc", delete=False
    ) as f:
        vault_path = Path(f.name)
    yield vault_path
    # Cleanup
    if vault_path.exists():
        vault_path.unlink()


@pytest.fixture
def sample_config_json():
    """Create a sample config JSON with database credentials."""
    return {
        "log_settings": {
            "console_loglevel": "INFO",
            "file_loglevel": "DEBUG",
            "log_dir": "/tmp/logs",
        },
        "service_settings": {"service_name": "test"},
        "schedule_settings": {
            "enabled": False,
            "days_of_week": [1, 2, 3],
            "time": "02:00",
            "timezone": "UTC",
        },
        "prometheus_settings": {"enabled": False},
        "email_settings": {
            "enabled": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "json_user@example.com",
            "smtp_password": "json_smtp_pass",
            "use_ssl": False,
            "use_tls": True,
            "from_email": "backup@example.com",
            "success_recipients": ["admin@example.com"],
            "failure_recipients": ["admin@example.com"],
            "test_mode": False,
        },
        "db_config": [
            {
                "id_dbms": 1,
                "dbms": "mysql",
                "host": "mysql.example.com",
                "port": 3306,
                "user": "json_mysql_user",
                "secret": "json_mysql_pass",
                "db_ignore": ["sys", "tmp"],
                "database": [],
                "enabled": True,
            },
            {
                "id_dbms": 2,
                "dbms": "postgresql",
                "host": "postgres.example.com",
                "port": 5432,
                "user": "json_pg_user",
                "secret": "json_pg_pass",
                "db_ignore": ["template0"],
                "database": [],
                "enabled": True,
            },
        ],
        "bkp_system": {
            "path_sql": "/tmp/sql",
            "path_zip": "/tmp/zip",
            "path_files": "/tmp/files",
            "retention_files": 7,
        },
    }


@pytest.fixture
def temp_config_file(sample_config_json):
    """Create a temporary config JSON file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(sample_config_json, f, indent=2)
        config_path = Path(f.name)
    yield config_path
    # Cleanup
    if config_path.exists():
        config_path.unlink()


class TestVaultConfigIntegration:
    """Test Vault + ConfigLoader integration."""

    def test_load_config_without_vault(self, temp_config_file):
        """Test loading config without vault (JSON fallback only)."""
        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=None
        )

        # Should use JSON credentials
        assert len(config.db_config) == 2
        assert config.db_config[0].user == "json_mysql_user"
        assert config.db_config[0].secret == "json_mysql_pass"
        assert config.db_config[1].user == "json_pg_user"
        assert config.db_config[1].secret == "json_pg_pass"

        # Email settings should use JSON
        assert config.email_settings.smtp_user == "json_user@example.com"
        assert config.email_settings.smtp_password == "json_smtp_pass"

    def test_load_config_with_vault_priority(
        self, temp_config_file, temp_vault_path
    ):
        """Test Vault has priority over JSON for credentials."""
        # Setup vault with database credentials
        vault = VaultManager(temp_vault_path)
        vault.set("db_1", "vault_mysql_user", "vault_mysql_pass")
        vault.set("smtp", "vault_smtp@example.com", "vault_smtp_pass")
        vault.save()

        # Load config with vault
        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=temp_vault_path
        )

        # Database 1 should use vault credentials
        assert config.db_config[0].user == "vault_mysql_user"
        assert config.db_config[0].secret == "vault_mysql_pass"

        # Database 2 should use JSON fallback (not in vault)
        assert config.db_config[1].user == "json_pg_user"
        assert config.db_config[1].secret == "json_pg_pass"

        # Email should use vault credentials
        assert config.email_settings.smtp_user == "vault_smtp@example.com"
        assert config.email_settings.smtp_password == "vault_smtp_pass"

    def test_load_config_vault_fallback_to_json(
        self, temp_config_file, temp_vault_path
    ):
        """Test fallback to JSON when vault doesn't have credential."""
        # Create empty vault
        vault = VaultManager(temp_vault_path)
        vault.save()

        # Load config with empty vault
        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=temp_vault_path
        )

        # Should fall back to JSON for all credentials
        assert config.db_config[0].user == "json_mysql_user"
        assert config.db_config[0].secret == "json_mysql_pass"
        assert config.email_settings.smtp_user == "json_user@example.com"
        assert config.email_settings.smtp_password == "json_smtp_pass"

    def test_vault_manager_reference_stored(
        self, temp_config_file, temp_vault_path
    ):
        """Test that VaultManager reference is stored in config."""
        vault = VaultManager(temp_vault_path)
        vault.save()

        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=temp_vault_path
        )

        # VaultManager should be stored in config
        assert config._vault_manager is not None

    def test_vault_load_failure_fallback(
        self, temp_config_file, temp_vault_path
    ):
        """Test graceful fallback when vault fails to load."""
        # Don't create vault file - should trigger load failure

        # Load config with non-existent vault
        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=temp_vault_path
        )

        # Should fall back to JSON for all credentials
        assert config.db_config[0].user == "json_mysql_user"
        assert config.db_config[0].secret == "json_mysql_pass"
        assert config.email_settings.smtp_user == "json_user@example.com"
        assert config.email_settings.smtp_password == "json_smtp_pass"

        # VaultManager should be None
        assert config._vault_manager is None

    def test_partial_vault_coverage(
        self, temp_config_file, temp_vault_path
    ):
        """Test mixed scenario: some credentials in vault, some in JSON."""
        # Setup vault with only database 2 and no SMTP
        vault = VaultManager(temp_vault_path)
        vault.set("db_2", "vault_pg_user", "vault_pg_pass")
        vault.save()

        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=temp_vault_path
        )

        # Database 1 should use JSON (not in vault)
        assert config.db_config[0].user == "json_mysql_user"
        assert config.db_config[0].secret == "json_mysql_pass"

        # Database 2 should use vault
        assert config.db_config[1].user == "vault_pg_user"
        assert config.db_config[1].secret == "vault_pg_pass"

        # Email should use JSON (not in vault)
        assert config.email_settings.smtp_user == "json_user@example.com"
        assert config.email_settings.smtp_password == "json_smtp_pass"

    def test_all_credentials_from_vault(
        self, temp_config_file, temp_vault_path
    ):
        """Test scenario where all credentials are in vault."""
        # Setup vault with all credentials
        vault = VaultManager(temp_vault_path)
        vault.set("db_1", "vault_mysql_user", "vault_mysql_pass")
        vault.set("db_2", "vault_pg_user", "vault_pg_pass")
        vault.set("smtp", "vault_smtp@example.com", "vault_smtp_pass")
        vault.save()

        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=temp_vault_path
        )

        # All credentials should be from vault
        assert config.db_config[0].user == "vault_mysql_user"
        assert config.db_config[0].secret == "vault_mysql_pass"
        assert config.db_config[1].user == "vault_pg_user"
        assert config.db_config[1].secret == "vault_pg_pass"
        assert config.email_settings.smtp_user == "vault_smtp@example.com"
        assert config.email_settings.smtp_password == "vault_smtp_pass"

    def test_disabled_database_credentials_not_loaded(
        self, temp_config_file, temp_vault_path
    ):
        """Test that disabled databases still get credentials loaded."""
        # Create vault with credentials
        vault = VaultManager(temp_vault_path)
        vault.set("db_1", "vault_mysql_user", "vault_mysql_pass")
        vault.save()

        # Modify config to disable database 1
        with open(temp_config_file) as f:
            config_data = json.load(f)
        config_data["db_config"][0]["enabled"] = False
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        config = VyaBackupConfig.from_file(
            temp_config_file, vault_path=temp_vault_path
        )

        # Credentials should still be loaded from vault
        assert config.db_config[0].user == "vault_mysql_user"
        assert config.db_config[0].secret == "vault_mysql_pass"
        assert not config.db_config[0].enabled
