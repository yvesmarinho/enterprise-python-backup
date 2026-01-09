# Feature Specification: Phase 2 - Core Development

**Branch**: `001-phase2-core-development` | **Date**: 2026-01-09  
**Project**: VYA BackupDB v2.0.0  
**Author**: Yves Marinho - Vya.Digital

## Feature Summary

Implementar o núcleo fundamental do sistema VYA BackupDB v2.0.0, incluindo:

1. **Database Abstraction Layer** via SQLAlchemy 2.0+ com suporte a MySQL/MariaDB e PostgreSQL
2. **Credential Management** com criptografia Fernet (hostname-based key derivation)
3. **Backup Engine** com operações por database individual
4. **Configuration System** com validação Pydantic
5. **Basic CLI** com Typer para operações essenciais
6. **Unit Tests** com pytest (>80% coverage target)

## Requirements

### Must-Have (MVP)

1. **Database Operations**
   - SQLAlchemy engine factory com suporte a async
   - MySQL adapter (mysql+pymysql)
   - PostgreSQL adapter (postgresql+psycopg)
   - Connection testing e health checks
   - Backup por database individual (não por instância completa)
   - Exclusão de system databases (information_schema, etc.)

2. **Security**
   - Credentials manager com Fernet encryption
   - Hostname-based key derivation
   - `.secrets/credentials.json` com permissões 0600
   - Log sanitization (sem passwords em logs)

3. **Configuration**
   - Pydantic models para config.yaml
   - Validação de schemas
   - Multi-environment support (dev/staging/prod)

4. **Storage**
   - File system storage com estrutura: `{hostname}/{db_id}/{db_name}/{date}/`
   - Gzip compression (nível configurável)
   - Metadata JSON por backup
   - Checksum SHA256

5. **CLI**
   - `backup` command com --instance, --database, --dry-run
   - `restore` command com --list, --latest, --file
   - `config validate` e `config show`
   - `credentials encrypt`
   - `users backup` command para backup global de usuários
   - `users restore` command com --all ou --user específico

6. **User/Role Management**
   - Backup de todos os usuários MySQL (mysql.user + SHOW GRANTS)
   - Backup de todos os roles PostgreSQL (pg_dumpall --roles-only)
   - Arquivo separado: `{hostname}/{instance}/users_{timestamp}.sql.gz`
   - Restore global (todos os usuários) ou individual (usuário específico)
   - Metadata JSON com lista de usuários e permissões

7. **Testing**
   - Unit tests para cada módulo
   - Integration tests com testcontainers
   - Coverage >80%

### Should-Have (Futuro)

- Parallel backups
- Prometheus metrics
- Email notifications
- Systemd integration
- GFS retention policy

### Won't Have (Out of Scope for Phase 2)

- Web UI
- REST API
- Incremental backups
- PITR (Point-in-Time Recovery)
- Vault integration (Phase 3)
- Parallel user backups (single-threaded in Phase 2)

## Technical Approach

### Technology Stack

- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0+ (async support)
- **Validation**: Pydantic v2
- **CLI**: Typer + Rich
- **Encryption**: cryptography (Fernet)
- **Testing**: pytest + pytest-cov + pytest-asyncio + testcontainers
- **DB Drivers**: pymysql, psycopg3

### Architecture

```
src/vya_backupbd/
├── __init__.py
├── __main__.py
├── cli.py                   # Typer CLI
├── config.py                # Pydantic models
├── core/
│   ├── backup.py           # Backup controller
│   └── restore.py          # Restore manager
├── db/
│   ├── base.py             # Abstract base
│   ├── engine.py           # Engine factory
│   ├── mysql.py            # MySQL adapter
│   └── postgresql.py       # PostgreSQL adapter
├── security/
│   ├── credentials.py      # Credential manager
│   └── encryption.py       # Fernet encryption
└── utils/
    ├── filesystem.py       # File operations
    ├── compression.py      # Gzip
    └── metadata.py         # Metadata JSON

tests/
├── unit/
│   ├── test_config.py
│   ├── test_credentials.py
│   ├── test_backup.py
│   └── test_db_*.py
└── integration/
    ├── test_mysql_backup.py
    └── test_postgresql_backup.py
```

## Success Criteria

- ✅ Backup de database MySQL individual funcional
- ✅ Backup de database PostgreSQL individual funcional
- ✅ Restore de backups por database
- ✅ Credenciais criptografadas com Fernet
- ✅ Unit tests com >80% coverage
- ✅ Integration tests com testcontainers (MySQL + PostgreSQL)
- ✅ CLI funcional com comandos básicos
- ✅ Configuração validada via Pydantic
- ✅ Zero credenciais em plain-text

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SQLAlchemy async complexity | Medium | Medium | Start with sync, migrate to async gradually |
| Testcontainers setup issues | Low | Medium | Fallback to Docker Compose |
| Fernet key derivation consistency | High | Low | Document algorithm, add tests |
| MySQL/PostgreSQL driver issues | Medium | Low | Use well-maintained drivers (pymysql, psycopg3) |

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.11"
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
pydantic = "^2.0"
typer = {extras = ["all"], version = "^0.12"}
rich = "^13.0"
cryptography = "^42.0"
pymysql = "^1.1"
psycopg = {extras = ["binary"], version = "^3.1"}
pyyaml = "^6.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-cov = "^4.1"
pytest-asyncio = "^0.23"
testcontainers = "^4.0"
black = "^24.0"
ruff = "^0.3"
mypy = "^1.8"
```

## Timeline

**Estimated Duration**: 4-6 weeks (Sprints 3-5)

- **Week 1-2**: Database abstraction + credential management + tests
- **Week 3-4**: Backup engine + restore + storage + tests  
- **Week 5-6**: CLI + configuration + integration tests + documentation

## References

- [Constitution](.specify/memory/constitution.md) - Core principles
- [Full Specification](.specify/memory/specify.md) - Complete project spec
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Pydantic v2 Docs](https://docs.pydantic.dev/)
