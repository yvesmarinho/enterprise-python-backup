"""
Tests for log_sanitizer module.
"""

import pytest
from dataclasses import dataclass
from vya_backupbd.utils.log_sanitizer import LogSanitizer, sanitize, sanitize_string, safe_repr


@dataclass
class SampleDataClass:
    """Sample dataclass for testing."""
    host: str
    password: str
    port: int


class TestLogSanitizer:
    """Test LogSanitizer class."""
    
    def test_dict_sanitization(self):
        """Test sanitization of dictionary."""
        sanitizer = LogSanitizer()
        
        data = {
            "host": "localhost",
            "password": "secret123",
            "port": 3306,
            "user": "root"
        }
        
        result = sanitizer.sanitize(data)
        
        assert result["host"] == "localhost"
        assert result["password"] == "***MASKED***"
        assert result["port"] == 3306
        assert result["user"] == "root"
    
    def test_nested_dict_sanitization(self):
        """Test sanitization of nested dictionary."""
        sanitizer = LogSanitizer()
        
        data = {
            "database": {
                "host": "localhost",
                "credentials": {
                    "user": "admin",
                    "password": "secret123",
                    "api_key": "abc123"
                }
            }
        }
        
        result = sanitizer.sanitize(data)
        
        assert result["database"]["host"] == "localhost"
        assert result["database"]["credentials"]["user"] == "admin"
        assert result["database"]["credentials"]["password"] == "***MASKED***"
        assert result["database"]["credentials"]["api_key"] == "***MASKED***"
    
    def test_dataclass_sanitization(self):
        """Test sanitization of dataclass."""
        sanitizer = LogSanitizer()
        
        obj = SampleDataClass(
            host="localhost",
            password="secret123",
            port=3306
        )
        
        result = sanitizer.sanitize(obj)
        
        assert result["host"] == "localhost"
        assert result["password"] == "***MASKED***"
        assert result["port"] == 3306
    
    def test_list_sanitization(self):
        """Test sanitization of list."""
        sanitizer = LogSanitizer()
        
        data = [
            {"name": "db1", "password": "pass1"},
            {"name": "db2", "secret": "pass2"}
        ]
        
        result = sanitizer.sanitize(data)
        
        assert result[0]["name"] == "db1"
        assert result[0]["password"] == "***MASKED***"
        assert result[1]["name"] == "db2"
        assert result[1]["secret"] == "***MASKED***"
    
    def test_custom_mask_value(self):
        """Test custom mask value."""
        sanitizer = LogSanitizer(mask_value="[REDACTED]")
        
        data = {"host": "localhost", "password": "secret"}
        result = sanitizer.sanitize(data)
        
        assert result["password"] == "[REDACTED]"
    
    def test_additional_keywords(self):
        """Test additional sensitive keywords."""
        sanitizer = LogSanitizer(additional_keywords={"custom_secret"})
        
        data = {
            "host": "localhost",
            "custom_secret": "value123"
        }
        
        result = sanitizer.sanitize(data)
        
        assert result["custom_secret"] == "***MASKED***"
    
    def test_string_sanitization(self):
        """Test string sanitization with patterns."""
        sanitizer = LogSanitizer()
        
        # Test password=value pattern
        text1 = "server.conf: host=localhost password=secret123 port=3306"
        result1 = sanitizer.sanitize_string(text1)
        assert "secret123" not in result1
        assert "password=***MASKED***" in result1
        
        # Test URL with password
        text2 = "mysql://user:secret123@localhost/db"
        result2 = sanitizer.sanitize_string(text2)
        assert "secret123" not in result2
        assert "***MASKED***" in result2
    
    def test_is_sensitive_field(self):
        """Test sensitive field detection."""
        sanitizer = LogSanitizer()
        
        assert sanitizer.is_sensitive_field("password") is True
        assert sanitizer.is_sensitive_field("PASSWORD") is True
        assert sanitizer.is_sensitive_field("db_password") is True
        assert sanitizer.is_sensitive_field("api_key") is True
        assert sanitizer.is_sensitive_field("secret_token") is True
        assert sanitizer.is_sensitive_field("host") is False
        assert sanitizer.is_sensitive_field("port") is False
    
    def test_none_and_primitives(self):
        """Test handling of None and primitive types."""
        sanitizer = LogSanitizer()
        
        assert sanitizer.sanitize(None) is None
        assert sanitizer.sanitize(123) == 123
        assert sanitizer.sanitize(45.6) == 45.6
        assert sanitizer.sanitize(True) is True
        assert sanitizer.sanitize("test") == "test"
    
    def test_max_depth_protection(self):
        """Test protection against infinite recursion."""
        sanitizer = LogSanitizer()
        
        # Create circular reference
        data = {"a": {}}
        data["a"]["b"] = data
        
        # Should not crash
        result = sanitizer.sanitize(data)
        assert result is not None


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_sanitize_function(self):
        """Test sanitize() convenience function."""
        data = {"host": "localhost", "password": "secret"}
        result = sanitize(data)
        
        assert result["host"] == "localhost"
        assert result["password"] == "***MASKED***"
    
    def test_sanitize_string_function(self):
        """Test sanitize_string() convenience function."""
        text = "Connection: mysql://user:pass123@localhost/db"
        result = sanitize_string(text)
        
        assert "pass123" not in result
        assert "***MASKED***" in result
    
    def test_safe_repr_function(self):
        """Test safe_repr() convenience function."""
        data = {"host": "localhost", "password": "secret"}
        result = safe_repr(data)
        
        assert isinstance(result, str)
        assert "localhost" in result
        assert "secret" not in result
        assert "***MASKED***" in result


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_dict(self):
        """Test empty dictionary."""
        sanitizer = LogSanitizer()
        result = sanitizer.sanitize({})
        assert result == {}
    
    def test_empty_list(self):
        """Test empty list."""
        sanitizer = LogSanitizer()
        result = sanitizer.sanitize([])
        assert result == []
    
    def test_complex_nested_structure(self):
        """Test complex nested structure."""
        sanitizer = LogSanitizer()
        
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "credentials": {
                            "username": "admin",
                            "password": "secret",
                            "tokens": ["token1", "token2"]
                        }
                    }
                }
            }
        }
        
        result = sanitizer.sanitize(data)
        assert result["level1"]["level2"]["level3"]["credentials"]["password"] == "***MASKED***"
        assert result["level1"]["level2"]["level3"]["credentials"]["username"] == "admin"
