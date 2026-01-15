"""
Unit tests for VaultManager - Secure credential storage system.

Tests cover:
- Vault initialization and file operations
- Credential CRUD operations (set, get, remove, list)
- Encryption/decryption of credentials
- Cache management
- Metadata tracking
- Error handling
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone

from python_backup.security.vault import VaultManager


@pytest.fixture
def temp_vault_path(tmp_path):
    """Create temporary vault file path."""
    return tmp_path / "test_vault.json.enc"


@pytest.fixture
def vault_manager(temp_vault_path):
    """Create VaultManager instance with temp path."""
    return VaultManager(temp_vault_path)


class TestVaultInitialization:
    """Test vault initialization and basic operations."""
    
    def test_init_creates_manager(self, vault_manager, temp_vault_path):
        """Test VaultManager initialization."""
        assert vault_manager.vault_path == temp_vault_path
        assert vault_manager.vault_data["version"] == "1.0.0"
        assert vault_manager.vault_data["credentials"] == {}
        assert vault_manager._cache == {}
    
    def test_load_nonexistent_vault_returns_false(self, vault_manager):
        """Test loading vault that doesn't exist."""
        result = vault_manager.load()
        assert result is False
    
    def test_save_creates_vault_file(self, vault_manager, temp_vault_path):
        """Test saving vault creates encrypted file."""
        result = vault_manager.save()
        assert result is True
        assert temp_vault_path.exists()
        
        # Check file permissions
        stat = temp_vault_path.stat()
        mode = oct(stat.st_mode)[-3:]
        assert mode == "600"
    
    def test_save_and_load_vault(self, vault_manager):
        """Test saving and loading vault preserves structure."""
        # Save initial vault
        vault_manager.save()
        
        # Load vault
        result = vault_manager.load()
        assert result is True
        assert vault_manager.vault_data["version"] == "1.0.0"
        assert "credentials" in vault_manager.vault_data


class TestCredentialOperations:
    """Test credential CRUD operations."""
    
    def test_set_new_credential(self, vault_manager):
        """Test adding new credential."""
        result = vault_manager.set(
            "test-db",
            "admin",
            "P@ssw0rd",
            "Test database"
        )
        assert result is True
        assert "test-db" in vault_manager.vault_data["credentials"]
    
    def test_set_updates_existing_credential(self, vault_manager):
        """Test updating existing credential preserves created_at."""
        # Add initial credential
        vault_manager.set("test-db", "admin", "old_pass", "Test")
        
        # Get created_at
        created_at = vault_manager.vault_data["credentials"]["test-db"]["metadata"]["created_at"]
        
        # Update credential
        vault_manager.set("test-db", "admin2", "new_pass", "Updated")
        
        # Check updated_at changed but created_at preserved
        metadata = vault_manager.vault_data["credentials"]["test-db"]["metadata"]
        assert metadata["created_at"] == created_at
        assert metadata["updated_at"] != created_at
    
    def test_get_existing_credential(self, vault_manager):
        """Test retrieving existing credential."""
        # Add credential
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        
        # Retrieve credential
        cred = vault_manager.get("test-db")
        
        assert cred is not None
        assert cred["username"] == "admin"
        assert cred["password"] == "P@ssw0rd"
    
    def test_get_nonexistent_credential_returns_none(self, vault_manager):
        """Test retrieving non-existent credential."""
        cred = vault_manager.get("nonexistent")
        assert cred is None
    
    def test_get_uses_cache(self, vault_manager):
        """Test credential retrieval uses cache."""
        # Add and retrieve credential
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        cred1 = vault_manager.get("test-db")
        
        # Check cache populated
        assert "test-db" in vault_manager._cache
        
        # Retrieve again (should use cache)
        cred2 = vault_manager.get("test-db")
        
        assert cred1 == cred2
    
    def test_set_invalidates_cache(self, vault_manager):
        """Test updating credential clears cache."""
        # Add and retrieve credential
        vault_manager.set("test-db", "admin", "old_pass")
        vault_manager.get("test-db")
        
        assert "test-db" in vault_manager._cache
        
        # Update credential
        vault_manager.set("test-db", "admin", "new_pass")
        
        # Cache should be cleared for this credential
        assert "test-db" not in vault_manager._cache
    
    def test_remove_existing_credential(self, vault_manager):
        """Test removing existing credential."""
        # Add credential
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        
        # Remove credential
        result = vault_manager.remove("test-db")
        
        assert result is True
        assert "test-db" not in vault_manager.vault_data["credentials"]
    
    def test_remove_nonexistent_credential_returns_false(self, vault_manager):
        """Test removing non-existent credential."""
        result = vault_manager.remove("nonexistent")
        assert result is False
    
    def test_remove_clears_cache(self, vault_manager):
        """Test removing credential clears cache."""
        # Add and retrieve credential
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        vault_manager.get("test-db")
        
        assert "test-db" in vault_manager._cache
        
        # Remove credential
        vault_manager.remove("test-db")
        
        # Cache should be cleared
        assert "test-db" not in vault_manager._cache
    
    def test_list_credentials_empty(self, vault_manager):
        """Test listing credentials in empty vault."""
        creds = vault_manager.list_credentials()
        assert creds == []
    
    def test_list_credentials_sorted(self, vault_manager):
        """Test listing credentials returns sorted list."""
        # Add multiple credentials
        vault_manager.set("zebra-db", "user", "pass")
        vault_manager.set("alpha-db", "user", "pass")
        vault_manager.set("beta-db", "user", "pass")
        
        creds = vault_manager.list_credentials()
        
        assert creds == ["alpha-db", "beta-db", "zebra-db"]
    
    def test_exists_returns_true_for_existing(self, vault_manager):
        """Test exists() returns True for existing credential."""
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        assert vault_manager.exists("test-db") is True
    
    def test_exists_returns_false_for_nonexistent(self, vault_manager):
        """Test exists() returns False for non-existent credential."""
        assert vault_manager.exists("nonexistent") is False


class TestEncryption:
    """Test encryption and decryption of credentials."""
    
    def test_credentials_encrypted_in_storage(self, vault_manager):
        """Test credentials are encrypted when stored."""
        # Add credential
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        
        # Check stored values are encrypted (not plaintext)
        stored = vault_manager.vault_data["credentials"]["test-db"]
        assert stored["username"] != "admin"
        assert stored["password"] != "P@ssw0rd"
    
    def test_credentials_decrypted_on_retrieval(self, vault_manager):
        """Test credentials are decrypted when retrieved."""
        # Add credential
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        
        # Retrieve credential
        cred = vault_manager.get("test-db")
        
        # Check decrypted values match original
        assert cred["username"] == "admin"
        assert cred["password"] == "P@ssw0rd"
    
    def test_vault_file_is_encrypted(self, vault_manager, temp_vault_path):
        """Test vault file content is encrypted."""
        # Add credential and save
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        vault_manager.save()
        
        # Read raw file content
        with open(temp_vault_path, 'rb') as f:
            content = f.read()
        
        # Content should be encrypted (not valid JSON)
        with pytest.raises(json.JSONDecodeError):
            json.loads(content)


class TestMetadata:
    """Test credential metadata tracking."""
    
    def test_get_metadata_existing(self, vault_manager):
        """Test getting metadata for existing credential."""
        vault_manager.set("test-db", "admin", "P@ssw0rd", "Test database")
        
        metadata = vault_manager.get_metadata("test-db")
        
        assert metadata is not None
        assert "created_at" in metadata
        assert "updated_at" in metadata
        assert metadata["description"] == "Test database"
    
    def test_get_metadata_nonexistent_returns_none(self, vault_manager):
        """Test getting metadata for non-existent credential."""
        metadata = vault_manager.get_metadata("nonexistent")
        assert metadata is None
    
    def test_metadata_timestamps_are_iso_format(self, vault_manager):
        """Test metadata timestamps are in ISO format."""
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        
        metadata = vault_manager.get_metadata("test-db")
        
        # Should be able to parse timestamps
        created = datetime.fromisoformat(metadata["created_at"])
        updated = datetime.fromisoformat(metadata["updated_at"])
        
        assert isinstance(created, datetime)
        assert isinstance(updated, datetime)


class TestCacheManagement:
    """Test credential cache management."""
    
    def test_clear_cache(self, vault_manager):
        """Test clearing credential cache."""
        # Add and retrieve credentials
        vault_manager.set("db1", "user1", "pass1")
        vault_manager.set("db2", "user2", "pass2")
        vault_manager.get("db1")
        vault_manager.get("db2")
        
        assert len(vault_manager._cache) == 2
        
        # Clear cache
        vault_manager.clear_cache()
        
        assert len(vault_manager._cache) == 0
    
    def test_load_clears_cache(self, vault_manager):
        """Test loading vault clears cache."""
        # Add and retrieve credential
        vault_manager.set("test-db", "admin", "P@ssw0rd")
        vault_manager.save()
        vault_manager.get("test-db")
        
        assert len(vault_manager._cache) == 1
        
        # Load vault again
        vault_manager.load()
        
        # Cache should be cleared
        assert len(vault_manager._cache) == 0


class TestVaultInfo:
    """Test vault information and statistics."""
    
    def test_get_vault_info_empty(self, vault_manager):
        """Test getting info for empty vault."""
        info = vault_manager.get_vault_info()
        
        assert info["version"] == "1.0.0"
        assert info["credentials_count"] == 0
        assert info["file_size_bytes"] == 0
        assert info["cache_size"] == 0
    
    def test_get_vault_info_with_credentials(self, vault_manager):
        """Test getting info with credentials."""
        # Add credentials and save
        vault_manager.set("db1", "user1", "pass1")
        vault_manager.set("db2", "user2", "pass2")
        vault_manager.save()
        
        # Retrieve one (populates cache)
        vault_manager.get("db1")
        
        info = vault_manager.get_vault_info()
        
        assert info["credentials_count"] == 2
        assert info["file_size_bytes"] > 0
        assert info["cache_size"] == 1


class TestPersistence:
    """Test vault persistence across instances."""
    
    def test_save_and_load_multiple_credentials(self, temp_vault_path):
        """Test saving and loading multiple credentials."""
        # Create vault and add credentials
        vault1 = VaultManager(temp_vault_path)
        vault1.set("db1", "user1", "pass1", "Database 1")
        vault1.set("db2", "user2", "pass2", "Database 2")
        vault1.save()
        
        # Create new instance and load
        vault2 = VaultManager(temp_vault_path)
        vault2.load()
        
        # Verify credentials
        cred1 = vault2.get("db1")
        cred2 = vault2.get("db2")
        
        assert cred1["username"] == "user1"
        assert cred1["password"] == "pass1"
        assert cred2["username"] == "user2"
        assert cred2["password"] == "pass2"
    
    def test_update_persists_across_instances(self, temp_vault_path):
        """Test updating credential persists across instances."""
        # Create vault and add credential
        vault1 = VaultManager(temp_vault_path)
        vault1.set("test-db", "admin", "old_pass")
        vault1.save()
        
        # Create new instance, update, and save
        vault2 = VaultManager(temp_vault_path)
        vault2.load()
        vault2.set("test-db", "admin", "new_pass")
        vault2.save()
        
        # Create third instance and verify
        vault3 = VaultManager(temp_vault_path)
        vault3.load()
        cred = vault3.get("test-db")
        
        assert cred["password"] == "new_pass"
