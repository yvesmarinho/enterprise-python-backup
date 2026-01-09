# VYA BackupDB Constitution
<!-- Sistema Unificado de Backup de Bancos de Dados MySQL e PostgreSQL -->

## 🎯 Missão do Projeto

**Criar uma versão unificada, moderna e escalável do sistema de backup**, consolidando as melhores práticas das versões existentes (wfdb02 avançada + Enterprise base sólida), com foco em segurança, monitoramento e automação.

**Data de Início:** 09 de Janeiro de 2026  
**Versão Target:** 2.0.0  
**Python:** 3.11+ (type hints, async, performance)  
**Licença:** GNU GPL v2.0+  
**Autor:** Yves Marinho - Vya.Digital

---

## Core Principles

### I. Modular Architecture (NON-NEGOTIABLE)
**Sistema modular com separação clara de responsabilidades:**
- Cada módulo deve ser independente e testável isoladamente
- Abstração clara para DBMS (interface comum para MySQL/PostgreSQL)
- Design Patterns obrigatórios: Factory (DBs), Strategy (backup), Observer (notificações)
- Dependency Injection para facilitar testes e extensibilidade
- Type hints completos (Python 3.11+) em todas as funções e classes

**Estrutura de Diretórios Obrigatória:**
```
src/vya_backupbd/
├── core/           # Lógica principal (backup, restore, scheduler, cleanup)
├── db/             # Abstrações DBMS via SQLAlchemy (models, engine, session)
├── security/       # Criptografia, credentials manager, audit
├── monitoring/     # Métricas, tracing, health
├── notifications/  # Email, Slack, webhooks
└── utils/          # Utilitários compartilhados

.secrets/           # Credenciais (GITIGNORED)
└── credentials.json # Credenciais criptografadas (fase inicial)
```

### II. Security-First (CRITICAL)
**Segurança em todas as camadas:**
- **PROIBIDO:** Credenciais em texto plano no código-fonte
- **OBRIGATÓRIO:** Criptografia end-to-end (cryptography/Fernet)
- **OBRIGATÓRIO:** Credenciais em `.secrets/credentials.json` (fase inicial, gitignored)
- **FUTURO:** Migração para Vault (HashiCorp/AWS Secrets Manager/Azure Key Vault)
- **OBRIGATÓRIO:** Sanitização completa de logs (nenhuma senha/secret visível)
- **OBRIGATÓRIO:** Audit log de todas as operações sensíveis
- **OBRIGATÓRIO:** TLS/SSL para conexões com bancos de dados
- Encoding server-based (sem chaves externas no código)
- RBAC (Role-Based Access Control) para operações críticas

### III. Test-First Development (NON-NEGOTIABLE)
**TDD mandatório para todo código novo:**
- Tests escritos → User aprova → Tests falham → Implementação → Tests passam
- Cobertura mínima: >80% (pytest + pytest-cov)
- Testes unitários para cada módulo
- Testes de integração com DBs reais (testcontainers-python)
- Testes E2E automatizados (pytest-bdd)
- Testes de segurança (SAST/DAST)
- CI/CD com GitHub Actions/GitLab CI

### IV. Observability & Monitoring (MANDATORY)
**Monitoramento completo de todas as operações:**
- **Prometheus Metrics** (obrigatório):
  - Counters: backups_total, errors_total, restores_total
  - Gauges: last_backup_status, disk_usage, configured_databases
  - Histograms: backup_duration, restore_duration
  - Summaries: backup_size, restore_size
- **OpenTelemetry** para tracing distribuído (Jaeger)
- **Structured logging** (structlog + ELK Stack)
- **Health checks** automáticos (liveness, readiness)
- **Dashboards Grafana** pré-configurados
- **Alertas inteligentes** baseados em thresholds (AlertManager)

### V. Configuration as Code
**Configuração validada e versionada:**
- **Pydantic** obrigatório para validação de configurações
- **SQLAlchemy** para todas as transações de banco de dados (ORM e Core)
- JSON Schema para validação adicional
- Configurações separadas por ambiente (dev/staging/prod)
- Secrets em `.secrets/credentials.json` (gitignored, fase inicial)
- Versionamento de schemas de configuração
- Migration scripts para mudanças de configuração

### VI. DRY Principle (Don't Repeat Yourself)
**Zero tolerância para código duplicado:**
- Funções `checkFolder()`, `connectDB()`, lógica de dump devem ser unificadas
- Código comum entre wfdb02 e Enterprise deve ser extraído
- Reutilização via composição ao invés de herança quando possível
- Utilities compartilhados em `src/vya_backupbd/utils/`

### VII. Performance & Scalability
**Sistema otimizado para múltiplos servidores:**
- **Async I/O** obrigatório (asyncio, aiofiles, aiohttp)
- **Paralelização** de backups de múltiplos DBs
- **Connection pooling** para DBs (reduce overhead)
- **Streaming** para dumps grandes (não carregar tudo na memória)
- **Rate limiting** configurável para não sobrecarregar servidores
- **Resource limits** (CPU, memória) configuráveis
- **Compression adaptativa** baseada em tamanho do backup

---

## Technical Standards

### Database Support
**DBMS Suportados:**
- MySQL/MariaDB via SQLAlchemy (dialeto mysql+pymysql ou mysql+mysqlconnector)
- PostgreSQL via SQLAlchemy (dialeto postgresql+psycopg)
- **SQLAlchemy** como camada de abstração obrigatória (ORM + Core)
- Suporte a async via SQLAlchemy 2.0+ (async engine e async session)
- Extensível para outros DBMS via drivers SQLAlchemy

**Operações Suportadas:**
- **Backup por Database Individual:** Cada database é backupado em arquivo separado
  - Facilita restore pontual de databases específicos
  - Permite paralelização de backups
  - Reduz impacto de falhas (um backup falho não afeta outros)
- Full backup de database (dados, stored procedures, triggers, views, etc.)
- Incremental backup (futura implementação)
- Point-in-Time Recovery (PITR)
- Restore completo de database individual
- Restore seletivo (tabelas específicas - futuro)
- Verificação de integridade automática por database

### Storage & Retention
**Gestão de Armazenamento:**
- **Armazenamento Local:** Backups gerados em pasta local configurável
  - **Estrutura de Diretórios:** `/backups/{hostname}/{database_id}/{database_name}/YYYY-MM-DD/`
  - Exemplo: `/var/backups/vya_backupdb/wfdb02/prod-mysql-01/mydb/2026-01-09/mydb_20260109_020000.sql.gz`
  - Organização por servidor → instância DB → database → data
  - Facilita localização e restore de databases específicos
- **Cloud Upload:** Idrive (pré-configurado na máquina com scheduler próprio)
  - Sistema gera backups localmente
  - Idrive sincroniza automaticamente com cloud storage
  - Sem dependência de SDKs de cloud (S3, Azure, GCS) no código
- **Compressão:** gzip (nível configurável 1-9) aplicada por database
- **Retenção inteligente:** GFS (Grandfather-Father-Son) por database
  - Daily: últimos 7 dias
  - Weekly: últimas 4 semanas
  - Monthly: últimos 12 meses
  - Política aplicada independentemente para cada database
- **Cleanup local:** Automático de backups expirados baseado em política GFS por database
- **Verificação de integridade:** Checksums (MD5/SHA256) antes do Idrive sincronizar (por arquivo)
- **Deduplicação:** Gerenciada pelo Idrive (futura implementação no código)

### Scheduling System
**Agendamento Avançado:**
- Systemd timers (Linux)
- Cron compatible
- Dias da semana específicos
- Horários configuráveis (timezone aware)
- Interval-based scheduling
- Window de execução (±30min tolerance)
- Fallback em caso de falha no agendamento

### Notification System
**Notificações Múltiplas:**
- Email (SMTP configurável, sucesso para um e-mail, falha para outro e-mail)
- Níveis: SUCCESS, WARNING, ERROR, CRITICAL
- Templates customizáveis
- Retry logic em caso de falha

---

## Security Requirements

### Credentials Management
**Gestão Segura de Credenciais (Evolutiva):**

**Fase 1 - Inicial (MVP):**
- Credenciais em `.secrets/credentials.json` (gitignored)
- Estrutura JSON:
  ```json
  {
    "databases": [
      {
        "id": "db1",
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "username": "encrypted_base64",
        "password": "encrypted_base64",
        "database": "mydb"
      }
    ]
  }
  ```
- Criptografia Fernet para username/password no JSON
- Chave de criptografia derivada do hostname (server-based encoding)
- `.secrets/` adicionado ao `.gitignore`

**Fase 2 - Intermediária:**
- Suporte a variáveis de ambiente
- Suporte a arquivos `.env`
- Validação de permissões de arquivo (0600)

**Fase 3 - Avançada (Futuro):**
- HashiCorp Vault integration
- AWS Secrets Manager
- Azure Key Vault
- Rotação automática de credenciais
- Audit trail de todos os acessos

### Audit & Compliance
**Auditoria Completa:**
- Log de todas as operações CRUD (não se aplica)
- Timestamp + User + Operation + Result
- Immutable audit logs
- Retention: mínimo 90 dias
- Export para SIEM (Splunk, ELK)
- Compliance: LGPD, GDPR ready

### Network Security
**Comunicação Segura:**
- TLS 1.2+ obrigatório para DBs
- Certificate validation obrigatória
- No plain-text passwords over network
- VPN/SSH tunnel support
- Firewall rules documentation

---

## Development Workflow

### Git Workflow
**Branching Strategy:**
- `main` - produção (protected)
- `develop` - desenvolvimento (protected)
- `feature/*` - novas features
- `fix/*` - correções
- `hotfix/*` - correções urgentes
- PRs obrigatórios para merge em `main`/`develop`

### Code Quality Gates
**Verificações Obrigatórias:**
- **Linting:** ruff (fast) ou pylint
- **Formatting:** black (line-length=120)
- **Type checking:** mypy (strict mode)
- **Security:** bandit (SAST)
- **Dependencies:** safety check
- **Coverage:** >80% (pytest-cov)
- **Documentation:** docstrings obrigatórias (Google style)

### CI/CD Pipeline
**Automação Completa:**
```yaml
Pipeline Stages:
1. Lint & Format Check
2. Type Checking (mypy)
3. Security Scan (bandit, safety)
4. Unit Tests (pytest)
5. Integration Tests (testcontainers)
6. Coverage Report (>80%)
7. Build Docker Image
8. Push to Registry
9. Deploy to Staging
10. E2E Tests
11. Deploy to Production (manual approval)
```

### Documentation Standards
**Documentação Obrigatória:**
- README.md completo com Quick Start
- API Documentation (Sphinx + autodoc)
- Architecture Decision Records (ADRs)
- Runbook operacional
- Troubleshooting guide
- Changelog estruturado (Keep a Changelog format)

---

## DevOps Standards

### Containerization
**Docker/Podman:**
- Multi-stage builds (builder + runtime)
- Alpine Linux base (minimal size)
- Non-root user obrigatório
- Health checks no Dockerfile
- Labels para metadata
- Scanning de vulnerabilidades (Trivy)

### Kubernetes Deployment
**Cloud-Native:**
- Helm charts obrigatórios
- Resource limits configurados
- Liveness/Readiness probes
- ConfigMaps + Secrets
- Service Mesh ready (Istio)
- Auto-scaling (HPA)
- StatefulSet para dados persistentes

### Infrastructure as Code
**Automação de Infraestrutura:**
- Terraform para provisionamento
- Ansible para configuração
- GitOps workflow (ArgoCD/FluxCD)
- Environment parity (dev=staging=prod)
- Disaster Recovery plan

---

## Migration Strategy

### Phase 1: Foundation (Sprints 1-2)
- ✅ Análise das versões existentes (COMPLETO)
- Setup do projeto unificado
- Estrutura de diretórios
- Configuração CI/CD básica
- Documentação inicial

### Phase 2: Core Refactoring (Sprints 3-5)
- Abstração DBMS (base, mysql, postgresql)
- Unificação de código duplicado
- Implementação de design patterns
- Validação com Pydantic
- Testes unitários básicos

### Phase 3: Security Enhancement (Sprints 6-7)
- Vault integration
- Criptografia de credenciais
- Audit logging
- Sanitização de logs
- Testes de segurança

### Phase 4: Monitoring & Observability (Sprints 8-9)
- Prometheus metrics completas
- OpenTelemetry tracing
- Dashboards Grafana
- Alerting configurável
- Health checks

### Phase 5: Advanced Features (Sprints 10-12)
- Backup incremental
- PITR (Point-in-Time Recovery)
- Múltiplos destinos (S3, Azure, GCS)
- Deduplicação
- CLI moderna (Typer + Rich)

### Phase 6: Performance & Scale (Sprints 13-14)
- Async I/O completo
- Paralelização
- Connection pooling
- Benchmarks e otimização
- Load testing (Locust)

### Phase 7: DevOps Maturity (Sprints 15-16)
- Containerização completa
- Helm charts
- Ansible playbooks
- Terraform modules
- GitOps setup

### Phase 8: Production Ready (Sprints 17-18)
- Documentação completa
- Testes E2E
- Homologação
- Migração gradual
- Suporte e treinamento

---

## Problem Analysis (From Legacy Versions)

### Critical Issues Identified
**Segurança (Enterprise v0.1.0):**
- ❌ Credenciais em texto plano no JSON
- ❌ Passwords expostos nos logs
- ❌ Sem criptografia de dados sensíveis
- **Solução:** Vault + Fernet + Log sanitization

**Código Duplicado:**
- ❌ Funções `checkFolder()` repetidas
- ❌ Funções `connectDB()` similares
- ❌ Lógica de dump duplicada
- **Solução:** DRY principle + Abstração

**Observação sobre vya_global:**
- ℹ️ `vya_global` (contém `global_functions.py`) é um projeto separado e independente
- ℹ️ Biblioteca compartilhada entre múltiplos projetos da Vya.Digital
- ℹ️ Pode ser instalada como dependência Python (pip/poetry) se necessário
- ℹ️ Decisão de uso no novo projeto será baseada em necessidade real vs. abstração própria

### Strong Points (To Keep)
**Versão wfdb02 (Advanced):**
- ✅ Prometheus metrics bem implementadas
- ✅ Agendamento inteligente (systemd)
- ✅ Encoding server-based seguro
- ✅ Cleanup automático
- ✅ Modo dry-run

**Versão Enterprise (Solid Base):**
- ✅ Código base bem estruturado
- ✅ Teste de conectividade
- ✅ CLI funcional
- ✅ Múltiplos DBMS

---

## Stack Tecnológico Definitivo

### Core
- **Python:** 3.11+ (type hints, performance)
- **ORM:** SQLAlchemy 2.0+ (async support, type hints)
- **Config:** Pydantic v2 (validação)
- **CLI:** Typer + Rich (UX moderna)
- **Async:** asyncio + aiofiles + aiohttp

### Database Drivers
- **ORM:** SQLAlchemy 2.0+ (camada de abstração obrigatória)
- **MySQL:** pymysql (puro Python) ou mysqlclient (C-based, performance)
- **PostgreSQL:** psycopg (psycopg3, sync+async nativo)
- **Connection Pool:** SQLAlchemy built-in pooling

### Security
- **Encryption:** cryptography (Fernet)
- **Vault:** hvac (HashiCorp Vault client)
- **Secrets:** boto3 (AWS), azure-keyvault (Azure)

### Monitoring
- **Metrics:** prometheus-client
- **Tracing:** opentelemetry-api + opentelemetry-sdk
- **Logging:** structlog

### Testing
- **Framework:** pytest + pytest-cov + pytest-asyncio
- **Integration:** testcontainers-python
- **E2E:** pytest-bdd
- **Mocking:** pytest-mock
- **Load:** locust

### DevOps
- **Container:** Docker/Podman
- **Orchestration:** Kubernetes + Helm
- **IaC:** Terraform + Ansible
- **CI/CD:** GitHub Actions

### Storage
- **Local:** pathlib (stdlib), aiofiles (async I/O)
- **Compression:** gzip (stdlib)
- **Cloud Sync:** Idrive (externo, pré-configurado no sistema)
- **Checksums:** hashlib (stdlib - MD5/SHA256)

---

## Governance

### Constitution Authority
- Esta constituição supersede todas as outras práticas e guias
- Amendments requerem aprovação e migration plan
- Todos os PRs/reviews devem verificar compliance
- Exceções devem ser documentadas e justificadas

### Code Review Requirements
- Mínimo 1 aprovação para features
- Mínimo 2 aprovações para mudanças críticas
- Security changes requerem aprovação do security lead
- Todos os comentários devem ser resolvidos

### Quality Gates
- Todos os testes devem passar (0 failures)
- Coverage >80% obrigatório
- Security scan sem critical/high issues
- Performance benchmarks não podem regredir >10%

### Deprecation Policy
- Aviso prévio de 2 releases para breaking changes
- Migration guide obrigatório
- Suporte de backward compatibility por 6 meses

---

**Version:** 1.0.0  
**Ratified:** 09 de Janeiro de 2026  
**Last Amended:** 09 de Janeiro de 2026  
**Next Review:** 09 de Abril de 2026 (quarterly)
