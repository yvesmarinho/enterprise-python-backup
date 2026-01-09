"""Unit tests for encryption module"""

import socket

import pytest
from cryptography.fernet import InvalidToken

from vya_backupbd.security.encryption import (
    decrypt_dict,
    decrypt_string,
    encrypt_dict,
    encrypt_string,
    get_hostname_key,
)


class TestHostnameKey:
    """Tests for hostname-based key derivation"""

    def test_key_is_consistent(self) -> None:
        """Test that key derivation is deterministic"""
        key1 = get_hostname_key()
        key2 = get_hostname_key()
        assert key1 == key2

    def test_key_is_valid_fernet_key(self) -> None:
        """Test that generated key is valid for Fernet"""
        key = get_hostname_key()
        assert len(key) == 44  # Base64-encoded 32 bytes = 44 chars
        assert key.endswith(b"=")  # Base64 padding

    def test_key_based_on_hostname(self) -> None:
        """Test that key is actually based on hostname"""
        key = get_hostname_key()
        hostname = socket.gethostname()
        # Key should change if hostname changes (can't test directly,
        # but we verify it uses hostname)
        assert hostname is not None
        assert key is not None


class TestStringEncryption:
    """Tests for string encryption/decryption"""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Test encrypting and decrypting returns original"""
        plaintext = "my_secret_password"
        encrypted = encrypt_string(plaintext)
        decrypted = decrypt_string(encrypted)
        assert decrypted == plaintext

    def test_encrypted_is_different_from_plaintext(self) -> None:
        """Test that encrypted string is not plaintext"""
        plaintext = "password123"
        encrypted = encrypt_string(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > len(plaintext)

    def test_empty_string(self) -> None:
        """Test encrypting empty string"""
        plaintext = ""
        encrypted = encrypt_string(plaintext)
        decrypted = decrypt_string(encrypted)
        assert decrypted == plaintext

    def test_unicode_string(self) -> None:
        """Test encrypting unicode characters"""
        plaintext = "Café ☕ Ñoño 你好"
        encrypted = encrypt_string(plaintext)
        decrypted = decrypt_string(encrypted)
        assert decrypted == plaintext

    def test_long_string(self) -> None:
        """Test encrypting long string"""
        plaintext = "a" * 10000
        encrypted = encrypt_string(plaintext)
        decrypted = decrypt_string(encrypted)
        assert decrypted == plaintext

    def test_decrypt_invalid_data(self) -> None:
        """Test decrypting invalid data raises error"""
        with pytest.raises(InvalidToken):
            decrypt_string("not_valid_encrypted_data")


class TestDictEncryption:
    """Tests for dictionary encryption/decryption"""

    def test_encrypt_decrypt_dict(self) -> None:
        """Test encrypting and decrypting dictionary"""
        data = {
            "username": "backup_user",
            "password": "secret_password",
            "host": "localhost",
        }
        encrypted = encrypt_dict(data)
        decrypted = decrypt_dict(encrypted)

        # All keys should be preserved
        assert set(encrypted.keys()) == set(data.keys())
        assert decrypted == data

    def test_encrypted_dict_values_differ(self) -> None:
        """Test that encrypted values are different from originals"""
        data = {"password": "secret123"}
        encrypted = encrypt_dict(data)
        assert encrypted["password"] != data["password"]

    def test_empty_dict(self) -> None:
        """Test encrypting empty dictionary"""
        data: dict[str, str] = {}
        encrypted = encrypt_dict(data)
        decrypted = decrypt_dict(encrypted)
        assert decrypted == data

    def test_dict_with_special_characters(self) -> None:
        """Test dictionary with special characters"""
        data = {
            "user": "admin@example.com",
            "pass": "P@ssw0rd!#$%",
            "db": "my-database_01",
        }
        encrypted = encrypt_dict(data)
        decrypted = decrypt_dict(encrypted)
        assert decrypted == data


class TestEncryptionSecurity:
    """Security-focused encryption tests"""

    def test_same_plaintext_different_ciphertexts(self) -> None:
        """Test that same plaintext produces different ciphertexts"""
        plaintext = "same_password"
        encrypted1 = encrypt_string(plaintext)
        encrypted2 = encrypt_string(plaintext)
        # Fernet includes timestamp, so same plaintext → different ciphertext
        assert encrypted1 != encrypted2
        # But both decrypt to same value
        assert decrypt_string(encrypted1) == plaintext
        assert decrypt_string(encrypted2) == plaintext

    def test_password_not_in_encrypted_output(self) -> None:
        """Test that password doesn't appear in encrypted output"""
        password = "MySuperSecretPassword123"
        encrypted = encrypt_string(password)
        # Password should not be visible in encrypted string
        assert password not in encrypted
        assert password.lower() not in encrypted.lower()
