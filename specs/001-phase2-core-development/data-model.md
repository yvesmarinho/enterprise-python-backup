# Data Model: Phase 2 - Core Development

**Feature**: VYA BackupDB Phase 2  
**Date**: 2026-01-09

## Overview

Este documento define o modelo de dados para o sistema VYA BackupDB v2.0.0, incluindo configurações, credenciais, metadados de backup e estruturas internas.

---

## 1. Configuration Model (Pydantic)

### AppConfig (config.yaml)

```python
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from typing import Literal, Optional
from pathlib import Path

class DatabaseConfig(BaseModel):
    """Database instance configuration"""
    id: str = Field(..., description="Unique database ID")
    type: Literal["mysql", "postgresql"] = Field(..., description="Database type")
    host: str = Field(..., description="Database hostname")
    port: int = Field(ge=1, le=65535, description="Database port")
    enabled: bool = Field(default=True, description="Enable backup for this DB")
    exclude_databases: list[str] = Field(
        default_factory=list,
        description="Databases to exclude from backup"
    )
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_ca_cert: Optional[Path] = Field(None, description="SSL CA certificate path")
    
    @field_validator('exclude_databases')
    @classmethod
    def validate_excludes(cls, v):
        # Add default system databases if not present
        defaults = {
            "mysql": ["information_schema", "performance_schema", "mysql", "sys"],
            "postgresql": ["postgres", "template0", "template1"]
        }
        return list(set(v + defaults.get(cls.type, [])))

class StorageConfig(BaseModel):
    """Storage configuration"""
    base_path: Path = Field(
        default=Path("/var/backups/vya_backupdb"),
        description="Base path for backups"
    )
    structure: str = Field(
        default="{hostname}/{db_id}/{db_name}/{date}",
        description="Directory structure pattern"
    )
    compression_level: int = Field(
        ge=1, le=9, default=6,
        description="Gzip compression level (1-9)"
    )
    checksum_algorithm: Literal["md5", "sha256"] = Field(
        default="sha256",
        description="Checksum algorithm"
    )
    
class RetentionConfig(BaseModel):
    """Retention policy configuration"""
    strategy: Literal["simple", "gfs"] = Field(default="gfs")
    daily_keep: int = Field(ge=1, default=7, description="Keep last N daily backups")
    weekly_keep: int = Field(ge=1, default=4, description="Keep last N weekly backups")
    monthly_keep: int = Field(ge=1, default=12, description="Keep last N monthly backups")
    cleanup_enabled: bool = Field(default=True, description="Enable automatic cleanup")

class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    format: Literal["json", "text"] = Field(default="json")
    output: Literal["console", "file", "both"] = Field(default="file")
    file_path: Path = Field(default=Path("/var/log/vya_backupdb/app.log"))

class AppConfig(BaseSettings):
    """Main application configuration"""
    application_name: str = Field(default="vya-backupdb")
    version: str = Field(default="2.0.0")
    environment: Literal["dev", "staging", "production"] = Field(default="production")
    
    databases: list[DatabaseConfig] = Field(..., description="Database instances")
    storage: StorageConfig = Field(default_factory=StorageConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

---

## 2. Credentials Model (.secrets/credentials.json)

### CredentialsStore

```python
from pydantic import BaseModel, Field
from typing import Literal

class DatabaseCredential(BaseModel):
    """Encrypted database credentials"""
    id: str = Field(..., description="Database ID (matches DatabaseConfig.id)")
    username: str = Field(..., description="Encrypted username (Fernet)")
    password: str = Field(..., description="Encrypted password (Fernet)")
    
class EncryptionMetadata(BaseModel):
    """Encryption metadata"""
    method: Literal["fernet"] = Field(default="fernet")
    key_derivation: Literal["hostname-based"] = Field(default="hostname-based")
    version: str = Field(default="1.0")

class CredentialsStore(BaseModel):
    """Credentials storage format"""
    version: str = Field(default="1.0")
    encryption: EncryptionMetadata = Field(default_factory=EncryptionMetadata)
    credentials: list[DatabaseCredential] = Field(
        default_factory=list,
        description="Encrypted database credentials"
    )
```

**Example JSON**:
```json
{
  "version": "1.0",
  "encryption": {
    "method": "fernet",
    "key_derivation": "hostname-based",
    "version": "1.0"
  },
  "credentials": [
    {
      "id": "prod-mysql-01",
      "username": "gAAAAABl...",
      "password": "gAAAAABl..."
    },
    {
      "id": "prod-postgres-01",
      "username": "gAAAAABl...",
      "password": "gAAAAABl..."
    }
  ]
}
```

---

## 3. Backup Metadata Model

### BackupMetadata (.metadata.json per backup)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional

class BackupInfoModel(BaseModel):
    """Backup execution information"""
    database_id: str
    database_name: str
    database_type: Literal["mysql", "postgresql"]
    hostname: str
    backup_type: Literal["full", "incremental", "differential"] = "full"
    timestamp: datetime
    duration_seconds: float
    status: Literal["success", "failed", "partial"]
    error_message: Optional[str] = None

class FileInfoModel(BaseModel):
    """Backup file information"""
    filename: str
    size_bytes: int
    size_human: str  # e.g., "1.5 MB"
    compression_level: int
    checksum_algorithm: Literal["md5", "sha256"]
    checksum: str

class SchemaInfoModel(BaseModel):
    """Database schema information"""
    tables_count: int
    views_count: int = 0
    procedures_count: int = 0
    functions_count: int = 0
    triggers_count: int = 0
    schema_hash: str  # Hash of schema structure

class BackupMetadata(BaseModel):
    """Complete backup metadata"""
    backup_info: BackupInfoModel
    file_info: FileInfoModel
    schema_info: SchemaInfoModel
    version: str = Field(default="2.0.0")
```

**Example JSON**:
```json
{
  "backup_info": {
    "database_id": "prod-mysql-01",
    "database_name": "mydb",
    "database_type": "mysql",
    "hostname": "wfdb02",
    "backup_type": "full",
    "timestamp": "2026-01-09T02:00:00-03:00",
    "duration_seconds": 45.2,
    "status": "success"
  },
  "file_info": {
    "filename": "mydb_20260109_020000_full.sql.gz",
    "size_bytes": 1572864,
    "size_human": "1.5 MB",
    "compression_level": 6,
    "checksum_algorithm": "sha256",
    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "schema_info": {
    "tables_count": 25,
    "views_count": 5,
    "procedures_count": 10,
    "functions_count": 3,
    "triggers_count": 2,
    "schema_hash": "a1b2c3d4e5f6789..."
  },
  "version": "2.0.0"
}
```

---

## 4. Internal Domain Models

### BackupResult

```python
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime

class BackupResult(BaseModel):
    """Result of backup operation"""
    success: bool
    database_id: str
    database_name: str
    backup_file: Optional[Path] = None
    metadata_file: Optional[Path] = None
    checksum_file: Optional[Path] = None
    duration_seconds: float
    size_bytes: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
```

### RestoreResult

```python
class RestoreResult(BaseModel):
    """Result of restore operation"""
    success: bool
    database_name: str
    backup_file: Path
    duration_seconds: float
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
```

### DatabaseInfo

```python
class DatabaseInfo(BaseModel):
    """Information about a database"""
    name: str
    size_bytes: int = 0
    tables_count: int = 0
    last_backup: Optional[datetime] = None
    backup_status: Literal["never", "success", "failed", "partial"] = "never"
```

---

## 5. Entity Relationships

```
AppConfig (config.yaml)
    ├── 1:N DatabaseConfig[]
    │   └── references → DatabaseCredential (by id)
    ├── 1:1 StorageConfig
    ├── 1:1 RetentionConfig
    └── 1:1 LoggingConfig

CredentialsStore (.secrets/credentials.json)
    └── 1:N DatabaseCredential[]
        └── referenced by ← DatabaseConfig (by id)

BackupMetadata (.metadata.json per backup)
    ├── 1:1 BackupInfoModel
    ├── 1:1 FileInfoModel
    └── 1:1 SchemaInfoModel

BackupResult (runtime model)
    └── generates → BackupMetadata (persisted)

RestoreResult (runtime model)
    └── reads ← BackupMetadata (validation)
```

---

## 6. Database Schema (SQLAlchemy - if needed for future audit log)

**Note**: Phase 2 MVP não usa banco de dados para audit log, mas preparamos estrutura para Phase 4.

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class BackupOperation(enum.Enum):
    BACKUP = "backup"
    RESTORE = "restore"
    CLEANUP = "cleanup"

class OperationStatus(enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

class AuditLog(Base):
    """Audit log table (Phase 4)"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    operation = Column(Enum(BackupOperation), nullable=False)
    database_id = Column(String(255), nullable=False)
    database_name = Column(String(255), nullable=True)
    status = Column(Enum(OperationStatus), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    hostname = Column(String(255), nullable=False)
```

---

## 7. Validation Rules

### DatabaseConfig Validations
- ✅ `id`: Alphanumeric + hyphens only (regex: `^[a-zA-Z0-9-]+$`)
- ✅ `port`: 1-65535
- ✅ `host`: Valid hostname or IP
- ✅ `exclude_databases`: Auto-add system databases

### StorageConfig Validations
- ✅ `base_path`: Must be absolute path
- ✅ `compression_level`: 1-9
- ✅ Directory permissions: 0755 for base_path

### CredentialsStore Validations
- ✅ File permissions: 0600 (read/write owner only)
- ✅ `id` must match existing DatabaseConfig.id
- ✅ Credentials must be Fernet-encrypted strings

### BackupMetadata Validations
- ✅ `checksum`: Valid hex string (length depends on algorithm)
- ✅ `timestamp`: ISO 8601 format with timezone
- ✅ `size_bytes`: > 0 for successful backups

---

## Summary

O data model foi projetado para:
1. **Type Safety**: Pydantic validation em todas as camadas
2. **Serialization**: JSON para configuração e metadados
3. **Encryption**: Fernet para credenciais sensíveis
4. **Extensibility**: Campos Optional para features futuras
5. **Auditability**: Metadata completo para cada backup

**Next**: Proceed to contracts/ (API contracts - CLI commands)
