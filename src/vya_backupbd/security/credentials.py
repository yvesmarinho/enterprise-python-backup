"""
Credentials management module.

Handles secure storage, loading, encryption/decryption of database credentials.
Credentials are stored in .secrets/credentials.json with encrypted passwords.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from vya_backupbd.security.encryption import EncryptionManager
from vya_backupbd.config.models import DatabaseConfig

logger = logging.getLogger(__name__)


class CredentialsManager:
    """
    Manages database credentials with encryption.
    
    Credentials are stored in JSON format:
    {
        "database-id": {
            "username": "user",
            "password": "encrypted_password",
            "encrypted": true
        }
    }
    
    Passwords are encrypted using EncryptionManager with hostname-based keys.
    Decrypted credentials are cached in memory for performance.
    """
    
    def __init__(self, credentials_path: str | Path):
        """
        Initialize credentials manager.
        
        Args:
            credentials_path: Path to credentials JSON file
        """
        self.credentials_path = Path(credentials_path)
        self.credentials: Dict[str, Dict[str, Any]] = {}
        self._encryption = EncryptionManager()
        self._cache: Dict[str, Dict[str, str]] = {}
        
        logger.debug(f"Initialized CredentialsManager with path: {self.credentials_path}")
    
    def load(self) -> bool:
        """
        Load credentials from file.
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if not self.credentials_path.exists():
                logger.warning(f"Credentials file not found: {self.credentials_path}")
                return False
            
            with open(self.credentials_path, 'r') as f:
                self.credentials = json.load(f)
            
            # Clear cache on reload
            self._cache.clear()
            
            logger.info(f"Loaded {len(self.credentials)} credentials from {self.credentials_path}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credentials file: {e}")
            self.credentials = {}
            return False
            
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            self.credentials = {}
            return False
    
    def save(self) -> bool:
        """
        Save credentials to file.
        
        Creates parent directories if needed.
        Sets file permissions to 0600 (owner read/write only).
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Create parent directories
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write credentials
            with open(self.credentials_path, 'w') as f:
                json.dump(self.credentials, f, indent=2)
            
            # Set secure permissions (owner read/write only)
            os.chmod(self.credentials_path, 0o600)
            
            logger.info(f"Saved {len(self.credentials)} credentials to {self.credentials_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            return False
    
    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Encrypted password
        """
        try:
            encrypted = self._encryption.encrypt_string(password)
            logger.debug(f"Encrypted password (length: {len(password)} -> {len(encrypted)})")
            return encrypted
        except Exception as e:
            logger.error(f"Error encrypting password: {e}")
            raise
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a password.
        
        Args:
            encrypted_password: Encrypted password
            
        Returns:
            str: Plain text password
        """
        try:
            decrypted = self._encryption.decrypt_string(encrypted_password)
            logger.debug(f"Decrypted password (length: {len(encrypted_password)} -> {len(decrypted)})")
            return decrypted
        except Exception as e:
            logger.error(f"Error decrypting password: {e}")
            raise
    
    def get_credential(self, database_id: str) -> Optional[Dict[str, str]]:
        """
        Get credential for a database.
        
        Returns decrypted credentials. Results are cached in memory.
        
        Args:
            database_id: Database identifier
            
        Returns:
            dict: Credential with username and decrypted password, or None if not found
        """
        # Check cache first
        if database_id in self._cache:
            logger.debug(f"Retrieved credential for '{database_id}' from cache")
            return self._cache[database_id].copy()
        
        # Get from credentials
        if database_id not in self.credentials:
            logger.warning(f"Credential not found for database: {database_id}")
            return None
        
        cred = self.credentials[database_id]
        
        # Build result
        result = {
            "username": cred.get("username", ""),
            "password": cred.get("password", "")
        }
        
        # Decrypt password if encrypted
        if cred.get("encrypted", False):
            try:
                result["password"] = self.decrypt_password(result["password"])
            except Exception as e:
                logger.error(f"Failed to decrypt password for '{database_id}': {e}")
                return None
        
        # Cache result
        self._cache[database_id] = result.copy()
        
        logger.debug(f"Retrieved credential for '{database_id}' (username: {result['username']})")
        return result
    
    def validate(self, database_configs: List[DatabaseConfig]) -> bool:
        """
        Validate that credentials exist for all database configs.
        
        Args:
            database_configs: List of database configurations
            
        Returns:
            bool: True if all configs have credentials, False otherwise
        """
        if not database_configs:
            logger.debug("No database configs to validate")
            return True
        
        missing = []
        for config in database_configs:
            if config.id not in self.credentials:
                missing.append(config.id)
        
        if missing:
            logger.error(f"Missing credentials for databases: {', '.join(missing)}")
            return False
        
        logger.info(f"Validated credentials for {len(database_configs)} databases")
        return True
    
    def check_permissions(self) -> bool:
        """
        Check if credentials file has secure permissions (0600).
        
        Returns:
            bool: True if permissions are secure, False otherwise
        """
        try:
            if not self.credentials_path.exists():
                logger.debug("Credentials file doesn't exist, cannot check permissions")
                return True  # File doesn't exist yet, will be created with correct perms
            
            stat_info = os.stat(self.credentials_path)
            perms = stat_info.st_mode & 0o777
            
            if perms == 0o600:
                logger.debug(f"Credentials file has secure permissions: {oct(perms)}")
                return True
            else:
                logger.warning(f"Credentials file has insecure permissions: {oct(perms)} (expected: 0o600)")
                return False
                
        except Exception as e:
            logger.error(f"Error checking file permissions: {e}")
            return False
    
    def fix_permissions(self) -> bool:
        """
        Fix credentials file permissions to 0600.
        
        Returns:
            bool: True if fixed successfully, False otherwise
        """
        try:
            if not self.credentials_path.exists():
                logger.warning("Credentials file doesn't exist, cannot fix permissions")
                return False
            
            os.chmod(self.credentials_path, 0o600)
            logger.info(f"Fixed credentials file permissions to 0600")
            return True
            
        except Exception as e:
            logger.error(f"Error fixing file permissions: {e}")
            return False
    
    def add_credential(self, database_id: str, username: str, password: str, 
                      encrypt: bool = True) -> bool:
        """
        Add or update a credential.
        
        Args:
            database_id: Database identifier
            username: Username
            password: Password (will be encrypted if encrypt=True)
            encrypt: Whether to encrypt the password
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        try:
            pwd = self.encrypt_password(password) if encrypt else password
            
            self.credentials[database_id] = {
                "username": username,
                "password": pwd,
                "encrypted": encrypt
            }
            
            # Clear cache for this credential
            if database_id in self._cache:
                del self._cache[database_id]
            
            logger.info(f"Added credential for database: {database_id} (username: {username})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding credential for '{database_id}': {e}")
            return False
    
    def remove_credential(self, database_id: str) -> bool:
        """
        Remove a credential.
        
        Args:
            database_id: Database identifier
            
        Returns:
            bool: True if removed, False if not found
        """
        if database_id not in self.credentials:
            logger.warning(f"Credential not found for removal: {database_id}")
            return False
        
        del self.credentials[database_id]
        
        # Clear cache
        if database_id in self._cache:
            del self._cache[database_id]
        
        logger.info(f"Removed credential for database: {database_id}")
        return True
    
    def clear_cache(self) -> None:
        """Clear the credential cache."""
        self._cache.clear()
        logger.debug("Cleared credential cache")
    
    def get_database_ids(self) -> List[str]:
        """
        Get list of database IDs with credentials.
        
        Returns:
            list: Database identifiers
        """
        return list(self.credentials.keys())


def sanitize_log_message(message: str, patterns: Optional[List[str]] = None) -> str:
    """
    Sanitize log message by masking sensitive data.
    
    Replaces passwords, credentials, and other sensitive patterns with '***'.
    
    Args:
        message: Log message to sanitize
        patterns: Additional patterns to mask (regex strings)
        
    Returns:
        str: Sanitized message
    """
    import re
    
    # Default patterns to mask
    default_patterns = [
        r'password["\']?\s*[:=]\s*["\']?([^"\',\s}]+)["\']?',  # password: "value"
        r'--password[=\s]+([^\s]+)',  # --password=value
        r'PGPASSWORD=([^\s]+)',  # PGPASSWORD=value
        r'pass["\']?\s*[:=]\s*["\']?([^"\',\s}]+)["\']?',  # pass: value
        r'pwd["\']?\s*[:=]\s*["\']?([^"\',\s}]+)["\']?',  # pwd: value
        r'secret["\']?\s*[:=]\s*["\']?([^"\',\s}]+)["\']?',  # secret: value
        r'token["\']?\s*[:=]\s*["\']?([^"\',\s}]+)["\']?',  # token: value
        r'key["\']?\s*[:=]\s*["\']?([^"\',\s}]+)["\']?',  # key: value
    ]
    
    if patterns:
        default_patterns.extend(patterns)
    
    sanitized = message
    for pattern in default_patterns:
        sanitized = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), '***'), 
                          sanitized, flags=re.IGNORECASE)
    
    return sanitized
