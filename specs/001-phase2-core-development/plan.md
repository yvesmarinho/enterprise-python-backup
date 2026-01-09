# Implementation Plan: Phase 2 - Core Development

**Branch**: `001-phase2-core-development` | **Date**: 2026-01-09 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-phase2-core-development/spec.md`

## Summary

Implementar o núcleo fundamental do sistema VYA BackupDB v2.0.0, focando na abstração de banco de dados via SQLAlchemy 2.0+, gerenciamento seguro de credenciais com Fernet, engine de backup por database individual, sistema de configuração com Pydantic, e CLI básico com Typer. Includes unit tests (>80% coverage) e integration tests com testcontainers.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: SQLAlchemy 2.0+, Pydantic v2, Typer, cryptography  
**Storage**: Local filesystem (`/var/backups/vya_backupdb/{hostname}/{db_id}/{db_name}/{date}/`)  
**Testing**: pytest + pytest-cov + pytest-asyncio + testcontainers  
**Target Platform**: Linux server (Ubuntu 22.04+, Debian 12+, RHEL 9+)  
**Project Type**: Single Python package (CLI-based)  
**Performance Goals**: <5min backup for 1GB database, <10min restore  
**Constraints**: >80% test coverage, zero plain-text credentials, <200MB memory per backup  
**Scale/Scope**: Multi-database support (10+ databases per instance), production-ready MVP

**Workspace Context**: ⚠️ **IMPORTANTE**
- **Active Repository**: `enterprise-vya-backupdb/` (este repositório)
- **Reference Only** (não modificar): `../vya_backupbd/`, `../enterprise-vya_backupbd/`
- Diretórios de referência contêm código legado para consulta apenas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Modular Architecture ✅
- ✅ Sistema modular com separação clara (core, db, security, utils)
- ✅ Abstração DBMS via SQLAlchemy (interface comum MySQL/PostgreSQL)
- ✅ Design Patterns: Factory (DB engines), Strategy (backup)
- ✅ Type hints completos Python 3.11+

### II. Security-First ✅
- ✅ Credenciais criptografadas (Fernet, `.secrets/credentials.json`)
- ✅ Hostname-based key derivation (sem chaves externas)
- ✅ Log sanitization (nenhuma senha visível)
- ✅ Permissões 0600 em arquivos de credenciais

### III. Test-First Development ✅
- ✅ TDD: Tests escritos → User aprova → Implementation
- ✅ Cobertura >80% (pytest + pytest-cov)
- ✅ Unit tests para cada módulo
- ✅ Integration tests com testcontainers

### IV. Observability & Monitoring ⚠️ (Parcial - Phase 4)
- ⚠️ Structured logging (structlog) - **Phase 2**
- ❌ Prometheus metrics - **Phase 4**
- ❌ Health checks - **Phase 4**
- **Justificativa**: MVP foca em core functionality, observability completa em Phase 4

### V. Configuration as Code ✅
- ✅ Pydantic para validação de configurações
- ✅ SQLAlchemy para transações DB
- ✅ Configurações por ambiente (dev/staging/prod)
- ✅ Secrets em `.secrets/credentials.json`

### VI. DRY Principle ✅
- ✅ Código unificado (sem duplicação checkFolder/connectDB)
- ✅ Utilities compartilhados em `utils/`
- ✅ Composição ao invés de herança

### VII. Performance & Scalability ⚠️ (Parcial - Phase 6)
- ⚠️ Async I/O - **Phase 2 (básico), Phase 6 (completo)**
- ❌ Paralelização - **Phase 6**
- ❌ Connection pooling - **Phase 6**
- **Justificativa**: MVP foca em funcionalidade core, otimizações em Phase 6

**STATUS**: ✅ **APPROVED** - Violations justified for MVP scope

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/vya_backupbd/
├── __init__.py           # Package initialization
├── __main__.py           # CLI entry point
├── cli.py                # Typer CLI commands
├── config.py             # Pydantic configuration models
├── core/
│   ├── __init__.py
│   ├── backup.py         # Backup controller (per-database)
│   └── restore.py        # Restore manager
├── db/
│   ├── __init__.py
│   ├── base.py           # Abstract database interface
│   ├── engine.py         # SQLAlchemy engine factory
│   ├── mysql.py          # MySQL adapter
│   └── postgresql.py     # PostgreSQL adapter
├── security/
│   ├── __init__.py
│   ├── credentials.py    # Credential manager (Fernet)
│   └── encryption.py     # Encryption utilities
└── utils/
    ├── __init__.py
    ├── filesystem.py     # File operations
    ├── compression.py    # Gzip compression
    └── metadata.py       # Backup metadata JSON

tests/
├── __init__.py
├── conftest.py           # Pytest fixtures
├── unit/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_credentials.py
│   ├── test_encryption.py
│   ├── test_backup.py
│   ├── test_restore.py
│   ├── test_db_base.py
│   ├── test_db_engine.py
│   ├── test_db_mysql.py
│   ├── test_db_postgresql.py
│   └── test_utils.py
└── integration/
    ├── __init__.py
    ├── test_mysql_backup.py
    ├── test_postgresql_backup.py
    └── test_end_to_end.py

.secrets/                 # Gitignored
└── credentials.json      # Encrypted credentials

config/
└── config.yaml           # Application configuration

pyproject.toml            # Poetry dependencies
pytest.ini                # Pytest configuration
.gitignore                # Git ignore patterns
README.md                 # Project documentation
```

**Structure Decision**: Single Python package (Option 1) - CLI-based tool sem frontend/backend separation. Estrutura modular com separação clara de responsabilidades conforme constitution.md.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No unjustified violations found.** All partial implementations (⚠️) have documented phase migrations:
- Observability complete in Phase 4
- Async/parallelization complete in Phase 6

## Phase Execution Summary

### Phase 0: Outline & Research ✅ COMPLETE

**Output**: [research.md](./research.md)

**Completed Tasks**:
- Researched SQLAlchemy 2.0+ Core API patterns
- Evaluated Fernet encryption with hostname-based key derivation
- Documented Pydantic v2 BaseSettings patterns
- Analyzed per-database backup strategy vs single dump
- Researched testcontainers integration patterns
- Documented Typer + Rich CLI patterns
- Analyzed async I/O strategy (Phase 2 vs Phase 6)
- Documented GFS retention implementation

**Decisions Made**: 8 technical decisions with rationale and code examples

### Phase 1: Design & Contracts ✅ COMPLETE

**Output**: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Completed Tasks**:
- Created Pydantic data models (AppConfig, DatabaseConfig, StorageConfig, RetentionConfig, LoggingConfig)
- Created CredentialsStore model with encryption metadata
- Created BackupMetadata model with nested structures
- Created domain models (BackupResult, RestoreResult, DatabaseInfo)
- Defined CLI contract with all commands, options, exit codes
- Created quick start guide with installation, configuration, usage examples
- Updated agent context (GitHub Copilot) with current technologies

**Validation**: All models include validation rules, relationships, and example JSON structures

### Phase 2: Tasks & Implementation ⏭️ NEXT STEP

**Command**: `/speckit.tasks` (separate command per template note)

**Expected Output**: [tasks.md](./tasks.md) - Breakdown of implementation tasks

**Next Steps**:
1. Run `/speckit.tasks` to generate task breakdown
2. Begin TDD implementation (tests → approval → code)
3. Implement modules in order: db → security → core → utils → cli
4. Achieve >80% test coverage
5. Run integration tests with testcontainers
