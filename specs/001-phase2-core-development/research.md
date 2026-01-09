# Research Document: Phase 2 - Core Development

**Feature**: VYA BackupDB Phase 2 - Core Development  
**Date**: 2026-01-09  
**Author**: Yves Marinho - Vya.Digital

## Overview

Este documento consolida a pesquisa necessária para resolver todos os "NEEDS CLARIFICATION" do Technical Context e estabelecer as melhores práticas para as tecnologias escolhidas.

---

## 1. SQLAlchemy 2.0+ Best Practices

### Decision: Use SQLAlchemy 2.0 Core (não ORM completo)
**Rationale**:
- Backup/restore não requer mapeamento objeto-relacional
- Core fornece controle direto sobre queries SQL
- Melhor performance para operações de dump/restore
- Suporte async nativo no 2.0+

**Alternatives Considered**:
- ❌ SQLAlchemy ORM: Overhead desnecessário para backup
- ❌ Raw drivers (pymysql/psycopg): Perda de abstração e pooling

**Implementation**:
```python
# Engine factory pattern
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

def create_db_engine(dialect: str, host: str, port: int, user: str, pwd: str):
    if dialect == "mysql":
        return create_engine(f"mysql+pymysql://{user}:{pwd}@{host}:{port}")
    elif dialect == "postgresql":
        return create_engine(f"postgresql+psycopg://{user}:{pwd}@{host}:{port}")
```

**Resources**:
- [SQLAlchemy 2.0 Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)

---

## 2. Fernet Encryption for Credentials

### Decision: Hostname-based key derivation
**Rationale**:
- Sem necessidade de gerenciar chaves externas
- Chave específica por servidor (isolamento)
- Simples e seguro para MVP
- Migração futura para Vault mantém compatibilidade

**Alternatives Considered**:
- ❌ Environment variables: Risco de exposição em logs
- ❌ Config file com chave: Risco se file comprometido
- ✅ Hostname-based: Chave derivada automaticamente

**Implementation**:
```python
import socket
from hashlib import sha256
import base64
from cryptography.fernet import Fernet

def derive_key_from_hostname() -> bytes:
    hostname = socket.gethostname()
    key_material = sha256(hostname.encode()).digest()
    return base64.urlsafe_b64encode(key_material)

def encrypt_credential(plaintext: str) -> str:
    cipher = Fernet(derive_key_from_hostname())
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt_credential(ciphertext: str) -> str:
    cipher = Fernet(derive_key_from_hostname())
    return cipher.decrypt(ciphertext.encode()).decode()
```

**Security Notes**:
- SHA256 para derivação (não reversível)
- Fernet fornece autenticação + criptografia
- Arquivo `.secrets/` com permissões 0600

**Resources**:
- [Cryptography Fernet](https://cryptography.io/en/latest/fernet/)
- [Key Derivation Best Practices](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/)

---

## 3. Pydantic v2 Configuration Validation

### Decision: Pydantic BaseSettings para config.yaml
**Rationale**:
- Validação automática de tipos
- Support para YAML via pydantic-settings
- Error messages claros
- Integration com environment variables

**Alternatives Considered**:
- ❌ configparser: Sem validação de tipos
- ❌ dataclasses: Validação manual necessária
- ✅ Pydantic: Validação + docs + IDE support

**Implementation**:
```python
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from typing import Literal

class DatabaseConfig(BaseModel):
    id: str
    type: Literal["mysql", "postgresql"]
    host: str
    port: int = Field(ge=1, le=65535)
    enabled: bool = True
    exclude_databases: list[str] = []

class StorageConfig(BaseModel):
    base_path: str = "/var/backups/vya_backupdb"
    compression_level: int = Field(ge=1, le=9, default=6)
    
class AppConfig(BaseSettings):
    databases: list[DatabaseConfig]
    storage: StorageConfig
    
    class Config:
        env_file = ".env"
        yaml_file = "config.yaml"
```

**Resources**:
- [Pydantic v2 Docs](https://docs.pydantic.dev/latest/)
- [Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

## 4. Backup Per Database Strategy

### Decision: Individual database files com estrutura hierárquica
**Rationale**:
- Restore pontual mais rápido
- Paralelização futura facilitada
- Falha em um backup não afeta outros
- Organização clara por servidor/instância/database/data

**Alternatives Considered**:
- ❌ Full instance dump: Restore lento, arquivo grande
- ❌ Tabela por tabela: Overhead excessivo
- ✅ Database individual: Balance ideal

**File Structure**:
```
/var/backups/vya_backupdb/
└── {hostname}/              # wfdb02
    └── {db_id}/             # prod-mysql-01
        └── {db_name}/       # mydb
            └── {date}/      # 2026-01-09
                ├── mydb_20260109_020000_full.sql.gz
                ├── mydb_20260109_020000_full.sql.gz.sha256
                └── mydb_20260109_020000_full.metadata.json
```

**Metadata JSON**:
```json
{
  "backup_info": {
    "database_id": "prod-mysql-01",
    "database_name": "mydb",
    "database_type": "mysql",
    "hostname": "wfdb02",
    "timestamp": "2026-01-09T02:00:00-03:00",
    "duration_seconds": 45.2,
    "status": "success"
  },
  "file_info": {
    "filename": "mydb_20260109_020000_full.sql.gz",
    "size_bytes": 1048576,
    "checksum": "e3b0c44..."
  }
}
```

**Resources**:
- [mysqldump per-database](https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html)
- [pg_dump options](https://www.postgresql.org/docs/current/app-pgdump.html)

---

## 5. Testcontainers Integration

### Decision: testcontainers-python para integration tests
**Rationale**:
- Databases reais (não mocks) para testes
- Isolamento completo (cada test = container novo)
- CI/CD friendly (funciona em GitHub Actions)
- Suporte a MySQL e PostgreSQL

**Alternatives Considered**:
- ❌ Mocks: Não testa SQL real
- ❌ Docker Compose: Setup manual necessário
- ✅ Testcontainers: Setup automático

**Implementation**:
```python
import pytest
from testcontainers.mysql import MySqlContainer
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def mysql_container():
    with MySqlContainer("mysql:8.0") as mysql:
        yield mysql

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

def test_mysql_backup(mysql_container):
    # Populate test data
    # Execute backup
    # Verify backup file exists
    # Verify checksum
    pass
```

**Resources**:
- [Testcontainers Python](https://testcontainers-python.readthedocs.io/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)

---

## 6. CLI Design with Typer

### Decision: Typer + Rich para modern CLI UX
**Rationale**:
- Type hints nativos (Python 3.11+)
- Help automático
- Validação de argumentos
- Rich para output colorido e progress bars

**Alternatives Considered**:
- ❌ argparse: Verboso, sem type hints
- ❌ click: Menos type-safe que Typer
- ✅ Typer: Modern, type-safe, clean

**Implementation**:
```python
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer()
console = Console()

@app.command()
def backup(
    instance: str = typer.Option(..., help="Database instance ID"),
    database: str = typer.Option(None, help="Specific database (optional)"),
    dry_run: bool = typer.Option(False, help="Test without executing"),
    verbose: bool = typer.Option(False, help="Verbose output")
):
    """Perform database backup"""
    if verbose:
        console.print(f"[cyan]Backing up {instance}/{database or 'all'}[/cyan]")
    
    with Progress() as progress:
        task = progress.add_task("[green]Backing up...", total=100)
        # Backup logic here
        progress.update(task, advance=50)

if __name__ == "__main__":
    app()
```

**Resources**:
- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)

---

## 7. Async I/O Strategy

### Decision: asyncio básico em Phase 2, completo em Phase 6
**Rationale**:
- Backup/restore são I/O bound (disco + rede)
- Async permite múltiplos backups concorrentes (futuro)
- SQLAlchemy 2.0 tem suporte async nativo

**Phase 2 Scope**:
- Sync operations (simpler, faster development)
- Async infrastructure preparada (engine factory)

**Phase 6 Scope**:
- Full async implementation
- Parallel backups
- Connection pooling

**Implementation (Phase 2)**:
```python
# Sync version para MVP
def backup_database(db_config: DatabaseConfig) -> BackupResult:
    engine = create_sync_engine(db_config)
    # Backup logic
    return result

# Async infrastructure preparada
async def backup_database_async(db_config: DatabaseConfig) -> BackupResult:
    engine = create_async_engine(db_config)
    # Async backup logic (Phase 6)
    return result
```

**Resources**:
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [asyncio Best Practices](https://docs.python.org/3/library/asyncio-task.html)

---

## 8. GFS Retention Policy

### Decision: GFS (Grandfather-Father-Son) por database
**Rationale**:
- Retention inteligente (não apenas "keep N days")
- Otimização de espaço
- Recovery options variados (daily, weekly, monthly)

**Implementation Strategy (Phase 2 - Basic, Phase 5 - Complete)**:
```python
class RetentionPolicy:
    daily_keep: int = 7      # Last 7 days
    weekly_keep: int = 4     # Last 4 weeks
    monthly_keep: int = 12   # Last 12 months
    
def classify_backup(date: datetime) -> Literal["daily", "weekly", "monthly"]:
    # Monday = weekly
    if date.weekday() == 0:
        return "weekly"
    # First day of month = monthly
    if date.day == 1:
        return "monthly"
    return "daily"

def should_keep(backup_date: datetime, policy: RetentionPolicy) -> bool:
    age_days = (datetime.now() - backup_date).days
    classification = classify_backup(backup_date)
    
    if classification == "daily":
        return age_days <= policy.daily_keep
    elif classification == "weekly":
        return age_days <= policy.weekly_keep * 7
    elif classification == "monthly":
        return age_days <= policy.monthly_keep * 30
```

**Resources**:
- [GFS Backup Strategy](https://en.wikipedia.org/wiki/Backup_rotation_scheme#Grandfather-father-son)

---

## Research Topic 9: User/Role Backup Strategy

**Question**: Should Phase 2 include backup of database users, roles, and permissions?

**Decision**: ✅ **YES - Include in Phase 2**

**Rationale**:
1. **Critical for DR**: Restore to empty server requires users
2. **Separate from database backup**: Users are global (instance-level)
   - MySQL: `mysql.user` table + individual SHOW GRANTS
   - PostgreSQL: Cluster-wide roles via `pg_dumpall --roles-only`
3. **Independent operation**: Can backup/restore users separately from databases
4. **Flexible restore**: Support both global (all users) and single user restore

**Phase 2 Implementation**:

**Backup Strategy**:
```
✅ User backup creates separate file:
  📁 {hostname}/{instance}/users_{timestamp}.sql.gz
  
✅ Includes:
  - All user accounts
  - All passwords (hashed)
  - All GRANTs/permissions
  - Host patterns
  
✅ Metadata JSON:
  - List of users
  - Privilege summary
  - Backup timestamp
```

**Restore Options**:
```bash
# Backup users (global)
vya-backupdb users backup --instance prod-mysql-01 \
  --output users_backup.sql.gz

# List backed-up users
vya-backupdb users list --file users_backup.sql.gz

# Restore users to target server
vya-backupdb users restore --file users_backup.sql.gz \
  --target-instance staging-mysql-01 \
  --exclude-user root,mysql.sys

# Show GRANTs for specific database
vya-backupdb users show-grants --database mydb
```

**Implementation Strategy**:

**MySQL**:
```python
# Get all users
users = connection.execute(
    "SELECT User, Host FROM mysql.user WHERE User != 'mysql.sys'"
)

# For each user, get GRANTs
for user, host in users:
    grants = connection.execute(f"SHOW GRANTS FOR '{user}'@'{host}'")
    # Write to users_backup.sql

# Create compressed file
gzip_compress('users_backup.sql', 'users_{timestamp}.sql.gz')
```

**PostgreSQL**:
```python
# Use pg_dumpall for roles
import subprocess

result = subprocess.run([
    'pg_dumpall',
    '--roles-only',
    '-h', host,
    '-U', username,
    '-f', 'users_backup.sql'
], env={'PGPASSWORD': password})

# Compress
gzip_compress('users_backup.sql', 'users_{timestamp}.sql.gz')
```

**File Structure**:
```
/var/backups/vya_backupdb/
└── wfdb02/
    └── prod-mysql-01/
        ├── users_20260109_020000.sql.gz       # User backup
        ├── users_20260109_020000.metadata.json # User metadata
        ├── mydb/
        │   └── 2026-01-09/
        │       ├── mydb_20260109_020100_full.sql.gz
        │       └── mydb_20260109_020100_full.metadata.json
        └── testdb/
            └── 2026-01-09/
                ├── testdb_20260109_020200_full.sql.gz
                └── testdb_20260109_020200_full.metadata.json
```

**Alternatives Considered**:
- ❌ Include users in each database backup → bloat, duplication
- ❌ Always backup users with database → coupling, security risk
- ✅ **Separate feature (Phase 3)** → clean separation, flexible

**Resources**:
- [MySQL User Management](https://dev.mysql.com/doc/refman/8.0/en/user-account-management.html)
- [PostgreSQL Roles](https://www.postgresql.org/docs/current/user-manag.html)
- [pg_dumpall documentation](https://www.postgresql.org/docs/current/app-pg-dumpall.html)

---

## Summary

Todas as decisões técnicas foram tomadas com base em:
1. **Simplicidade**: MVP funcional antes de otimizações
2. **Segurança**: Fernet encryption, log sanitization
3. **Testabilidade**: Testcontainers para tests realistas
4. **Manutenibilidade**: Type hints, Pydantic validation
5. **Escalabilidade**: Async infrastructure preparada

**Next Steps**: Proceed to Phase 1 (Design & Contracts)
