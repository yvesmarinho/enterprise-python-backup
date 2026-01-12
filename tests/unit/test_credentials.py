"""
Unit tests for credentials management.

Tests secure storage, loading, encryption/decryption of database credentials.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from vya_backupbd.security.credentials import CredentialsManager
from vya_backupbd.config.models import DatabaseConfig


@pytest.fixture
def sample_credentials():
    """Sample encrypted credentials."""
    return {
        "test-mysql-01": {
            "username": "root",
            "password": "mysql_secure_pass_123",
            "encrypted": True
        },
        "test-postgres-01": {
            "username": "postgres",
            "password": "pg_secure_pass_456",
            "encrypted": True
        }
    }


@pytest.fixture
def credentials_file(tmp_path):
    """Create temporary credentials file."""
    creds_dir = tmp_path / ".secrets"
    creds_dir.mkdir()
    creds_file = creds_dir / "credentials.json"
    return creds_file


@pytest.fixture
def sample_database_configs():
    """Sample database configurations."""
    return [
        DatabaseConfig(
            id="test-mysql-01",
            type="mysql",
            host="localhost",
            port=3306,
            username="root",
            password="placeholder",
            database="testdb"
        ),
        DatabaseConfig(
            id="test-postgres-01",
            type="postgresql",
            host="localhost",
            port=5432,
            username="postgres",
            password="placeholder",
            database="testdb"
        )
    ]


class TestCredentialsManagerInitialization:
    """Test CredentialsManager initialization."""

    def test_manager_creation(self, credentials_file):
        """Test creating credentials manager."""
        manager = CredentialsManager(credentials_file)
        
        assert manager.credentials_path == credentials_file
        assert isinstance(manager.credentials_path, Path)

    def test_manager_with_string_path(self, tmp_path):
        """Test creating manager with string path."""
        path_str = str(tmp_path / ".secrets" / "credentials.json")
        manager = CredentialsManager(path_str)
        
        assert isinstance(manager.credentials_path, Path)
        assert str(manager.credentials_path) == path_str

    def test_manager_requires_path(self):
        """Test that manager requires credentials path."""
        with pytest.raises(TypeError):
            CredentialsManager()


class TestCredentialsLoading:
    """Test loading credentials from file."""

    def test_load_credentials_success(self, credentials_file, sample_credentials):
        """Test successful credentials loading."""
        # Write credentials to file
        credentials_file.write_text(json.dumps(sample_credentials))
        
        manager = CredentialsManager(credentials_file)
        result = manager.load()
        
        assert result is True
        assert len(manager.credentials) == 2
        assert "test-mysql-01" in manager.credentials
        assert "test-postgres-01" in manager.credentials

    def test_load_credentials_file_not_found(self, credentials_file):
        """Test loading when file doesn't exist."""
        manager = CredentialsManager(credentials_file)
        result = manager.load()
        
        # Should return False but not crash
        assert result is False
        assert manager.credentials == {}

    def test_load_credentials_invalid_json(self, credentials_file):
        """Test loading invalid JSON."""
        credentials_file.write_text("{ invalid json }")
        
        manager = CredentialsManager(credentials_file)
        result = manager.load()
        
        assert result is False
        assert manager.credentials == {}

    def test_load_credentials_empty_file(self, credentials_file):
        """Test loading empty credentials file."""
        credentials_file.write_text("{}")
        
        manager = CredentialsManager(credentials_file)
        result = manager.load()
        
        assert result is True
        assert manager.credentials == {}


class TestCredentialsSaving:
    """Test saving credentials to file."""

    def test_save_credentials_success(self, credentials_file, sample_credentials):
        """Test successful credentials saving."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = sample_credentials
        
        result = manager.save()
        
        assert result is True
        assert credentials_file.exists()
        
        # Verify file content
        content = json.loads(credentials_file.read_text())
        assert content == sample_credentials

    def test_save_credentials_creates_directory(self, tmp_path):
        """Test that save creates parent directories."""
        creds_file = tmp_path / "new_dir" / ".secrets" / "credentials.json"
        
        manager = CredentialsManager(creds_file)
        manager.credentials = {"test": {"username": "user", "password": "pass"}}
        
        result = manager.save()
        
        assert result is True
        assert creds_file.exists()
        assert creds_file.parent.exists()

    def test_save_credentials_empty(self, credentials_file):
        """Test saving empty credentials."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {}
        
        result = manager.save()
        
        assert result is True
        content = json.loads(credentials_file.read_text())
        assert content == {}

    def test_save_credentials_overwrites(self, credentials_file):
        """Test that save overwrites existing file."""
        credentials_file.write_text('{"old": "data"}')
        
        manager = CredentialsManager(credentials_file)
        manager.credentials = {"new": {"username": "user", "password": "pass"}}
        manager.save()
        
        content = json.loads(credentials_file.read_text())
        assert "old" not in content
        assert "new" in content


class TestCredentialsEncryption:
    """Test credential encryption and decryption."""

    def test_encrypt_password(self, credentials_file):
        """Test encrypting a password."""
        manager = CredentialsManager(credentials_file)
        
        plaintext = "my_secret_password"
        encrypted = manager.encrypt_password(plaintext)
        
        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        assert len(encrypted) > len(plaintext)

    def test_decrypt_password(self, credentials_file):
        """Test decrypting a password."""
        manager = CredentialsManager(credentials_file)
        
        plaintext = "my_secret_password"
        encrypted = manager.encrypt_password(plaintext)
        decrypted = manager.decrypt_password(encrypted)
        
        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self, credentials_file):
        """Test encrypt/decrypt roundtrip."""
        manager = CredentialsManager(credentials_file)
        
        passwords = [
            "simple",
            "with spaces and symbols !@#$%",
            "unicode: café, 日本語, emoji 🔐",
            "very_long_password_" * 10
        ]
        
        for password in passwords:
            encrypted = manager.encrypt_password(password)
            decrypted = manager.decrypt_password(encrypted)
            assert decrypted == password

    def test_encrypt_empty_string(self, credentials_file):
        """Test encrypting empty string."""
        manager = CredentialsManager(credentials_file)
        
        encrypted = manager.encrypt_password("")
        decrypted = manager.decrypt_password(encrypted)
        
        assert decrypted == ""


class TestCredentialsRetrieval:
    """Test retrieving credentials for databases."""

    def test_get_credential_success(self, credentials_file):
        """Test getting credential for database."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {
            "test-db": {
                "username": "user1",
                "password": "encrypted_pass",
                "encrypted": True
            }
        }
        
        with patch.object(manager, 'decrypt_password', return_value='decrypted_pass'):
            cred = manager.get_credential("test-db")
        
        assert cred is not None
        assert cred["username"] == "user1"
        assert cred["password"] == "decrypted_pass"

    def test_get_credential_not_found(self, credentials_file):
        """Test getting non-existent credential."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {}
        
        cred = manager.get_credential("nonexistent")
        
        assert cred is None

    def test_get_credential_unencrypted(self, credentials_file):
        """Test getting unencrypted credential."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {
            "test-db": {
                "username": "user1",
                "password": "plain_pass",
                "encrypted": False
            }
        }
        
        cred = manager.get_credential("test-db")
        
        assert cred["password"] == "plain_pass"


class TestCredentialsValidation:
    """Test credential validation against configs."""

    def test_validate_credentials_success(self, credentials_file, sample_database_configs):
        """Test successful validation."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {
            "test-mysql-01": {"username": "root", "password": "pass1"},
            "test-postgres-01": {"username": "postgres", "password": "pass2"}
        }
        
        result = manager.validate(sample_database_configs)
        
        assert result is True

    def test_validate_credentials_missing(self, credentials_file, sample_database_configs):
        """Test validation with missing credentials."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {
            "test-mysql-01": {"username": "root", "password": "pass1"}
            # Missing test-postgres-01
        }
        
        result = manager.validate(sample_database_configs)
        
        assert result is False

    def test_validate_credentials_extra_ok(self, credentials_file, sample_database_configs):
        """Test validation allows extra credentials."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {
            "test-mysql-01": {"username": "root", "password": "pass1"},
            "test-postgres-01": {"username": "postgres", "password": "pass2"},
            "extra-db": {"username": "user", "password": "pass3"}
        }
        
        result = manager.validate(sample_database_configs)
        
        # Should pass - extra credentials are OK
        assert result is True

    def test_validate_empty_configs(self, credentials_file):
        """Test validation with empty configs."""
        manager = CredentialsManager(credentials_file)
        manager.credentials = {"some-db": {"username": "user", "password": "pass"}}
        
        result = manager.validate([])
        
        # Empty configs should validate
        assert result is True


class TestFilePermissions:
    """Test file permission checks."""

    @patch('os.stat')
    def test_check_permissions_secure(self, mock_stat, credentials_file):
        """Test checking secure file permissions (0600)."""
        # Mock file with 0600 permissions
        mock_stat.return_value = MagicMock(st_mode=0o100600)
        
        manager = CredentialsManager(credentials_file)
        result = manager.check_permissions()
        
        assert result is True

    @patch('os.stat')
    def test_check_permissions_insecure(self, mock_stat, credentials_file):
        """Test detecting insecure permissions."""
        # Mock file with 0644 permissions (readable by others)
        mock_stat.return_value = MagicMock(st_mode=0o100644)
        
        manager = CredentialsManager(credentials_file)
        result = manager.check_permissions()
        
        assert result is False

    @patch('os.chmod')
    def test_fix_permissions(self, mock_chmod, credentials_file):
        """Test fixing file permissions."""
        credentials_file.write_text("{}")
        
        manager = CredentialsManager(credentials_file)
        manager.fix_permissions()
        
        # Should set to 0600
        mock_chmod.assert_called_with(credentials_file, 0o600)


class TestCredentialsIntegration:
    """Integration tests for credential management."""

    def test_full_lifecycle(self, credentials_file):
        """Test complete save/load/encrypt/decrypt cycle."""
        manager = CredentialsManager(credentials_file)
        
        # Add credentials with encryption
        original_password = "super_secret_123"
        encrypted_password = manager.encrypt_password(original_password)
        
        manager.credentials = {
            "prod-db": {
                "username": "admin",
                "password": encrypted_password,
                "encrypted": True
            }
        }
        
        # Save
        assert manager.save() is True
        
        # Create new manager and load
        manager2 = CredentialsManager(credentials_file)
        assert manager2.load() is True
        
        # Retrieve and decrypt (get_credential already decrypts if encrypted=True)
        cred = manager2.get_credential("prod-db")
        assert cred["username"] == "admin"
        assert cred["password"] == original_password  # Already decrypted by get_credential

    def test_multiple_databases(self, credentials_file, sample_database_configs):
        """Test managing multiple database credentials."""
        manager = CredentialsManager(credentials_file)
        
        # Encrypt and store credentials for each database
        original_passwords = {}
        for config in sample_database_configs:
            password = f"pass_{config.id}"
            original_passwords[config.id] = password
            encrypted_pass = manager.encrypt_password(password)
            manager.credentials[config.id] = {
                "username": config.username,
                "password": encrypted_pass,
                "encrypted": True
            }
        
        # Save and reload
        manager.save()
        manager2 = CredentialsManager(credentials_file)
        manager2.load()
        
        # Verify all credentials
        assert len(manager2.credentials) == 2
        assert manager2.validate(sample_database_configs) is True
        
        # Verify decrypted passwords
        for config in sample_database_configs:
            cred = manager2.get_credential(config.id)
            assert cred["password"] == original_passwords[config.id]
