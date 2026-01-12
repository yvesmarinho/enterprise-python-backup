"""
End-to-end integration tests for credentials management.

Tests complete credential lifecycle with real file system operations,
encryption integration, and interaction with database configs.
"""

import pytest
import json
import os
from pathlib import Path

from vya_backupbd.security.credentials import CredentialsManager
from vya_backupbd.security.encryption import EncryptionManager
from vya_backupbd.config.models import DatabaseConfig


@pytest.fixture
def test_secrets_dir(tmp_path):
    """Create test secrets directory."""
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    return secrets_dir


@pytest.fixture
def credentials_file(test_secrets_dir):
    """Path to credentials file."""
    return test_secrets_dir / "credentials.json"


@pytest.fixture
def database_configs():
    """Sample database configurations."""
    return [
        DatabaseConfig(
            id="prod-mysql-01",
            type="mysql",
            host="mysql.example.com",
            port=3306,
            username="root",
            password="placeholder",
            database="production"
        ),
        DatabaseConfig(
            id="prod-postgres-01",
            type="postgresql",
            host="postgres.example.com",
            port=5432,
            username="postgres",
            password="placeholder",
            database="production"
        ),
        DatabaseConfig(
            id="staging-mysql-01",
            type="mysql",
            host="mysql-staging.example.com",
            port=3306,
            username="staging_user",
            password="placeholder",
            database="staging"
        )
    ]


class TestCredentialsE2ELifecycle:
    """End-to-end credential lifecycle tests."""

    def test_complete_credential_setup(self, credentials_file, database_configs):
        """Test complete setup: create, encrypt, save, load, decrypt."""
        # Initialize manager
        manager = CredentialsManager(credentials_file)
        
        # Add encrypted credentials for each database
        real_passwords = {
            "prod-mysql-01": "MysqlProdPass!123",
            "prod-postgres-01": "PostgresProdPass!456",
            "staging-mysql-01": "StagingPass!789"
        }
        
        for db_id, password in real_passwords.items():
            encrypted = manager.encrypt_password(password)
            manager.credentials[db_id] = {
                "username": next(cfg.username for cfg in database_configs if cfg.id == db_id),
                "password": encrypted,
                "encrypted": True
            }
        
        # Save to file
        assert manager.save() is True
        assert credentials_file.exists()
        
        # Verify file is created with content
        content = json.loads(credentials_file.read_text())
        assert len(content) == 3
        
        # Load in new manager instance
        manager2 = CredentialsManager(credentials_file)
        assert manager2.load() is True
        
        # Verify all credentials can be retrieved (get_credential already decrypts)
        for db_id, expected_password in real_passwords.items():
            cred = manager2.get_credential(db_id)
            assert cred is not None
            assert cred["password"] == expected_password  # Already decrypted by get_credential

    def test_credential_validation_workflow(self, credentials_file, database_configs):
        """Test validation workflow with real configs."""
        manager = CredentialsManager(credentials_file)
        
        # Add credentials for only some databases
        manager.credentials = {
            "prod-mysql-01": {
                "username": "root",
                "password": manager.encrypt_password("pass1"),
                "encrypted": True
            },
            "prod-postgres-01": {
                "username": "postgres",
                "password": manager.encrypt_password("pass2"),
                "encrypted": True
            }
            # Missing staging-mysql-01
        }
        
        # Validation should fail (missing one database)
        result = manager.validate(database_configs)
        assert result is False
        
        # Add missing credential
        manager.credentials["staging-mysql-01"] = {
            "username": "staging_user",
            "password": manager.encrypt_password("pass3"),
            "encrypted": True
        }
        
        # Now validation should pass
        result = manager.validate(database_configs)
        assert result is True


class TestCredentialsFileSystem:
    """Test file system interactions."""

    def test_file_permissions_workflow(self, credentials_file):
        """Test checking and fixing file permissions."""
        manager = CredentialsManager(credentials_file)
        
        # Create file with credentials
        manager.credentials = {
            "test-db": {
                "username": "user",
                "password": manager.encrypt_password("pass"),
                "encrypted": True
            }
        }
        manager.save()
        
        # Set insecure permissions (simulate)
        os.chmod(credentials_file, 0o644)
        
        # Check should fail
        assert manager.check_permissions() is False
        
        # Fix permissions
        manager.fix_permissions()
        
        # Check should pass
        assert manager.check_permissions() is True
        
        # Verify actual permissions
        stat_info = os.stat(credentials_file)
        perms = stat_info.st_mode & 0o777
        assert perms == 0o600

    def test_directory_creation(self, tmp_path):
        """Test that manager creates necessary directories."""
        nested_path = tmp_path / "level1" / "level2" / ".secrets" / "credentials.json"
        
        manager = CredentialsManager(nested_path)
        manager.credentials = {"test": {"username": "user", "password": "pass"}}
        
        # Save should create all directories
        assert manager.save() is True
        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_file_corruption_recovery(self, credentials_file):
        """Test handling corrupted credentials file."""
        # Create valid credentials
        manager = CredentialsManager(credentials_file)
        manager.credentials = {
            "db1": {"username": "user1", "password": "pass1"}
        }
        manager.save()
        
        # Corrupt the file
        credentials_file.write_text("{ corrupted json ]]]")
        
        # Load should handle gracefully
        manager2 = CredentialsManager(credentials_file)
        result = manager2.load()
        
        assert result is False
        assert manager2.credentials == {}


class TestCredentialsEncryptionIntegration:
    """Test integration with encryption module."""

    def test_encryption_manager_compatibility(self, credentials_file):
        """Test that CredentialsManager uses EncryptionManager correctly."""
        # Get encryption manager instance
        encryption = EncryptionManager()
        
        # Create credentials manager
        manager = CredentialsManager(credentials_file)
        
        # Encrypt password
        password = "test_password_123"
        encrypted = manager.encrypt_password(password)
        
        # Verify it's actually encrypted (different from original)
        assert encrypted != password
        
        # Decrypt using CredentialsManager
        decrypted = manager.decrypt_password(encrypted)
        assert decrypted == password

    def test_encryption_consistency(self, credentials_file):
        """Test that encryption is consistent across manager instances."""
        password = "consistent_password"
        
        # Encrypt with first manager
        manager1 = CredentialsManager(credentials_file)
        encrypted1 = manager1.encrypt_password(password)
        
        # Decrypt with second manager
        manager2 = CredentialsManager(credentials_file)
        decrypted = manager2.decrypt_password(encrypted1)
        
        assert decrypted == password

    def test_multiple_password_encryption(self, credentials_file):
        """Test encrypting multiple different passwords."""
        manager = CredentialsManager(credentials_file)
        
        passwords = [
            "simple_pass",
            "complex!Pass@123",
            "emoji_🔐_password",
            "very_long_password_" * 20
        ]
        
        encrypted_passwords = []
        for pwd in passwords:
            enc = manager.encrypt_password(pwd)
            encrypted_passwords.append(enc)
            
            # Each encrypted password should be unique
            assert enc not in encrypted_passwords[:-1]
            
            # Verify decryption
            dec = manager.decrypt_password(enc)
            assert dec == pwd


class TestCredentialsConfigIntegration:
    """Test integration with database configurations."""

    def test_credential_to_config_mapping(self, credentials_file, database_configs):
        """Test mapping credentials to database configs."""
        manager = CredentialsManager(credentials_file)
        
        # Create credentials matching all configs
        for config in database_configs:
            manager.credentials[config.id] = {
                "username": config.username,
                "password": manager.encrypt_password(f"pass_{config.id}"),
                "encrypted": True
            }
        
        manager.save()
        
        # Load and validate
        manager2 = CredentialsManager(credentials_file)
        manager2.load()
        
        # Each config should have matching credential
        for config in database_configs:
            cred = manager2.get_credential(config.id)
            assert cred is not None
            assert cred["username"] == config.username

    def test_partial_credential_coverage(self, credentials_file, database_configs):
        """Test handling partial credential coverage."""
        manager = CredentialsManager(credentials_file)
        
        # Only add credentials for first two databases
        for config in database_configs[:2]:
            manager.credentials[config.id] = {
                "username": config.username,
                "password": manager.encrypt_password("pass"),
                "encrypted": True
            }
        
        manager.save()
        
        # Load and check validation
        manager2 = CredentialsManager(credentials_file)
        manager2.load()
        
        # Should have 2 credentials
        assert len(manager2.credentials) == 2
        
        # Validation against all configs should fail
        assert manager2.validate(database_configs) is False
        
        # Validation against partial configs should pass
        assert manager2.validate(database_configs[:2]) is True

    def test_extra_credentials_handling(self, credentials_file, database_configs):
        """Test handling extra credentials not in configs."""
        manager = CredentialsManager(credentials_file)
        
        # Add credentials for configs + extra ones
        for config in database_configs:
            manager.credentials[config.id] = {
                "username": config.username,
                "password": manager.encrypt_password("pass"),
                "encrypted": True
            }
        
        # Add extra credentials
        manager.credentials["extra-db-01"] = {
            "username": "extra_user",
            "password": manager.encrypt_password("extra_pass"),
            "encrypted": True
        }
        manager.credentials["old-db-archived"] = {
            "username": "old_user",
            "password": manager.encrypt_password("old_pass"),
            "encrypted": True
        }
        
        manager.save()
        
        # Validation should pass (extra credentials are OK)
        manager2 = CredentialsManager(credentials_file)
        manager2.load()
        assert manager2.validate(database_configs) is True


class TestCredentialsErrorScenarios:
    """Test error handling scenarios."""

    def test_missing_credentials_file_init(self, test_secrets_dir):
        """Test initializing with non-existent credentials file."""
        creds_file = test_secrets_dir / "nonexistent.json"
        
        manager = CredentialsManager(creds_file)
        result = manager.load()
        
        # Should handle gracefully
        assert result is False
        assert manager.credentials == {}

    def test_empty_credentials_validation(self, credentials_file, database_configs):
        """Test validating with empty credentials."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {}
        
        # Should fail if configs exist
        assert manager.validate(database_configs) is False
        
        # Should pass if no configs
        assert manager.validate([]) is True

    def test_invalid_credential_format(self, credentials_file):
        """Test handling invalid credential format."""
        # Manually create file with invalid format
        credentials_file.write_text(json.dumps({
            "db1": {
                "username": "user1"
                # Missing password
            }
        }))
        
        manager = CredentialsManager(credentials_file)
        result = manager.load()
        
        # Should load the file
        assert result is True
        
        # Getting credential should handle missing password (returns empty string)
        cred = manager.get_credential("db1")
        assert cred is not None
        assert "username" in cred
        assert "password" in cred
        assert cred["password"] == ""  # Missing password becomes empty string


class TestCredentialsPerformance:
    """Test performance with many credentials."""

    def test_many_credentials(self, credentials_file):
        """Test handling many credentials efficiently."""
        manager = CredentialsManager(credentials_file)
        
        # Create 100 credentials
        num_creds = 100
        original_passwords = {}
        for i in range(num_creds):
            db_id = f"database-{i:03d}"
            password = f"pass_{i}"
            original_passwords[db_id] = password
            manager.credentials[db_id] = {
                "username": f"user_{i}",
                "password": manager.encrypt_password(password),
                "encrypted": True
            }
        
        # Save
        assert manager.save() is True
        
        # Load in new instance
        manager2 = CredentialsManager(credentials_file)
        assert manager2.load() is True
        
        # Verify all credentials
        assert len(manager2.credentials) == num_creds
        
        # Spot check some credentials
        for i in [0, 49, 99]:
            db_id = f"database-{i:03d}"
            cred = manager2.get_credential(db_id)
            assert cred is not None
            assert cred["username"] == f"user_{i}"
            # get_credential already decrypts
            assert cred["password"] == original_passwords[db_id]

    def test_validation_performance(self, credentials_file):
        """Test validation with many database configs."""
        manager = CredentialsManager(credentials_file)
        
        # Create many configs
        configs = []
        for i in range(50):
            config = DatabaseConfig(
                id=f"db-{i:03d}",
                type="mysql" if i % 2 == 0 else "postgresql",
                host=f"host{i}.example.com",
                port=3306 if i % 2 == 0 else 5432,
                username=f"user{i}",
                password="placeholder",
                database=f"database{i}"
            )
            configs.append(config)
            
            # Add matching credential
            manager.credentials[config.id] = {
                "username": config.username,
                "password": manager.encrypt_password(f"pass{i}"),
                "encrypted": True
            }
        
        manager.save()
        
        # Load and validate
        manager2 = CredentialsManager(credentials_file)
        manager2.load()
        
        # Validation should complete quickly
        result = manager2.validate(configs)
        assert result is True
