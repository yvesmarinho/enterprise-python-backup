# VYA BackupDB - Project Specification

## Executive Summary

**Project Name:** VYA BackupDB v2.0.0  
**Type:** Enterprise Database Backup & Restore System  
**Status:** In Development (Phase 1 - Foundation)  
**Started:** January 9, 2026  
**Target Release:** Q3 2026  
**License:** GNU GPL v2.0+  
**Author:** Yves Marinho - Vya.Digital

### Mission Statement
Create a unified, modern, and scalable database backup system by consolidating best practices from existing versions (wfdb02 advanced + Enterprise solid base), with focus on security, monitoring, and automation.

---

## Project Overview

### What is VYA BackupDB?
VYA BackupDB is an enterprise-grade automated backup and restore system for MySQL/MariaDB and PostgreSQL databases. It provides:

- **Automated Backups:** Scheduled full backups with intelligent retention (GFS strategy)
- **Security-First:** Encrypted credentials, TLS/SSL connections, audit logging
- **Multi-Database:** Support for MySQL/MariaDB and PostgreSQL via SQLAlchemy
- **Monitoring:** Prometheus metrics, OpenTelemetry tracing, Grafana dashboards (apenas geração de dados, já existe o stack Prometheus)
- **Cloud-Ready:** Multiple storage backends (Local, S3, Azure, GCS)
- **Production-Ready:** Systemd integration, Docker/Kubernetes support, CI/CD pipeline

### Problem Statement
Current legacy versions (Enterprise v0.1.0 and wfdb02) have:
- ❌ Security issues (plain-text credentials in Enterprise)
- ❌ Code duplication (checkFolder, connectDB functions)
- ❌ Inconsistent features between versions
- ❌ Limited test coverage
- ❌ Manual deployment processes
- ❌ No integration with existing cloud backup solution (Idrive)

**Note:** `vya_global` (shared library) is a separate independent project and can be used as optional dependency if needed.

### Solution
A unified codebase that:
- ✅ Encrypts all credentials (Fernet + future Vault integration)
- ✅ Eliminates code duplication (DRY principle)
- ✅ Modular architecture with clear separation of concerns
- ✅ Feature parity + new capabilities
- ✅ >80% test coverage (TDD approach, futuramente)
- ✅ Automated deployment (Docker, Helm, Ansible, futuramente)
- ✅ Integrates with Idrive for cloud backup (generates files for scheduled sync)
- ✅ Optional use of vya_global library for shared utilities (if needed)

---

## Technical Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────┐
│                   VYA BackupDB System                   │
├─────────────────────────────────────────────────────────┤
│  CLI Interface (Typer + Rich)                          │
├─────────────────────────────────────────────────────────┤
│  Core Layer                                             │
│  ├── Backup Controller     ├── Restore Manager          │
│  ├── Scheduler             └── Cleanup Service          │
├─────────────────────────────────────────────────────────┤
│  Database Abstraction (SQLAlchemy 2.0+)                 │
│  ├── MySQL/MariaDB       └── PostgreSQL                 │
├─────────────────────────────────────────────────────────┤
│  Cross-Cutting Concerns                                 │
│  ├── Security (Fernet, Vault)   ├── Monitoring (Prom.)  │
│  ├── Notifications (Email)      └── Audit Logging       │
├─────────────────────────────────────────────────────────┤
│  Infrastructure                                         │
│  ├── Local Storage (Backup Files)                       │
│  ├── Scheduling (Systemd, Cron)                         │
│  └── Cloud Sync (Idrive - External Scheduler)           │
└─────────────────────────────────────────────────────────┘
```

### Module Structure
```
src/vya_backupbd/
├── __init__.py
├── __main__.py              # Entry point
├── cli.py                   # CLI interface (Typer)
├── config.py                # Pydantic configuration models
│
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── backup.py           # Backup orchestration
│   ├── restore.py          # Restore operations
│   ├── scheduler.py        # Job scheduling
│   └── cleanup.py          # Retention management
│
├── db/                      # Database abstraction (SQLAlchemy)
│   ├── __init__.py
│   ├── engine.py           # Engine factory
│   ├── models.py           # ORM models (if needed)
│   ├── mysql.py            # MySQL-specific operations
│   └── postgresql.py       # PostgreSQL-specific operations
│
├── security/                # Security layer
│   ├── __init__.py
│   ├── credentials.py      # Credentials manager (Fernet)
│   ├── vault.py            # Vault integration (future)
│   └── audit.py            # Audit logging
│
├── monitoring/              # Observability
│   ├── __init__.py
│   ├── metrics.py          # Prometheus metrics
│   ├── tracing.py          # OpenTelemetry (future)
│   └── health.py           # Health checks
│
├── notifications/           # Notification system
│   ├── __init__.py
│   ├── email.py            # Email notifications (SMTP)
│   ├── slack.py            # Slack webhooks (future)
│   └── webhook.py          # Generic webhooks (future)
│
└── utils/                   # Shared utilities
    ├── __init__.py
    ├── filesystem.py       # File operations
    ├── compression.py      # Gzip compression
    └── validation.py       # Input validation
```

---

## Key Features & Requirements

### Must-Have (MVP - Phase 2)
1. **Database Operations**
   - **Backup por Database Individual:** Cada database em arquivo separado
   - Full backup for MySQL and PostgreSQL (um database por vez)
   - Backup de múltiplos databases (iteração sequencial/paralela)
   - Restore pontual de database específico
   - Restore from backup files (seleção por database/data)
   - Connection testing (dry-run mode)
   - Database listing and validation
   - Exclusão de databases do sistema (information_schema, etc.)

2. **Security**
   - Encrypted credentials in `.secrets/credentials.json`
   - Fernet encryption (key derived from hostname)
   - TLS/SSL connections to databases
   - Log sanitization (no passwords in logs)

3. **Storage**
   - Local filesystem storage (pasta configurável)
   - **Estrutura por database:** `/tmp/bkpsql/YYYY-MM-DD-{db-mgnt}-{hostname}-{db_name}-.*`
   - Gzip compression (configurable level 1-9) por database armazenado na pasta`/tmp/bkpzip/YYYY-MM-DD-{db-mgnt}-{hostname}-{db_name}-.gz`
   - Checksum verification (MD5/SHA256) por arquivo de backup
   - Idrive integration (gera arquivos para sync automático)
   - GFS retention strategy (daily/weekly/monthly) por database
   - Automatic cleanup de backups expirados por database
   - Metadata file (JSON) com informações do backup

4. **Scheduling**
   - Systemd timer integration
   - Configurable intervals
   - Timezone awareness

5. **Notifications**
   - Email notifications (success/failure)
   - Different recipients for success/error
   - Configurable templates

6. **Monitoring**
   - Prometheus metrics (basic)
   - Structured logging (structlog)
   - Health check endpoint

7. **CLI**
   - Modern CLI with Typer
   - Rich output formatting

### Should-Have (Phase 3-5)
- Incremental backups
- Point-in-Time Recovery (PITR)
- Vault integration (HashiCorp, AWS, Azure)
- Advanced metrics and tracing
- Grafana dashboards
- Parallel backups
- Idrive sync status monitoring
- Backup verification after Idrive sync

### Could-Have (Phase 6-8)
- Deduplication
- Backup verification
- Auto-recovery mechanisms
- Multi-region replication

---

## Technology Stack

### Core Technologies
| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.11+ | Core language |
| ORM | SQLAlchemy | 2.0+ | Database abstraction |
| Validation | Pydantic | 2.x | Config validation |
| CLI | Typer | 0.12+ | Command-line interface |
| Output | Rich | 13.x | Terminal formatting |
| Async | asyncio | stdlib | Async operations |

### Database Drivers
| Database | Driver | Dialect |
|----------|--------|---------|
| MySQL | pymysql | mysql+pymysql |
| PostgreSQL | psycopg3 | postgresql+psycopg |

### Security & Monitoring
| Category | Technology | Purpose |
|----------|-----------|---------|
| Encryption | cryptography | Fernet encryption |
| Metrics | prometheus-client | Metrics collection |
| Logging | structlog | Structured logging |
| Tracing | opentelemetry | Distributed tracing (future) |

### Testing & Quality
| Category | Technology | Purpose |
|----------|-----------|---------|
| Testing | pytest | Test framework |
| Coverage | pytest-cov | Code coverage |
| Async Tests | pytest-asyncio | Async test support |
| Integration | testcontainers | DB integration tests |
| Linting | ruff | Fast linting |
| Formatting | black | Code formatting |
| Type Check | mypy | Static type checking |
| Security | bandit | Security scanning |

### DevOps
| Category | Technology | Purpose |
|----------|-----------|---------|
| Container | Docker/Podman | Containerization |
| Orchestration | Kubernetes + Helm | K8s deployment |
| IaC | Terraform + Ansible | Infrastructure |
| CI/CD | GitHub Actions | Automation |

---

## Configuration Model

### Application Configuration (`config.yaml`)
```yaml
application:
  name: "vya-backupdb"
  version: "2.0.0"
  environment: "production"  # dev, staging, production
  
logging:
  level: "INFO"              # DEBUG, INFO, WARNING, ERROR
  format: "json"             # json, text
  output: "file"             # console, file, both
  file_path: "/var/log/vya_backupdb/app.log"

backup:
  compression_level: 6       # 1-9 (gzip)
  verify_integrity: true
  dry_run: false

storage:
  local:
    base_path: "/var/backups/vya_backupdb"           # Base path monitorada pelo Idrive
    structure: "{hostname}/{db_id}/{db_name}/{date}" # Estrutura de pastas
    temp_path: "/var/backups/vya_backupdb/temp"      # Temporários antes de mover
    # Exemplo final: /var/backups/vya_backupdb/wfdb02/prod-mysql-01/mydb/2026-01-09/
  file_naming:
    pattern: "{db_name}_{datetime}_{type}.sql.gz"   # Padrão de nome de arquivo
    datetime_format: "%Y%m%d_%H%M%S"                 # 20260109_020000
    # Exemplo: mydb_20260109_020000_full.sql.gz
  retention:
    strategy: "gfs"          # simple, gfs
    daily_keep: 7
    weekly_keep: 4
    monthly_keep: 12
    cleanup_enabled: true     # Auto-cleanup de backups expirados
    apply_per_database: true  # Política aplicada por database individual
  checksums:
    enabled: true
    algorithm: "sha256"      # md5, sha256
    store_file: true          # Salva .sha256 junto com backup
  metadata:
    enabled: true             # Gera arquivo .metadata.json com info do backup
    include_schema_hash: true # Hash do schema para detectar mudanças
  idrive:
    enabled: true             # Integração com Idrive (externo)
    sync_folder: "/var/backups/vya_backupdb"  # Pasta sincronizada
    verify_after_sync: false  # Verificar após Idrive sincronizar (futuro)

scheduling:
  enabled: true
  method: "systemd"          # systemd, cron, interval
  interval_minutes: 1440     # 24 hours
  timezone: "America/Sao_Paulo"

monitoring:
  prometheus:
    enabled: true
    pushgateway_url: "https://prometheus.vya.digital/pushgateway"
    job_name: "vya-backup-{hostname}"
    push_interval: 60
  health_check:
    enabled: true
    port: 8080
    path: "/health"

notifications:
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    use_tls: true
    from_address: "backups@vya.digital"
    success_recipients: ["admin@vya.digital"]
    error_recipients: ["alerts@vya.digital", "oncall@vya.digital"]
    templates:
      success: "backup_success.html"
      error: "backup_error.html"
```

### Backup Metadata (`.metadata.json` - gerado automaticamente)
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
    "size_bytes": 1048576,
    "size_human": "1.0 MB",
    "compression_level": 6,
    "checksum_algorithm": "sha256",
    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "schema_info": {
    "tables_count": 25,
    "views_count": 5,
    "procedures_count": 10,
    "schema_hash": "a1b2c3d4e5f6..."
  },
  "version": "2.0.0"
}
```

### Credentials Configuration (`.secrets/credentials.json`)
```json
{
  "version": "1.0",
  "encryption": {
    "method": "fernet",
    "key_derivation": "hostname-based"
  },
  "databases": [
    {
      "id": "prod-mysql-01",
      "enabled": true,
      "type": "mysql",
      "host": "mysql.prod.vya.digital",
      "port": 3306,
      "username": "gAAAAABl...",  // encrypted
      "password": "gAAAAABl...",  // encrypted
      "database": "*",
      "exclude_databases": ["information_schema", "performance_schema"],
      "ssl": {
        "enabled": true,
        "ca_cert": "/etc/ssl/certs/mysql-ca.pem"
      }
    },
    {
      "id": "prod-postgres-01",
      "enabled": true,
      "type": "postgresql",
      "host": "postgres.prod.vya.digital",
      "port": 5432,
      "username": "gAAAAABl...",  // encrypted
      "password": "gAAAAABl...",  // encrypted
      "database": "*",
      "exclude_databases": ["postgres", "template0", "template1"],
      "ssl": {
        "enabled": true,
        "mode": "verify-full"
      }
    }
  ]
}
```

---

## API Specification (CLI)

### Backup Operations
```bash
# Full backup (all configured databases - um por vez)
vya-backupdb backup

# Backup specific database instance (todos os databases da instância)
vya-backupdb backup --instance prod-mysql-01

# Backup specific database (apenas um database)
vya-backupdb backup --instance prod-mysql-01 --database mydb

# Backup múltiplos databases específicos
vya-backupdb backup --instance prod-mysql-01 --database mydb,otherdb

# Dry-run mode (test connection only)
vya-backupdb backup --dry-run

# Backup with custom compression
vya-backupdb backup --compression 9

# Parallel backup (múltiplos databases simultaneamente)
vya-backupdb backup --parallel --workers 4

# Verbose output
vya-backupdb backup --verbose

# List databases disponíveis para backup
vya-backupdb backup --list-databases --instance prod-mysql-01
```

### Restore Operations
```bash
# List available backups (todos os databases)
vya-backupdb restore --list

# List backups de database específico
vya-backupdb restore --list --instance prod-mysql-01 --database mydb

# Restore latest backup de database específico
vya-backupdb restore --instance prod-mysql-01 --database mydb --latest

# Restore specific backup file
vya-backupdb restore --file /var/backups/.../mydb_20260109_020000_full.sql.gz

# Restore to specific date/time (busca backup mais próximo)
vya-backupdb restore --instance prod-mysql-01 --database mydb --datetime "2026-01-09 10:00:00"

# Restore com target diferente (para outro database)
vya-backupdb restore --file backup.sql.gz --target-database mydb_restore

# Dry-run restore (valida backup sem aplicar)
vya-backupdb restore --file backup.sql.gz --dry-run

# Interactive restore (seleciona backup de lista)
vya-backupdb restore --interactive --instance prod-mysql-01 --database mydb
```

### Configuration Management
```bash
# Validate configuration
vya-backupdb config validate

# Show current configuration
vya-backupdb config show

# Test database connections
vya-backupdb config test-connections

# Encrypt credentials
vya-backupdb credentials encrypt --input plain.json --output .secrets/credentials.json
```

### Monitoring
```bash
# Show system status
vya-backupdb status

# Health check
vya-backupdb health

# Show metrics
vya-backupdb metrics

# Show last backup status
vya-backupdb status --last-backup
```

---

## Security Specification

### Credential Encryption (Phase 1)
**Method:** Fernet (symmetric encryption)  
**Key Derivation:** Hostname-based (no external keys)  
**Storage:** `.secrets/credentials.json` (gitignored, mode 0600)

**Encryption Process:**
```python
import socket
from cryptography.fernet import Fernet
from hashlib import sha256
import base64

# Derive key from hostname
hostname = socket.gethostname()
key_material = sha256(hostname.encode()).digest()
key = base64.urlsafe_b64encode(key_material)
cipher = Fernet(key)

# Encrypt credential
encrypted = cipher.encrypt(b"my_password")
```

**Decryption Process:**
```python
# Same key derivation as encryption
decrypted = cipher.decrypt(encrypted)
```

### Future Vault Integration (Phase 3)
**Supported Providers:**
- HashiCorp Vault (hvac client)
- AWS Secrets Manager (boto3)
- Azure Key Vault (azure-keyvault)

**Migration Path:**
1. Phase 1: `.secrets/credentials.json` (encrypted)
2. Phase 2: Environment variables + `.env` support
3. Phase 3: Vault integration (optional, configurable)

### Log Sanitization
**Rules:**
- NEVER log passwords in any form
- NEVER log connection strings with credentials
- Sanitize all SQL queries before logging
- Mask sensitive fields (username shown as `user***`)
- Audit logs stored separately with encryption

---

## Monitoring Specification

### Prometheus Metrics

**Counters:**
```
vya_backup_executions_total{database_type, database_id, status}
vya_backup_errors_total{database_type, database_id, error_type}
vya_backup_restores_total{database_type, database_id, status}
vya_backup_files_processed_total{operation, status}
```

**Gauges:**
```
vya_backup_last_status{database_type, database_id}  # 1=success, 0=failure
vya_backup_last_timestamp{database_type, database_id}
vya_backup_last_size_bytes{database_type, database_id}
vya_backup_configured_databases{database_type}
vya_backup_disk_usage_bytes{path_type}
```

**Histograms:**
```
vya_backup_duration_seconds{database_type, database_id}
vya_backup_restore_duration_seconds{database_type, database_id}
```

**Summaries:**
```
vya_backup_size_bytes_summary{database_type}
```

### Health Check Endpoints
```
GET /health
Response: {"status": "healthy", "timestamp": "2026-01-09T10:00:00Z"}

GET /health/ready
Response: {"ready": true, "databases": {"prod-mysql-01": "ok", "prod-postgres-01": "ok"}}

GET /health/live
Response: {"alive": true}
```

---

## Testing Strategy

### Test Coverage Requirements
- **Unit Tests:** >80% coverage
- **Integration Tests:** All database operations
- **E2E Tests:** Complete backup/restore workflows
- **Security Tests:** Bandit scan, no high/critical issues
- **Performance Tests:** Benchmarks for key operations

### Test Structure
```
tests/
├── unit/
│   ├── test_backup_controller.py
│   ├── test_restore_manager.py
│   ├── test_credentials.py
│   ├── test_scheduler.py
│   └── test_config.py
│
├── integration/
│   ├── test_mysql_operations.py
│   ├── test_postgresql_operations.py
│   ├── test_storage_backends.py
│   └── test_notifications.py
│
├── e2e/
│   ├── test_full_backup_workflow.py
│   ├── test_restore_workflow.py
│   └── test_scheduling.py
│
└── fixtures/
    ├── config_samples.py
    ├── database_containers.py
    └── mock_data.py
```

### Test Environments
- **Local:** Docker Compose (MySQL + PostgreSQL containers)
- **CI:** Testcontainers (ephemeral containers)
- **Integration:** Staging environment with real databases

---

## Deployment Specification

### Docker Deployment
```dockerfile
# Multi-stage build
FROM python:3.11-alpine AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-alpine
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src/ ./src/
ENV PATH=/root/.local/bin:$PATH
USER nobody
ENTRYPOINT ["vya-backupdb"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: CronJob
metadata:
  name: vya-backupdb
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: vya-backupdb
            image: vya/backupdb:2.0.0
            env:
            - name: VYA_CONFIG
              value: "/config/config.yaml"
            volumeMounts:
            - name: config
              mountPath: /config
            - name: secrets
              mountPath: /.secrets
            - name: backups
              mountPath: /var/backups
          volumes:
          - name: config
            configMap:
              name: vya-backupdb-config
          - name: secrets
            secret:
              secretName: vya-backupdb-credentials
          - name: backups
            persistentVolumeClaim:
              claimName: vya-backupdb-storage
```

### Systemd Service
```ini
[Unit]
Description=VYA BackupDB Service
After=network.target

[Service]
Type=oneshot
User=backups
Group=backups
WorkingDirectory=/opt/vya_backupdb
ExecStart=/opt/vya_backupdb/venv/bin/vya-backupdb backup
Environment="VYA_CONFIG=/etc/vya_backupdb/config.yaml"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## Development Roadmap

### Phase 1: Foundation ✅ (Weeks 1-2)
- [x] Project analysis and requirements gathering
- [x] Constitution document creation
- [x] Specification document creation
- [ ] Repository setup (Git, structure)
- [ ] CI/CD pipeline basic setup
- [ ] Development environment setup

### Phase 2: Core Development (Weeks 3-10)
- [ ] SQLAlchemy database abstraction
- [ ] Credential encryption (Fernet)
- [ ] Backup controller implementation
- [ ] Restore manager implementation
- [ ] Pydantic configuration models
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests (testcontainers)

### Phase 3: Security & Monitoring (Weeks 11-14)
- [ ] Log sanitization
- [ ] Audit logging
- [ ] Prometheus metrics integration
- [ ] Health check endpoints
- [ ] Security testing (bandit, safety)

### Phase 4: CLI & UX (Weeks 15-16)
- [ ] Typer CLI implementation
- [ ] Rich output formatting
- [ ] Progress indicators
- [ ] Interactive prompts
- [ ] Help documentation

### Phase 5: Deployment (Weeks 17-18)
- [ ] Docker image creation
- [ ] Helm chart development
- [ ] Systemd service files
- [ ] Ansible playbooks
- [ ] Documentation updates

### Phase 6: Beta & Testing (Weeks 19-20)
- [ ] Beta deployment to staging
- [ ] E2E testing
- [ ] Performance benchmarking
- [ ] Security audit
- [ ] User acceptance testing

### Phase 7: Production Release (Week 21+)
- [ ] Production deployment
- [ ] Monitoring setup
- [ ] Documentation finalization
- [ ] Training materials
- [ ] Support procedures

---

## Success Criteria

### Technical Metrics
- ✅ >80% test coverage
- ✅ Zero high/critical security vulnerabilities
- ✅ <5 minutes backup time for 1GB database
- ✅ <10 minutes restore time for 1GB database
- ✅ 99.9% backup success rate
- ✅ All CI/CD checks passing

### Operational Metrics
- ✅ Successful migration of 2+ legacy servers
- ✅ Zero data loss incidents
- ✅ <1 hour mean time to recovery (MTTR)
- ✅ Automated deployment to production
- ✅ Complete operational documentation

### Quality Metrics
- ✅ All code reviewed by 1+ team member
- ✅ All security requirements met
- ✅ All performance benchmarks met
- ✅ User documentation complete
- ✅ Zero P0/P1 bugs in production

---

## Risks & Mitigations

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SQLAlchemy complexity | Medium | Medium | Start simple, extensive testing |
| Async I/O bugs | High | Low | Comprehensive integration tests |
| Encryption key loss | Critical | Low | Document key derivation, backup procedures |
| Performance regression | Medium | Medium | Continuous benchmarking |

### Operational Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Migration failures | High | Medium | Thorough testing, rollback plan |
| Data corruption | Critical | Low | Backup verification, checksums |
| Network issues | Medium | Medium | Retry logic, timeout configuration |
| Storage exhaustion | Medium | Low | Monitoring, auto-cleanup |

### Mitigation Strategies
1. **Extensive Testing:** TDD approach, >80% coverage
2. **Gradual Rollout:** Phased migration (dev → staging → prod)
3. **Monitoring:** Prometheus metrics, alerting
4. **Documentation:** Comprehensive runbooks, troubleshooting guides
5. **Rollback Plan:** Quick rollback to legacy system if needed

---

## Dependencies & Prerequisites

### Runtime Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.11"
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
pydantic = "^2.0"
typer = {extras = ["all"], version = "^0.12"}
rich = "^13.0"
cryptography = "^42.0"
prometheus-client = "^0.20"
structlog = "^24.0"
aiofiles = "^24.0"
pymysql = "^1.1"
psycopg = {extras = ["binary"], version = "^3.1"}
# vya_global = {path = "../vya_global", optional = true}  # Biblioteca compartilhada Vya.Digital (se necessário)

# Notas:
# - Cloud storage via Idrive (externo), sem dependências boto3/azure/gcs
# - vya_global é opcional e pode ser usado para compartilhar funções entre projetos
```

### Development Dependencies
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-cov = "^4.1"
pytest-asyncio = "^0.23"
testcontainers = "^4.0"
black = "^24.0"
ruff = "^0.3"
mypy = "^1.8"
bandit = "^1.7"
```

### System Requirements
- **OS:** Linux (Ubuntu 22.04+, Debian 12+, RHEL 9+)
- **Python:** 3.11+
- **Database Clients:** mysql-client, postgresql-client
- **Storage:** Minimum 10GB free space for backups (local)
- **Network:** HTTPS access to databases and monitoring services
- **Cloud Backup:** Idrive pre-installed and configured with scheduler
- **Permissions:** Write access to Idrive sync folder (/var/backups/vya_backupdb/)

---

## References & Related Documents

### Internal Documentation
- [Constitution](./constitution.md) - Project principles and governance
- [ADR-001: SQLAlchemy Selection](../adr/001-sqlalchemy-selection.md)
- [ADR-002: Credential Storage Strategy](../adr/002-credential-storage.md)
- [ADR-003: Monitoring Architecture](../adr/003-monitoring-architecture.md)

### Shared Libraries (Optional)
- [vya_global](../../enterprise-vya_backupbd/usr/local/bin/enterprise/vya_global/) - Biblioteca compartilhada Vya.Digital com funções comuns (FTP, downloads, conversões, notificações Slack, etc.)

### External References
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [12-Factor App Methodology](https://12factor.net/)

### Legacy Codebase
- wfdb02 version: `/vya_backupbd/servers/wfdb02/backup/`
- Enterprise version: `/enterprise-vya_backupbd/usr/local/bin/enterprise/vya_backupbd/`

---

## Glossary

| Term | Definition |
|------|------------|
| **GFS** | Grandfather-Father-Son backup rotation strategy |
| **PITR** | Point-in-Time Recovery - restore to specific timestamp |
| **Fernet** | Symmetric encryption method from cryptography library |
| **ORM** | Object-Relational Mapping - database abstraction layer |
| **TDD** | Test-Driven Development - write tests first approach |
| **SAST** | Static Application Security Testing |
| **DAST** | Dynamic Application Security Testing |
| **MTTR** | Mean Time To Recovery |
| **SLO** | Service Level Objective |
| **SLI** | Service Level Indicator |

---

**Document Version:** 1.0.0  
**Last Updated:** January 9, 2026  
**Next Review:** February 9, 2026  
**Status:** Active  
**Approval:** Yves Marinho - Project Lead
