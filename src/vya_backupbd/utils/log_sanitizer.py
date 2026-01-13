"""
Log sanitizer utilities for masking sensitive information.

This module provides functions to sanitize log output by masking sensitive
data like passwords, tokens, and secrets.
"""

import re
import logging
from typing import Any, Dict, Set
from dataclasses import is_dataclass, fields as dataclass_fields

logger = logging.getLogger(__name__)


class LogSanitizer:
    """
    Sanitize sensitive information from logs.
    
    Masks passwords, secrets, tokens, and other sensitive data before logging.
    
    Example:
        >>> sanitizer = LogSanitizer()
        >>> config = {"host": "localhost", "password": "secret123"}
        >>> sanitizer.sanitize(config)
        {'host': 'localhost', 'password': '***MASKED***'}
    """
    
    # Palavras-chave que identificam campos sensíveis (case-insensitive)
    SENSITIVE_KEYWORDS: Set[str] = {
        'password', 'passwd', 'pwd',
        'secret', 'token', 'key',
        'apikey', 'api_key',
        'auth', 'credential',
        'private', 'salt'
    }
    
    # Valor padrão para substituição
    MASK_VALUE = "***MASKED***"
    
    def __init__(self, mask_value: str = None, additional_keywords: Set[str] = None):
        """
        Initialize log sanitizer.
        
        Args:
            mask_value: Custom mask value (default: ***MASKED***)
            additional_keywords: Additional sensitive keywords to mask
        """
        logger.debug(f"=== Função: __init__ (LogSanitizer) ===")
        
        self.mask_value = mask_value or self.MASK_VALUE
        
        # Combinar keywords padrão com adicionais
        self.sensitive_keywords = self.SENSITIVE_KEYWORDS.copy()
        if additional_keywords:
            self.sensitive_keywords.update(k.lower() for k in additional_keywords)
        
        logger.debug(f"=== Término Função: __init__ (LogSanitizer) ===")
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """
        Check if field name contains sensitive keywords.
        
        Args:
            field_name: Field name to check
            
        Returns:
            True if field is sensitive, False otherwise
        """
        field_lower = field_name.lower()
        return any(keyword in field_lower for keyword in self.sensitive_keywords)
    
    def sanitize(self, obj: Any) -> Any:
        """
        Sanitize object by masking sensitive fields.
        
        Args:
            obj: Object to sanitize (dict, dataclass, Pydantic model, etc.)
            
        Returns:
            Sanitized copy of object
        """
        logger.debug(f"=== Função: sanitize (LogSanitizer) ===")
        logger.debug(f"==> PARAM: obj TYPE: {type(obj)}")
        
        try:
            result = self._sanitize_recursive(obj)
            logger.debug(f"=== Término Função: sanitize (LogSanitizer) ===")
            return result
        except Exception as e:
            logger.warning(f"Error sanitizing object: {e}")
            logger.debug(f"=== Término Função: sanitize (LogSanitizer) COM ERRO ===")
            return str(obj)
    
    def _sanitize_recursive(self, obj: Any, depth: int = 0) -> Any:
        """
        Recursively sanitize object and nested structures.
        
        Args:
            obj: Object to sanitize
            depth: Current recursion depth
            
        Returns:
            Sanitized object
        """
        # Limite de profundidade para evitar recursão infinita
        if depth > 10:
            return "***MAX_DEPTH***"
        
        # None, números, booleanos
        if obj is None or isinstance(obj, (bool, int, float)):
            return obj
        
        # Strings
        if isinstance(obj, str):
            return obj
        
        # Dicionários
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Se é campo sensível E o valor não é dict/list (estrutura complexa)
                if self.is_sensitive_field(key) and not isinstance(value, (dict, list)):
                    result[key] = self.mask_value
                else:
                    # Recursivamente sanitizar o valor
                    result[key] = self._sanitize_recursive(value, depth + 1)
            return result
        
        # Listas e tuplas
        if isinstance(obj, (list, tuple)):
            sanitized = [self._sanitize_recursive(item, depth + 1) for item in obj]
            return type(obj)(sanitized)
        
        # Dataclasses
        if is_dataclass(obj):
            return self._sanitize_dataclass(obj, depth)
        
        # Pydantic models (BaseModel)
        if hasattr(obj, 'model_dump'):
            return self._sanitize_pydantic_v2(obj, depth)
        
        # Pydantic v1 models
        if hasattr(obj, 'dict'):
            return self._sanitize_pydantic_v1(obj, depth)
        
        # Objetos com __dict__
        if hasattr(obj, '__dict__'):
            return self._sanitize_object(obj, depth)
        
        # Outros tipos: converter para string
        return str(obj)
    
    def _sanitize_dataclass(self, obj: Any, depth: int) -> Dict:
        """Sanitize dataclass object."""
        result = {}
        for field in dataclass_fields(obj):
            value = getattr(obj, field.name)
            if self.is_sensitive_field(field.name):
                result[field.name] = self.mask_value
            else:
                result[field.name] = self._sanitize_recursive(value, depth + 1)
        return result
    
    def _sanitize_pydantic_v2(self, obj: Any, depth: int) -> Dict:
        """Sanitize Pydantic v2 model (model_dump)."""
        data = obj.model_dump()
        return self._sanitize_recursive(data, depth + 1)
    
    def _sanitize_pydantic_v1(self, obj: Any, depth: int) -> Dict:
        """Sanitize Pydantic v1 model (dict)."""
        data = obj.dict()
        return self._sanitize_recursive(data, depth + 1)
    
    def _sanitize_object(self, obj: Any, depth: int) -> Dict:
        """Sanitize generic object with __dict__."""
        result = {}
        for key, value in obj.__dict__.items():
            if self.is_sensitive_field(key):
                result[key] = self.mask_value
            else:
                result[key] = self._sanitize_recursive(value, depth + 1)
        return result
    
    def sanitize_string(self, text: str) -> str:
        """
        Sanitize sensitive data in string using regex patterns.
        
        Useful for sanitizing connection strings, URLs, etc.
        
        Args:
            text: String to sanitize
            
        Returns:
            Sanitized string
        """
        logger.debug(f"=== Função: sanitize_string (LogSanitizer) ===")
        logger.debug(f"==> PARAM: text TYPE: {type(text)}, SIZE: {len(text)} chars")
        
        if not isinstance(text, str):
            logger.debug(f"=== Término Função: sanitize_string (LogSanitizer) ===")
            return text
        
        patterns = [
            # password=value, pwd=value, etc
            (r'(password|passwd|pwd|secret|token|apikey|key)\s*=\s*[^\s&;,]+', 
             r'\1=' + self.mask_value),
            
            # password: "value", password: 'value'
            (r'(password|passwd|pwd|secret|token|apikey|key)\s*:\s*["\'][^"\']+["\']',
             r'\1: "' + self.mask_value + '"'),
            
            # URL com senha: user:pass@host
            (r'://([^:]+):([^@]+)@',
             r'://\1:' + self.mask_value + '@'),
        ]
        
        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        logger.debug(f"=== Término Função: sanitize_string (LogSanitizer) ===")
        return result


# Instância global do sanitizador
_default_sanitizer = LogSanitizer()


def sanitize(obj: Any) -> Any:
    """
    Convenience function to sanitize objects using default sanitizer.
    
    Args:
        obj: Object to sanitize
        
    Returns:
        Sanitized object
    
    Example:
        >>> from vya_backupbd.utils.log_sanitizer import sanitize
        >>> config = {"host": "localhost", "password": "secret"}
        >>> sanitize(config)
        {'host': 'localhost', 'password': '***MASKED***'}
    """
    return _default_sanitizer.sanitize(obj)


def sanitize_string(text: str) -> str:
    """
    Convenience function to sanitize strings using default sanitizer.
    
    Args:
        text: String to sanitize
        
    Returns:
        Sanitized string
    
    Example:
        >>> from vya_backupbd.utils.log_sanitizer import sanitize_string
        >>> conn_str = "mysql://user:password123@localhost/db"
        >>> sanitize_string(conn_str)
        'mysql://user:***MASKED***@localhost/db'
    """
    return _default_sanitizer.sanitize_string(text)


def safe_repr(obj: Any) -> str:
    """
    Safe representation of object for logging (with sanitization).
    
    Args:
        obj: Object to represent
        
    Returns:
        String representation with sensitive data masked
    
    Example:
        >>> from vya_backupbd.utils.log_sanitizer import safe_repr
        >>> config = {"host": "localhost", "password": "secret"}
        >>> logger.info(f"Config: {safe_repr(config)}")
    """
    sanitized = _default_sanitizer.sanitize(obj)
    return str(sanitized)
