"""Encryption utilities using Fernet with hostname-based key derivation"""

import base64
import hashlib
import socket
from typing import Any

from cryptography.fernet import Fernet


def get_hostname_key() -> bytes:
    """
    Derive encryption key from hostname using SHA-256.

    This provides a deterministic key based on the server's hostname,
    allowing credentials to be decrypted only on the same machine.

    Returns:
        bytes: 32-byte Fernet-compatible key
    """
    hostname = socket.gethostname()
    # Use SHA-256 to derive 32 bytes from hostname
    hash_digest = hashlib.sha256(hostname.encode()).digest()
    # Fernet requires base64-encoded 32-byte key
    return base64.urlsafe_b64encode(hash_digest)


def encrypt_string(plaintext: str) -> str:
    """
    Encrypt a string using Fernet with hostname-based key.

    Args:
        plaintext: String to encrypt

    Returns:
        str: Base64-encoded encrypted string
    """
    key = get_hostname_key()
    fernet = Fernet(key)
    encrypted_bytes = fernet.encrypt(plaintext.encode())
    return encrypted_bytes.decode()


def decrypt_string(encrypted: str) -> str:
    """
    Decrypt a Fernet-encrypted string using hostname-based key.

    Args:
        encrypted: Base64-encoded encrypted string

    Returns:
        str: Decrypted plaintext string

    Raises:
        cryptography.fernet.InvalidToken: If decryption fails (wrong key or corrupted data)
    """
    key = get_hostname_key()
    fernet = Fernet(key)
    decrypted_bytes = fernet.decrypt(encrypted.encode())
    return decrypted_bytes.decode()


def encrypt_dict(data: dict[str, str]) -> dict[str, str]:
    """
    Encrypt all string values in a dictionary.

    Args:
        data: Dictionary with string values to encrypt

    Returns:
        dict: Dictionary with encrypted values
    """
    return {key: encrypt_string(value) for key, value in data.items()}


def decrypt_dict(encrypted_data: dict[str, str]) -> dict[str, str]:
    """
    Decrypt all string values in a dictionary.

    Args:
        encrypted_data: Dictionary with encrypted values

    Returns:
        dict: Dictionary with decrypted values
    """
    return {key: decrypt_string(value) for key, value in encrypted_data.items()}


class EncryptionManager:
    """
    Encryption manager class for consistent interface.
    
    Provides hostname-based encryption/decryption using Fernet.
    """
    
    def __init__(self):
        """Initialize encryption manager."""
        self._key = get_hostname_key()
        self._fernet = Fernet(self._key)
    
    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt a string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            str: Encrypted string
        """
        return encrypt_string(plaintext)
    
    def decrypt_string(self, encrypted: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted: Encrypted string
            
        Returns:
            str: Decrypted string
        """
        return decrypt_string(encrypted)
    
    def encrypt_dict(self, data: dict[str, str]) -> dict[str, str]:
        """
        Encrypt all values in a dictionary.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            dict: Dictionary with encrypted values
        """
        return encrypt_dict(data)
    
    def decrypt_dict(self, encrypted_data: dict[str, str]) -> dict[str, str]:
        """
        Decrypt all values in a dictionary.
        
        Args:
            encrypted_data: Dictionary with encrypted values
            
        Returns:
            dict: Dictionary with decrypted values
        """
        return decrypt_dict(encrypted_data)

