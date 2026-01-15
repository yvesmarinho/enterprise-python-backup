"""
Vault Manager - Secure Credential Storage System

Manages encrypted credential vault with CRUD operations.
Credentials are stored in .secrets/vault.json.enc with Fernet encryption.
Falls back to .secrets/vya_backupbd.json for migration compatibility.

Architecture:
- VaultManager: Main interface for credential operations
- Encryption: Fernet with hostname-based keys (via EncryptionManager)
- Storage: JSON format with encrypted credentials
- CLI: Integration via vault commands (add/update/remove/list)

Usage:
    vault = VaultManager()
    vault.load()
    
    # Add credential
    vault.set("mysql-prod", "root", "SecureP@ssw0rd")
    
    # Retrieve credential
    cred = vault.get("mysql-prod")
    # {"username": "root", "password": "SecureP@ssw0rd"}
    
    # List all
    ids = vault.list_credentials()
    
    # Remove
    vault.remove("mysql-prod")
    
    vault.save()
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, List, Any

from python_backup.security.encryption import EncryptionManager

logger = logging.getLogger(__name__)


class VaultManager:
    """
    Secure credential vault with encryption.
    
    Stores credentials in encrypted JSON format:
    {
        "version": "1.0.0",
        "credentials": {
            "mysql-prod": {
                "username": "encrypted_username",
                "password": "encrypted_password",
                "metadata": {
                    "created_at": "2026-01-15T15:00:00Z",
                    "updated_at": "2026-01-15T16:30:00Z",
                    "description": "Production MySQL server"
                }
            }
        }
    }
    
    All values (username, password) are encrypted with Fernet.
    Cache stores decrypted credentials for performance.
    """
    
    VAULT_VERSION = "1.0.0"
    
    def __init__(self, vault_path: str | Path = ".secrets/vault.json.enc"):
        """
        Initialize vault manager.
        
        Args:
            vault_path: Path to encrypted vault file
        """
        self.vault_path = Path(vault_path)
        self.vault_data: Dict[str, Any] = {
            "version": self.VAULT_VERSION,
            "credentials": {}
        }
        self._encryption = EncryptionManager()
        self._cache: Dict[str, Dict[str, str]] = {}
        
        logger.debug(f"Initialized VaultManager with path: {self.vault_path}")
    
    def load(self) -> bool:
        """
        Load vault from encrypted file.
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if not self.vault_path.exists():
                logger.warning(f"Vault file not found: {self.vault_path}")
                return False
            
            # Read encrypted content
            with open(self.vault_path, 'rb') as f:
                encrypted_content = f.read()
            
            # Decrypt entire content
            decrypted_json = self._encryption.decrypt_bytes(encrypted_content).decode('utf-8')
            
            # Parse JSON
            self.vault_data = json.loads(decrypted_json)
            
            # Validate structure
            if "version" not in self.vault_data:
                logger.warning("Vault missing version field, adding default")
                self.vault_data["version"] = self.VAULT_VERSION
            
            if "credentials" not in self.vault_data:
                logger.error("Invalid vault structure: missing 'credentials' field")
                return False
            
            # Clear cache on reload
            self._cache.clear()
            
            num_creds = len(self.vault_data["credentials"])
            logger.info(f"Loaded vault with {num_creds} credentials from {self.vault_path}")
            return True
            
        except FileNotFoundError:
            logger.warning(f"Vault file not found: {self.vault_path}")
            return False
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in vault file: {e}")
            self.vault_data = {"version": self.VAULT_VERSION, "credentials": {}}
            return False
            
        except Exception as e:
            logger.error(f"Error loading vault: {e}", exc_info=True)
            self.vault_data = {"version": self.VAULT_VERSION, "credentials": {}}
            return False
    
    def save(self) -> bool:
        """
        Save vault to encrypted file.
        
        Creates parent directories if needed.
        Sets file permissions to 0600 (owner read/write only).
        Entire file content is encrypted with Fernet.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Create parent directories
            self.vault_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize to JSON
            json_content = json.dumps(self.vault_data, indent=2)
            
            # Encrypt entire content
            encrypted_content = self._encryption.encrypt_bytes(json_content.encode('utf-8'))
            
            # Write encrypted bytes
            with open(self.vault_path, 'wb') as f:
                f.write(encrypted_content)
            
            # Set secure permissions (owner read/write only)
            os.chmod(self.vault_path, 0o600)
            
            num_creds = len(self.vault_data["credentials"])
            logger.info(f"Saved vault with {num_creds} credentials to {self.vault_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving vault: {e}", exc_info=True)
            return False
    
    def set(self, credential_id: str, username: str, password: str, 
            description: str = "") -> bool:
        """
        Store or update a credential in the vault.
        
        Args:
            credential_id: Unique identifier for the credential
            username: Username (will be encrypted)
            password: Password (will be encrypted)
            description: Optional description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from datetime import datetime, timezone
            
            # Encrypt username and password
            encrypted_username = self._encryption.encrypt_string(username)
            encrypted_password = self._encryption.encrypt_string(password)
            
            # Check if updating existing credential
            is_update = credential_id in self.vault_data["credentials"]
            action = "Updated" if is_update else "Added"
            
            # Get existing created_at or set new one
            created_at = datetime.now(timezone.utc).isoformat()
            if is_update and "metadata" in self.vault_data["credentials"][credential_id]:
                created_at = self.vault_data["credentials"][credential_id]["metadata"].get(
                    "created_at", created_at
                )
            
            # Store encrypted credential
            self.vault_data["credentials"][credential_id] = {
                "username": encrypted_username,
                "password": encrypted_password,
                "metadata": {
                    "created_at": created_at,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "description": description
                }
            }
            
            # Invalidate cache for this credential
            if credential_id in self._cache:
                del self._cache[credential_id]
            
            logger.info(f"{action} credential '{credential_id}' in vault")
            return True
            
        except Exception as e:
            logger.error(f"Error setting credential '{credential_id}': {e}", exc_info=True)
            return False
    
    def get(self, credential_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieve and decrypt a credential from the vault.
        
        Results are cached in memory for performance.
        
        Args:
            credential_id: Unique identifier for the credential
            
        Returns:
            dict: {"username": str, "password": str} or None if not found
        """
        # Check cache first
        if credential_id in self._cache:
            logger.debug(f"Retrieved credential '{credential_id}' from cache")
            return self._cache[credential_id].copy()
        
        # Check if credential exists
        if credential_id not in self.vault_data["credentials"]:
            logger.warning(f"Credential '{credential_id}' not found in vault")
            return None
        
        try:
            cred = self.vault_data["credentials"][credential_id]
            
            # Decrypt username and password
            username = self._encryption.decrypt_string(cred["username"])
            password = self._encryption.decrypt_string(cred["password"])
            
            result = {
                "username": username,
                "password": password
            }
            
            # Cache result
            self._cache[credential_id] = result.copy()
            
            logger.debug(f"Retrieved credential '{credential_id}' (username: {username})")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving credential '{credential_id}': {e}", exc_info=True)
            return None
    
    def remove(self, credential_id: str) -> bool:
        """
        Remove a credential from the vault.
        
        Args:
            credential_id: Unique identifier for the credential
            
        Returns:
            bool: True if removed, False if not found
        """
        if credential_id not in self.vault_data["credentials"]:
            logger.warning(f"Cannot remove: credential '{credential_id}' not found")
            return False
        
        try:
            # Remove from vault
            del self.vault_data["credentials"][credential_id]
            
            # Remove from cache
            if credential_id in self._cache:
                del self._cache[credential_id]
            
            logger.info(f"Removed credential '{credential_id}' from vault")
            return True
            
        except Exception as e:
            logger.error(f"Error removing credential '{credential_id}': {e}", exc_info=True)
            return False
    
    def list_credentials(self) -> List[str]:
        """
        List all credential IDs in the vault.
        
        Returns:
            list: List of credential IDs (sorted alphabetically)
        """
        ids = sorted(self.vault_data["credentials"].keys())
        logger.debug(f"Listed {len(ids)} credentials")
        return ids
    
    def get_metadata(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a credential without decrypting values.
        
        Args:
            credential_id: Unique identifier for the credential
            
        Returns:
            dict: Metadata (created_at, updated_at, description) or None
        """
        if credential_id not in self.vault_data["credentials"]:
            return None
        
        cred = self.vault_data["credentials"][credential_id]
        return cred.get("metadata", {})
    
    def exists(self, credential_id: str) -> bool:
        """
        Check if a credential exists in the vault.
        
        Args:
            credential_id: Unique identifier for the credential
            
        Returns:
            bool: True if exists, False otherwise
        """
        return credential_id in self.vault_data["credentials"]
    
    def clear_cache(self) -> None:
        """Clear the in-memory credential cache."""
        self._cache.clear()
        logger.debug("Cleared credential cache")
    
    def get_vault_info(self) -> Dict[str, Any]:
        """
        Get vault information (version, count, size).
        
        Returns:
            dict: Vault statistics
        """
        num_credentials = len(self.vault_data["credentials"])
        
        # Calculate file size if exists
        file_size = 0
        if self.vault_path.exists():
            file_size = self.vault_path.stat().st_size
        
        return {
            "version": self.vault_data.get("version", "unknown"),
            "path": str(self.vault_path),
            "credentials_count": num_credentials,
            "file_size_bytes": file_size,
            "cache_size": len(self._cache)
        }
