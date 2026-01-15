# Vya BackupDB - Sistema de Backup de Bancos de Dados e Arquivos

## 📋 Visão Geral do Projeto

Sistema automatizado de backup e restore para bancos de dados MySQL, PostgreSQL e **arquivos/diretórios**, desenvolvido para ambientes enterprise com suporte a múltiplos servidores, notificações, agendamento e monitoramento via Prometheus.

**Data de Início da Nova Versão:** 9 de Janeiro de 2026  
**Versão Atual Analisada:** 2.0.0  
**Linguagem:** Python 3.12+  
**Licença:** GNU GPL v2.0+  
**Autor:** Yves Marinho - Vya.Digital  

---

## 📁 Estrutura do Workspace

> ⚠️ **IMPORTANTE**: Este workspace contém múltiplos diretórios. Apenas um é o projeto ativo.

**Projeto Ativo** (desenvolvimento atual):
- 📂 `enterprise-python-backup/` ← **VOCÊ ESTÁ AQUI**
  - Branch: `001-phase2-core-development`
  - Nova implementação seguindo metodologia Spec Kit
  - Documentação: `specs/001-phase2-core-development/`
  - **Todos os commits devem ser feitos neste repositório**

**Diretórios de Referência** (⛔ NÃO MODIFICAR):
- 📂 `../python_backup/` - Codebase legado para consulta
- 📂 `../enterprise-python_backup/` - Scripts em produção para consulta

Estes diretórios contêm código existente para análise e referência durante o desenvolvimento da nova versão, mas **não devem ser modificados** durante o desenvolvimento do Phase 2.

---

## 🎯 Objetivo da Nova Versão

Criar uma versão unificada, moderna e escalável do sistema de backup, consolidando as melhores práticas e funcionalidades das versões existentes, com melhorias em:

- ✅ Arquitetura modular e escalável
- ✅ Segurança (credenciais criptografadas)
- ✅ Monitoramento (Prometheus/Grafana)
- ✅ Gestão de agendamento inteligente
- ✅ Suporte a múltiplos servidores
- ✅ Testes automatizados
- ✅ Documentação completa
- ✅ Sistema de cleanup automatizado
- ✅ Suporte a containers
- ✅ **Backup de arquivos e diretórios com glob patterns**

---

## ✨ Funcionalidades Principais

### 🗄️ Backup de Bancos de Dados
- **MySQL**: Backup completo com mysqldump
- **PostgreSQL**: Backup completo com pg_dump  
- Compressão ZIP automática
- Restore com filtragem SQL inteligente
- Suporte a múltiplas instâncias

### 📁 Backup de Arquivos (NOVO em v2.0.0)
- **Glob Patterns**: Use `*`, `**`, `{}` para seleção flexível
- **Compressão tar.gz**: Automática com preservação de estrutura
- **Docker Volumes**: Backup de volumes Docker
- **Configurações**: Backup de arquivos de configuração do sistema
- **Uploads**: Backup de arquivos enviados por usuários
- **Restore Flexível**: Restaure para localização original ou customizada

**Exemplo de configuração**:
```json
{
  "id_dbms": 3,
  "dbms": "files",
  "host": "localhost",
  "port": 0,
  "db_list": [
    "/docker/volumes/**/*",
    "/opt/app/config/*.{yaml,json}",
    "/var/www/uploads/**/*.{jpg,png,pdf}"
  ],
  "enabled": true
}
```

**Comandos**:
```bash
# Backup de arquivos
vya-backupdb backup --instance 3

# Listar backups de arquivos
vya-backupdb restore-list --instance 3

# Restaurar para localização customizada
vya-backupdb restore --file backup.tar.gz --target /tmp/restored
```

📖 **Guia Completo**: [docs/guides/FILES_BACKUP_GUIDE.md](docs/guides/FILES_BACKUP_GUIDE.md)

### 📧 Notificações
- Email automático em caso de sucesso ou falha
- **Detalhes completos** no corpo do email (erros, stack traces, estatísticas)
- **Anexo automático** do arquivo de log em caso de falha
- Templates HTML profissionais
- Suporte SMTP/SSL/TLS

### 🔄 Retenção e Limpeza
- Políticas de retenção configuráveis (dias)
- Limpeza automática de backups antigos
- Dry-run mode para testes seguros
- Relatórios detalhados de espaço liberado

### 📊 Monitoramento
- Métricas Prometheus
- Logs detalhados com sanitização de senhas
- Status de saúde do sistema
- Rastreamento de operações

---

## 📊 Análise dos Códigos Antigos

### 🔍 Versões Identificadas

Foram identificadas **duas versões principais** do sistema:

#### **1. Versão wfdb02 (Servidor Específico)**
- **Localização:** `/python_backup/servers/wfdb02/backup/`
- **Versão:** Não especificada
- **Características:**
  - ✅ Implementação mais moderna com módulo Prometheus
  - ✅ Sistema de agendamento avançado
  - ✅ Segurança aprimorada (encoding server-based)
  - ✅ Configuração em JSON estruturado
  - ✅ Suporte a systemd (timer e services)
  - ✅ Scripts de instalação automatizados
  - ✅ Modo dry-run para testes
  - ✅ Limpeza automática de backups antigos

#### **2. Versão Enterprise (Genérica)**
- **Localização:** `/enterprise-python_backup/usr/local/bin/enterprise/python_backup/`
- **Versão:** 0.1.0
- **Características:**
  - ⚠️ Versão mais antiga porém com código base sólido
  - ⚠️ Credenciais em texto plano no JSON
  - ✅ Teste de conectividade implementado
  - ✅ Múltiplos caminhos para global_functions
  - ✅ Suporte a MySQL e PostgreSQL
  - ⚠️ Menos recursos de monitoramento
  - ⚠️ Configuração mais simples

---

## 🏗️ Estrutura Atual dos Códigos

### Arquivos Principais

| Arquivo | Versão wfdb02 | Versão Enterprise | Função |
|---------|---------------|-------------------|--------|
| **python_backup.py** | 374 linhas | 411 linhas | Script principal |
| **backup_control.py** | 605 linhas | 601 linhas | Módulo de backup |
| **restore.py** | ✅ Existe | ✅ Existe | Módulo de restore |
| **prometheus_metrics.py** | ✅ Existe | ❌ Não existe | Métricas Prometheus |
| **python_backup.json** | 101 linhas | 60 linhas | Configuração |
| **requirements.txt** | ✅ | ✅ | Dependências |

### Módulos e Dependências

#### Dependências Python Identificadas:
```
certifi==2022.12.7
charset-normalizer==3.1.0
idna==3.4
mysql-connector==2.2.9
pexpect==4.8.0
psycopg2-binary==2.9.6
ptyprocess==0.7.0
requests==2.28.2
slack-webhook==1.0.7
urllib3==1.26.15
wget==3.2
```

#### Dependências de Sistema:
- `mysqldump` (MySQL)
- `pg_dump` (PostgreSQL)
- Python 3.11+
- Ambiente virtual Python

---

## 🔧 Funcionalidades Implementadas

### ✅ Versão wfdb02 (Mais Completa)

1. **Backup Avançado**
   - Suporte MySQL e PostgreSQL
   - Backup incremental
   - Compressão ZIP automática
   - Validação de integridade
   - Cleanup automático (max_backup_age_days: 30)

2. **Segurança**
   - Credenciais criptografadas
   - Encoding server-based
   - Sem chaves externas (no_external_keys: true)
   - Conexões seguras obrigatórias

3. **Agendamento**
   - Timer systemd
   - Configuração de dias da semana
   - Horário específico (02:30)
   - Timezone configurável (America/Sao_Paulo)
   - Intervalo entre backups (1440 min = 24h)

4. **Monitoramento**
   - Métricas Prometheus
   - Integração Grafana
   - Logs detalhados (INFO/DEBUG)
   - Notificações Slack e E-mail

5. **DevOps**
   - Scripts de instalação
   - Configuração automática de permissões
   - Diagnóstico de ambiente virtual
   - Testes de sistema

### ⚙️ Versão Enterprise (Base Sólida)

1. **Funcionalidades Core**
   - Backup MySQL e PostgreSQL
   - Restore de backups
   - Modo dry-run (teste de conectividade)
   - Teste de e-mail
   - Argumentos via CLI

2. **Configuração**
   - JSON estruturado
   - Múltiplas configurações de DB
   - Ambiente DEV/PRD separado
   - DB ignore (exclusão de schemas)

3. **Logging**
   - Logs em arquivo e console
   - Níveis configuráveis (INFO/DEBUG)
   - Traceback completo de erros

---

## 🚨 Problemas Identificados

### Críticos

1. **Segurança (Enterprise)**
   - ❌ Credenciais em texto plano no JSON
   - ❌ Passwords expostos nos logs
   - ❌ Sem criptografia de dados sensíveis

2. **Dependência de global_functions**
   - ⚠️ Arquivo externo não incluído no projeto
   - ⚠️ Múltiplos caminhos hardcoded
   - ⚠️ Pode causar falhas se não encontrado

3. **Versionamento**
   - ⚠️ Sem controle de versão adequado
   - ⚠️ Histórico de modificações apenas em comentários
   - ⚠️ Falta de changelog estruturado

### Médios

4. **Código Duplicado**
   - 🔄 Funções `checkFolder()` repetidas
   - 🔄 Funções `connectDB()` similares
   - 🔄 Lógica de dump duplicada

5. **Gestão de Erros**
   - ⚠️ Alguns erros não tratados adequadamente
   - ⚠️ Raises genéricos (ConnectionError, RuntimeError)
   - ⚠️ Falta validação de entrada

6. **Configuração**
   - ⚠️ Paths hardcoded em alguns locais
   - ⚠️ Falta validação de JSON
   - ⚠️ Configurações inconsistentes entre versões

### Menores

7. **Documentação**
   - 📝 TODOs não resolvidos
   - 📝 Comentários misturados (PT/EN)
   - 📝 Falta docstrings em algumas funções

8. **Testes**
   - ⚠️ Testes unitários limitados
   - ⚠️ Falta cobertura de código
   - ⚠️ Testes de integração inexistentes

9. **Performance**
   - ⚠️ Subprocess.check_output pode bloquear
   - ⚠️ Sem limite de memória para dumps grandes
   - ⚠️ Falta paralelização para múltiplos DBs

---

## 📈 Pontos Fortes

### Arquitetura
- ✅ Separação clara em módulos
- ✅ Configuração externa em JSON
- ✅ Suporte a múltiplos DBMS
- ✅ Modular e extensível

### Operacional
- ✅ Logging robusto
- ✅ Notificações múltiplas (Email/Slack)
- ✅ Modo dry-run para testes
- ✅ Cleanup automático
- ✅ Integração systemd

### Monitoramento (wfdb02)
- ✅ Métricas Prometheus
- ✅ Dashboard Grafana
- ✅ Alertas configuráveis

### Segurança (wfdb02)
- ✅ Credenciais criptografadas
- ✅ Encoding baseado no servidor
- ✅ Sem dependência de chaves externas

---

## 🛠️ Melhorias Propostas para Nova Versão

### 1. Arquitetura e Código

- [ ] **Unificar as duas versões** em uma única base de código
- [ ] **Remover código duplicado** (DRY principle)
- [ ] **Implementar design patterns** (Factory para DBs, Strategy para backup)
- [ ] **Adicionar type hints** completos (Python 3.11+)
- [ ] **Criar abstração para DBMS** (interface comum)
- [ ] **Implementar dependency injection** para global_functions
- [ ] **Adicionar validação de configuração** (Pydantic)

### 2. Segurança

- [ ] **Criptografia end-to-end** para todas as credenciais
- [ ] **Vault integration** (HashiCorp Vault, AWS Secrets Manager)
- [ ] **Audit log** de todas as operações
- [ ] **Sanitização de logs** (remover senhas completamente)
- [ ] **TLS/SSL** obrigatório para conexões DB
- [ ] **RBAC** (Role-Based Access Control)
- [ ] **Rotação automática de credenciais**

### 3. Monitoramento e Observabilidade

- [ ] **OpenTelemetry** para traces distribuídos
- [ ] **Métricas detalhadas** (tamanho, tempo, taxa de sucesso)
- [ ] **Health checks** automáticos
- [ ] **Dashboards Grafana** pré-configurados
- [ ] **Alertas inteligentes** (baseado em thresholds)
- [ ] **SLO/SLI** (Service Level Objectives/Indicators)

### 4. Testes

- [ ] **Testes unitários** (pytest, >80% coverage)
- [ ] **Testes de integração** com DBs reais
- [ ] **Testes E2E** automatizados
- [ ] **Testes de performance** (benchmarking)
- [ ] **Testes de segurança** (SAST/DAST)
- [ ] **CI/CD pipeline** (GitHub Actions, GitLab CI)

### 5. DevOps e Deployment

- [ ] **Containerização** (Docker/Podman)
- [ ] **Helm charts** para Kubernetes
- [ ] **Ansible playbooks** para deployment
- [ ] **Terraform** para infraestrutura
- [ ] **Multi-stage builds** otimizados
- [ ] **Health checks** em containers

### 6. Funcionalidades

- [ ] **Backup incremental** e diferencial
- [ ] **Backup de múltiplos servidores** em paralelo
- [ ] **Restore point-in-time** (PITR)
- [ ] **Verificação de integridade** automática
- [ ] **Compressão adaptativa** (baseada em tamanho)
- [ ] **Retenção inteligente** (GFS - Grandfather-Father-Son)
- [ ] **Deduplicação** de dados
- [ ] **Backup para múltiplos destinos** (local, S3, Azure, GCS)

### 7. Interface e UX

- [ ] **CLI moderna** (Typer, Rich)
- [ ] **Web UI** para gestão (FastAPI + React)
- [ ] **API REST** completa
- [ ] **Webhooks** para eventos
- [ ] **Documentação interativa** (Swagger/OpenAPI)

### 8. Performance

- [ ] **Paralelização** de backups
- [ ] **Async I/O** (asyncio, aiofiles)
- [ ] **Connection pooling** para DBs
- [ ] **Streaming** de grandes dumps
- [ ] **Rate limiting** configurável
- [ ] **Resource limits** (CPU, memória)

### 9. Operacional

- [ ] **Auto-recovery** de falhas
- [ ] **Circuit breaker** pattern
- [ ] **Retry mechanism** exponencial
- [ ] **Graceful shutdown**
- [ ] **Zero-downtime deployment**
- [ ] **Rollback automático**

### 10. Documentação

- [ ] **README completo** com exemplos
- [ ] **Documentação técnica** (MkDocs)
- [ ] **API documentation** (Sphinx)
- [ ] **Runbook** operacional
- [ ] **Troubleshooting guide**
- [ ] **Architecture Decision Records** (ADRs)
- [ ] **Changelog** estruturado (Keep a Changelog)

---

## 📋 Roadmap da Nova Versão

### Fase 1: Consolidação (Sprint 1-2)
- [ ] Análise completa dos códigos existentes ✅
- [ ] Definição da arquitetura target
- [ ] Setup do repositório (Git, estrutura)
- [ ] Configuração CI/CD básica
- [ ] Documentação inicial ✅

### Fase 2: Core Refactoring (Sprint 3-5)
- [ ] Unificação do código base
- [ ] Implementação de abstrações
- [ ] Remoção de código duplicado
- [ ] Testes unitários básicos
- [ ] Validação de configuração (Pydantic)

### Fase 3: Segurança (Sprint 6-7)
- [ ] Implementação de criptografia
- [ ] Vault integration
- [ ] Audit logging
- [ ] Sanitização de logs
- [ ] Testes de segurança

### Fase 4: Monitoramento (Sprint 8-9)
- [ ] Métricas Prometheus avançadas
- [ ] OpenTelemetry
- [ ] Dashboards Grafana
- [ ] Alertas configuráveis
- [ ] Health checks

### Fase 5: Features Avançadas (Sprint 10-12)
- [ ] Backup incremental
- [ ] PITR
- [ ] Múltiplos destinos
- [ ] Deduplicação
- [ ] Web UI

### Fase 6: Performance e Escala (Sprint 13-14)
- [ ] Paralelização
- [ ] Async I/O
- [ ] Connection pooling
- [ ] Benchmark e otimização

### Fase 7: DevOps (Sprint 15-16)
- [ ] Containerização
- [ ] Kubernetes/Helm
- [ ] Ansible/Terraform
- [ ] CI/CD completo
- [ ] Auto-scaling

### Fase 8: Produção (Sprint 17-18)
- [ ] Documentação completa
- [ ] Testes E2E
- [ ] Homologação
- [ ] Migração gradual
- [ ] Suporte e manutenção

---

## 🔧 Stack Tecnológico Proposto

### Backend
- **Python:** 3.11+ (type hints, async, performance)
- **Framework:** FastAPI (API REST)
- **CLI:** Typer + Rich (interface moderna)
- **Config:** Pydantic (validação)
- **DB Drivers:** mysql-connector-python, psycopg3

### Segurança
- **Secrets:** HashiCorp Vault / AWS Secrets Manager
- **Encryption:** cryptography (Fernet)
- **Auth:** JWT + OAuth2

### Monitoramento
- **Metrics:** Prometheus + Grafana
- **Tracing:** OpenTelemetry + Jaeger
- **Logging:** structlog + ELK Stack

### Testes
- **Unit:** pytest + pytest-cov
- **Integration:** testcontainers-python
- **E2E:** pytest-bdd
- **Load:** locust

### DevOps
- **Container:** Docker / Podman
- **Orchestration:** Kubernetes + Helm
- **IaC:** Terraform + Ansible
- **CI/CD:** GitHub Actions / GitLab CI

### Documentação
- **API:** Swagger/OpenAPI
- **Docs:** MkDocs + Material theme
- **Code:** Sphinx + autodoc

---

## 📝 Comandos de Uso Atual

### Versão Enterprise
```bash
# Backup
/usr/local/bin/enterprise/python_backup/python_backup.py -b

# Backup com dry-run (teste)
/usr/local/bin/enterprise/python_backup/python_backup.py -b -d

# Restore
/usr/local/bin/enterprise/python_backup/python_backup.py -r 20210922_162528_asterisk.zip

# Teste de e-mail
/usr/local/bin/enterprise/python_backup/python_backup.py -t
```

### Versão wfdb02 (Systemd)
```bash
# Status do serviço
systemctl status vya-backup-wfdb02.timer
systemctl status vya-backup-wfdb02.service

# Executar manualmente
systemctl start vya-backup-wfdb02-oneshot.service

# Ver logs
journalctl -u vya-backup-wfdb02.service -f
```

---

## 📂 Estrutura de Diretórios Proposta

```
vya-backupdb-v2/
├── src/
│   ├── vya_backupdb/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── cli.py                 # CLI com Typer
│   │   ├── config.py              # Configuração com Pydantic
│   │   ├── core/
│   │   │   ├── backup.py          # Core backup logic
│   │   │   ├── restore.py         # Core restore logic
│   │   │   ├── scheduler.py       # Agendamento
│   │   │   └── cleanup.py         # Limpeza
│   │   ├── db/
│   │   │   ├── base.py            # Interface DB abstrata
│   │   │   ├── mysql.py           # MySQL implementation
│   │   │   └── postgresql.py     # PostgreSQL implementation
│   │   ├── security/
│   │   │   ├── encryption.py     # Criptografia
│   │   │   ├── vault.py          # Vault integration
│   │   │   └── audit.py          # Audit log
│   │   ├── monitoring/
│   │   │   ├── metrics.py        # Prometheus metrics
│   │   │   ├── tracing.py        # OpenTelemetry
│   │   │   └── health.py         # Health checks
│   │   ├── notifications/
│   │   │   ├── email.py          # Email notifier
│   │   │   ├── slack.py          # Slack notifier
│   │   │   └── webhook.py        # Generic webhook
│   │   └── utils/
│   │       ├── logging.py        # Logging setup
│   │       ├── filesystem.py     # File operations
│   │       └── validators.py     # Validações
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── architecture/
│   ├── api/
│   └── operations/
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── kubernetes/
│   │   └── helm/
│   ├── ansible/
│   └── terraform/
├── config/
│   ├── config.schema.json
│   └── config.example.json
├── scripts/
│   ├── install.sh
│   └── migrate.sh
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
└── .gitignore
```

---

## 🤝 Contribuindo

A nova versão será desenvolvida com práticas modernas de desenvolvimento:

- **Git Flow** para branches
- **Conventional Commits** para mensagens
- **Pull Requests** com review obrigatório
- **Testes automatizados** em CI/CD
- **Code coverage** mínimo de 80%
- **Linting** automático (ruff, black, mypy)

---

## 📄 Licença

GNU General Public License v2.0 or above

---

## 👤 Autor

**Yves Marinho**  
Vya.Digital  
Copyright (c) 2019-2026

---

## 📞 Suporte

Para suporte e dúvidas:
- Email: admin@vya.digital
- Email: atendimento@vya.digital

---

**Última atualização:** 9 de Janeiro de 2026  
**Documento:** Análise inicial e planejamento da nova versão  
**Status:** Em desenvolvimento ativo 🚀

# VYA Backup Database - Sistema Completo de Backup e Restore

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Sistema automatizado e robusto para backup e restauração de bancos de dados PostgreSQL e MySQL com suporte a múltiplos servidores, agendamento inteligente e segurança avançada.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Principais Características](#principais-características)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Operações de Backup](#operações-de-backup)
- [Operações de Restore](#operações-de-restore)
- [Sistema de Templates](#sistema-de-templates)
- [Monitoramento](#monitoramento)
- [Troubleshooting](#troubleshooting)
- [Documentação Completa](#documentação-completa)

## 🎯 Visão Geral

O **VYA Backup Database** é uma solução empresarial completa para gerenciamento de backups de bancos de dados, desenvolvida para ambientes de produção que exigem alta confiabilidade, segurança e facilidade de operação.

### Por que usar o VYA Backup DB?

- ✅ **Backup Automatizado**: Agendamento inteligente com dias da semana e horários específicos
- ✅ **Multi-Database**: Suporte nativo para PostgreSQL e MySQL no mesmo sistema
- ✅ **Segurança Avançada**: Senhas criptografadas com SHA256 + Base64 sem dependência de chaves externas
- ✅ **Restore Facilitado**: Sistema automatizado de restauração com validação e rollback
- ✅ **Sistema de Templates**: Geração rápida de configurações para múltiplos servidores
- ✅ **Monitoramento Integrado**: Métricas Prometheus e logs estruturados
- ✅ **Compatibilidade de Versões**: Suporte a upgrades entre versões do PostgreSQL (ex: 16 → 18)

## 🚀 Principais Características

### Backup Inteligente

- **Backup Completo de Cluster**: Inclui usuários, roles e objetos globais (PostgreSQL)
- **Backup Seletivo**: Por banco, por SGBD ou com filtros personalizados
- **Compressão Automática**: Suporte a múltiplos formatos (SQL, Custom, Tar, Directory)
- **Retenção Configurável**: Limpeza automática de backups antigos
- **Backup Incremental**: Suporte via WAL archiving (PostgreSQL)

### Restore Robusto

- **Detecção Automática de Formato**: Identifica automaticamente o tipo de backup
- **Validação Pré-Restore**: Verifica integridade e compatibilidade antes de restaurar
- **Restauração com Rollback**: Cria backup de segurança antes de aplicar restore
- **Restore Seletivo**: Por tabela, por schema ou por banco específico
- **Tratamento de Erros**: Remove automaticamente comandos DROP problemáticos

### Segurança e Compliance

- **Criptografia de Senhas**: SHA256 + Base64 baseado em identificador único do servidor
- **Sem Chaves Externas**: Segurança sem dependência de arquivos de chave
- **Auditoria Completa**: Logs detalhados de todas as operações
- **Permissões Granulares**: Usuários dedicados com privilégios mínimos necessários
- **Autenticação Segura**: Suporte a .pgpass, md5, scram-sha-256

### Automação e Escalabilidade

- **Sistema de Templates**: Gere configurações para N servidores rapidamente
- **Agendamento Flexível**: Dias da semana, horários e timezone configuráveis
- **Execução Paralela**: Restore paralelo com múltiplos jobs (PostgreSQL)
- **Integração CI/CD**: Scripts prontos para automação
- **Systemd Integration**: Serviços systemd para execução contínua

## 🏗️ Arquitetura do Sistema

```
enterprise-python-backup/
├── src/                              # Código fonte (templates)
│   ├── modules/
│   │   ├── backup_control.py.template    # Controlador de backup
│   │   ├── restore.py.template           # Controlador de restore
│   │   └── prometheus_metrics.py         # Métricas
│   ├── python_backup.py.template         # Aplicação principal
│   └── create_secure_config.py          # Gerador de configurações
│
├── servers/                          # Instâncias por servidor
│   ├── wf004/                       # Exemplo: servidor wf004
│   │   ├── modules/                 # Módulos compilados
│   │   ├── python_backup.py         # Script principal
│   │   ├── python_backup.json       # Configuração do servidor
│   │   └── systemd/                # Serviços systemd
│   └── [outros_servidores]/
│
├── docs/                            # Documentação
│   ├── Postgres Backup Completo Metodos.md
│   ├── Postgres erro no restore.md
│   └── [outros_docs]/
│
├── docs_sphinx/                     # Documentação Sphinx
│   ├── usage/
│   │   ├── backup_operations.md
│   │   ├── restore_operations.md
│   │   └── [outros_guias]/
│   └── configuration/
│
└── Makefile                         # Automação de build
```

### Fluxo de Operação

```
┌─────────────────┐
│ Template System │ ──┐
└─────────────────┘   │
                       ▼
┌─────────────────────────────────────────┐
│ make generate SERVER=novo_servidor     │
│ - Copia templates                       │
│ - Aplica configurações específicas      │
│ - Gera scripts de instalação           │
└─────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│ make config-secure SERVER=novo_servidor│
│ - Interface interativa                  │
│ - Validação de senhas                   │
│ - Criptografia automática              │
└─────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│ Systemd Service                         │
│ - Execução em modo daemon               │
│ - Restart automático em falhas          │
│ - Logs centralizados                    │
└─────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│ Backup Scheduler                        │
│ - Verifica dia da semana               │
│ - Verifica horário (±30 min tolerância)│
│ - Executa backup se permitido          │
└─────────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐     ┌──────────────────┐
│ MySQL Backup     │     │ PostgreSQL Backup│
│ - mysqldump      │     │ - pg_dump        │
│ - Compressão     │     │ - pg_dumpall     │
└──────────────────┘     └──────────────────┘
         │                           │
         └─────────────┬─────────────┘
                       ▼
┌─────────────────────────────────────────┐
│ Arquivo ZIP com timestamp               │
│ - Múltiplos dumps SQL                   │
│ - Metadados do backup                   │
│ - Compressão otimizada                  │
└─────────────────────────────────────────┘
```

## 📦 Requisitos

### Sistema Operacional

- Debian 12 (Bookworm) ou superior
- Ubuntu 22.04 LTS ou superior
- Outras distribuições Linux compatíveis com systemd

### Software

- **Python**: 3.9 ou superior
- **PostgreSQL**: 16+ (16, 17, 18 testados)
- **MySQL/MariaDB**: 8.0+ ou MariaDB 10.6+
- **Ferramentas de Linha de Comando**:
  - `pg_dump`, `pg_dumpall`, `pg_restore`, `psql`
  - `mysqldump`, `mysql`
  - `tar`, `gzip`

### Dependências Python

```bash
# Criar ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

**requirements.txt:**
```txt
psycopg2-binary>=2.9.9
mysql-connector-python>=8.2.0
python-dateutil>=2.8.2
prometheus-client>=0.19.0
```

### Hardware Mínimo

- **CPU**: 2 cores
- **RAM**: 2 GB (4 GB recomendado)
- **Disco**: Dependente do tamanho dos bancos de dados
  - Fórmula: `(Tamanho total dos DBs × 2) + 10 GB para sistema`

## 📥 Instalação

### Instalação Rápida (5 minutos)

```bash
# 1. Clone o repositório
git clone https://github.com/vyatechnologies/enterprise-python-backup.git
cd enterprise-python-backup

# 2. Gerar servidor de teste
make generate SERVER=quickstart \
  COMPANY="Minha Empresa" \
  AUTHOR="Seu Nome" \
  SERVER_LOCATION="Datacenter Principal"

# 3. Configurar credenciais de forma segura
cd servers/quickstart
make config

# 4. Executar primeiro backup
python3 -m python_backup

# 5. Verificar resultado
ls -lh backups/
```

### Instalação para Produção

```bash
# 1. Preparar sistema
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
  postgresql-client mysql-client make

# 2. Criar usuários de banco de dados
# PostgreSQL
sudo -u postgres psql << 'EOF'
CREATE ROLE backup_user WITH
  LOGIN
  SUPERUSER
  PASSWORD 'senha_segura_aqui';
COMMENT ON ROLE backup_user IS 'Usuário para backups automáticos';
EOF

# MySQL
mysql -u root -p << 'EOF'
CREATE USER 'backup_user'@'localhost' IDENTIFIED BY 'senha_segura_aqui';
GRANT SELECT, SHOW VIEW, LOCK TABLES, RELOAD ON *.* TO 'backup_user'@'localhost';
FLUSH PRIVILEGES;
EOF

# 3. Gerar configuração do servidor
make generate SERVER=producao_01

# 4. Configurar sistema
cd servers/producao_01
make config-secure

# 5. Instalar como serviço systemd
sudo ./install_producao_01_backup_service.sh

# 6. Verificar status
sudo systemctl status vya-backup-producao_01.service
```

## ⚙️ Configuração

### Configuração via Interface Interativa (Recomendado)

```bash
cd servers/seu_servidor
make config
```

A interface interativa irá solicitar:

1. **Nome do servidor**: Identificador único
2. **Localização**: Descrição física/lógica do servidor
3. **Autor**: Responsável pela configuração
4. **MySQL**:
   - Host (localhost ou IP)
   - Usuário
   - Senha (com confirmação)
5. **PostgreSQL**:
   - Host
   - Usuário
   - Senha (com confirmação)
6. **Agendamento**:
   - Dias da semana (0=Segunda, 6=Domingo)
   - Horário (HH:MM)
   - Timezone

### Configuração Manual

Edite `python_backup.json`:

```json
{
  "server_info": {
    "server_name": "producao_01",
    "location": "Datacenter SP",
    "author": "Admin",
    "company": "Minha Empresa"
  },
  "schedule": {
    "enabled": true,
    "weekdays": [0, 1, 2, 3, 4],
    "time": "02:30",
    "timezone": "America/Sao_Paulo",
    "tolerance_minutes": 30
  },
  "databases": {
    "mysql": {
      "enabled": true,
      "host": "localhost",
      "port": 3306,
      "user": "backup_user",
      "password_encrypted": "aGFzaF9kYV9zZW5oYV9hcXVp"
    },
    "postgresql": {
      "enabled": true,
      "host": "localhost",
      "port": 5432,
      "user": "backup_user",
      "password_encrypted": "aGFzaF9kYV9zZW5oYV9hcXVp"
    }
  },
  "paths": {
    "backup_path": "/backup/vya_backupdb",
    "zip_path": "/backup/vya_backupdb/archives",
    "log_path": "/var/log/vya_backupdb"
  },
  "backup_options": {
    "compress": true,
    "retention_days": 30,
    "create_zip": true
  }
}
```

### Criptografia de Senhas

O sistema usa criptografia baseada em SHA256 + Base64 vinculada ao nome do servidor:

```python
# Criptografar senha manualmente
from modules.backup_control import BackupController

# Substitua pelos valores reais
server_name = "producao_01"
plain_password = "minha_senha_segura"

encrypted = BackupController.encrypt_password(plain_password, server_name)
print(f"Senha criptografada: {encrypted}")
```

## 🎯 Uso

### Backup Manual

```bash
# Backup de todos os bancos configurados
python3 -m python_backup

# Backup apenas de um SGBD
python3 -m python_backup --dbms mysql
python3 -m python_backup --dbms postgresql

# Backup forçado (ignora agendamento)
python3 -m python_backup --force

# Modo debug
python3 -m python_backup --debug
```

### Restore Manual

```bash
# Restaurar backup específico
python3 modules/restore.py --file backups/arquivo_backup.zip

# Restaurar com confirmação interativa
python3 modules/restore.py --interactive

# Restaurar banco específico
python3 modules/restore.py \
  --file backups/mysql_database1_20250116_143022.sql \
  --target database1

# Restaurar com recriação do banco (PostgreSQL)
python3 modules/restore.py \
  --file backups/postgresql_webapp_20250116.sql \
  --recreate \
  --owner app_user
```

### Verificação de Agendamento

```bash
# Testar se o backup seria executado agora
python3 test_schedule_system.py

# Saída esperada:
# ✅ Backup seria executado:
#    - Dia da semana: Permitido
#    - Horário: Dentro da janela (02:00-03:00)
```

### Comandos Makefile

```bash
# Ver todos os comandos disponíveis
make help

# Gerar novo servidor
make generate SERVER=novo_servidor

# Configurar servidor existente
make config-secure SERVER=servidor

# Instalar como serviço
make install SERVER=servidor

# Executar backup
make backup SERVER=servidor

# Ver logs
make logs SERVER=servidor

# Limpar arquivos temporários
make clean
```

## 💾 Operações de Backup

### Tipos de Backup

#### 1. Backup Completo (Padrão)

Faz backup de:
- Todos os bancos de dados MySQL configurados
- Todos os bancos de dados PostgreSQL configurados
- Objetos globais do PostgreSQL (usuários, roles, tablespaces)

```bash
python3 -m python_backup
```

#### 2. Backup Seletivo por SGBD

```bash
# Apenas MySQL
python3 -m python_backup --dbms mysql

# Apenas PostgreSQL
python3 -m python_backup --dbms postgresql
```

#### 3. Backup com Filtros

Configure no `python_backup.json`:

```json
{
  "backup_filters": {
    "mysql": {
      "included_databases": ["app_prod", "user_data"],
      "excluded_databases": ["temp_db", "cache_db"]
    },
    "postgresql": {
      "included_schemas": ["public", "reports"],
      "excluded_tables": ["log_*", "temp_*"]
    }
  }
}
```

### Estrutura de Arquivos de Backup

```
backups/
├── arquivo_20250116_143022.zip
│   ├── mysql_database1_20250116_143022.sql
│   ├── mysql_database2_20250116_143025.sql
│   ├── postgresql_globals_20250116_143030.sql
│   ├── postgresql_webapp_20250116_143035.sql
│   └── backup_metadata.json
└── logs/
    └── backup_20250116_143022.log
```

### Monitoramento de Backup

```bash
# Ver logs em tempo real
tail -f /var/log/vya_backupdb/backup.log

# Ver últimos backups realizados
ls -lht backups/ | head -n 10

# Verificar tamanho dos backups
du -sh backups/

# Estatísticas de backup
python3 -c "
from modules.backup_control import BackupController
bc = BackupController('python_backup.json')
bc.print_backup_statistics()
"
```

## 🔄 Operações de Restore

### Tipos de Restore

#### 1. Restore Completo

Substitui completamente o banco de dados de destino.

```bash
python3 modules/restore.py \
  --file backups/mysql_database1_20250116_143022.sql \
  --type complete \
  --target database1
```

#### 2. Restore com Validação

Cria banco temporário para teste antes de aplicar no banco real.

```bash
python3 modules/restore.py \
  --file backups/arquivo_backup.zip \
  --mode safe \
  --verify
```

#### 3. Restore Seletivo

Restaura apenas tabelas específicas (requer formato custom/directory no PostgreSQL).

```bash
# PostgreSQL - formato custom
python3 modules/restore.py \
  --file backups/postgresql_webapp.dump \
  --tables users,orders,products \
  --target webapp_db_restored
```

### Modos de Restore

#### Modo Seguro (Padrão)

1. Cria backup de segurança dos dados atuais
2. Valida arquivo de backup
3. Cria banco temporário
4. Testa restore no banco temporário
5. Se OK, aplica no banco real
6. Limpa arquivos temporários

```bash
python3 modules/restore.py --mode safe --file backup.sql
```

#### Modo Rápido

Restore direto sem validações extras (⚠️ Não cria backup de segurança).

```bash
python3 modules/restore.py --mode fast --file backup.sql
```

#### Modo Teste

Restore apenas em banco temporário para inspeção.

```bash
python3 modules/restore.py --mode test --file backup.sql
# Cria: database1_test_YYYYMMDD_HHMMSS
```

### Tratamento de Erros de Restore

O sistema automaticamente:

1. **Remove comandos DROP problemáticos**: Constraints que não existem
2. **Ignora warnings irrelevantes**: "does not exist", "already exists"
3. **Cria backup de rollback**: Antes de qualquer modificação
4. **Valida formato**: Detecta automaticamente SQL text vs binary

Ver documentação completa em [docs/Postgres erro no restore.md](docs/Postgres%20erro%20no%20restore.md).

### Recuperação de Desastres

Script completo para recuperação:

```bash
#!/bin/bash
# disaster_recovery.sh

echo "🚨 Iniciando recuperação de desastre"

# 1. Parar aplicações
systemctl stop aplicacao_web aplicacao_api

# 2. Restaurar bancos
LATEST_MYSQL=$(ls -t backups/mysql_*.sql | head -1)
python3 modules/restore.py --file "$LATEST_MYSQL" --mode fast --force

LATEST_POSTGRES=$(ls -t backups/postgresql_*.sql | head -1)
python3 modules/restore.py --file "$LATEST_POSTGRES" --mode fast --force

# 3. Verificar integridade
python3 modules/restore.py --verify-all

# 4. Reiniciar aplicações
systemctl start aplicacao_web aplicacao_api

echo "✅ Recuperação concluída"
```

## 📐 Sistema de Templates

O sistema de templates permite gerar rapidamente configurações para múltiplos servidores mantendo padronização.

### Gerar Novo Servidor

```bash
make generate SERVER=nome_servidor \
  COMPANY="Nome da Empresa" \
  AUTHOR="Seu Nome" \
  SERVER_LOCATION="Localização Física" \
  BACKUP_INTERVAL=60
```

Isso irá:
1. Copiar todos os templates de `src/`
2. Substituir variáveis ({{SERVER_NAME}}, {{COMPANY}}, etc.)
3. Criar estrutura de diretórios
4. Gerar scripts de instalação personalizados
5. Criar serviços systemd

### Estrutura de Templates

```
src/
├── modules/
│   ├── backup_control.py.template
│   ├── restore.py.template
│   └── prometheus_metrics.py.template
├── python_backup.py.template
├── python_backup.json.example
└── systemd/
    ├── vya-backup.service.template
    └── vya-backup-oneshot.service.template
```

### Variáveis Disponíveis

- `{{SERVER_NAME}}`: Nome único do servidor
- `{{COMPANY}}`: Nome da empresa
- `{{AUTHOR}}`: Autor da configuração
- `{{SERVER_LOCATION}}`: Localização física/lógica
- `{{BACKUP_INTERVAL}}`: Intervalo de backup em minutos
- `{{TIMEZONE}}`: Timezone do servidor

### Personalização de Templates

Para adicionar novas variáveis:

1. Edite os templates em `src/`
2. Adicione variável no formato `{{NOME_VARIAVEL}}`
3. Atualize o `Makefile` para fazer substituição:

```makefile
sed -e 's|{{NOVA_VARIAVEL}}|$(NOVA_VARIAVEL)|g' \
    src/template.py.template > $(SERVER_DIR)/template.py
```

## 📊 Monitoramento

### Métricas Prometheus

O sistema exporta métricas para Prometheus:

```python
# Métricas disponíveis
vya_backup_total                    # Total de backups realizados
vya_backup_duration_seconds         # Duração do backup em segundos
vya_backup_size_bytes               # Tamanho do backup em bytes
vya_backup_errors_total             # Total de erros
vya_restore_total                   # Total de restores realizados
vya_restore_duration_seconds        # Duração do restore
```

### Configurar Pushgateway

No `python_backup.json`:

```json
{
  "monitoring": {
    "prometheus": {
      "enabled": true,
      "pushgateway_url": "http://localhost:9091",
      "job_name": "vya_backup_producao_01"
    }
  }
}
```

### Logs Estruturados

```bash
# Logs principais
tail -f /var/log/vya_backupdb/backup.log
tail -f /var/log/vya_backupdb/restore.log

# Logs do systemd
journalctl -u vya-backup-producao_01.service -f

# Filtrar apenas erros
journalctl -u vya-backup-producao_01.service -p err -f
```

### Dashboard Grafana

Importe o dashboard em `monitoring/grafana_dashboard.json` (a ser criado).

## 🔧 Troubleshooting

### Problemas Comuns

#### 1. Erro: "Permission denied" ao executar backup

**Causa**: Usuário de backup sem permissões adequadas.

**Solução PostgreSQL**:
```sql
-- Conceder SUPERUSER (necessário para pg_dumpall --globals-only)
ALTER ROLE backup_user WITH SUPERUSER;

-- OU usar roles predefinidas do PG 16+
GRANT pg_read_all_data TO backup_user;
GRANT pg_read_all_settings TO backup_user;
```

**Solução MySQL**:
```sql
GRANT SELECT, SHOW VIEW, LOCK TABLES, RELOAD ON *.* TO 'backup_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 2. Erro: "constraint does not exist" ao restaurar PostgreSQL

**Causa**: Flag `-c` (--clean) tentando remover constraints inexistentes.

**Solução**: O sistema já trata automaticamente. Se persistir:

```bash
# Usar modo safe (padrão)
python3 modules/restore.py --mode safe --file backup.sql

# OU recriar banco do zero
python3 modules/restore.py --recreate --file backup.sql
```

Ver detalhes em [docs/Postgres erro no restore.md](docs/Postgres%20erro%20no%20restore.md).

#### 3. Backup não executa no horário agendado

**Verificar**:

```bash
# 1. Testar agendamento
python3 test_schedule_system.py

# 2. Verificar logs
journalctl -u vya-backup-servidor.service -n 50

# 3. Verificar timezone do sistema
timedatectl

# 4. Verificar tolerância de minutos
# Edite tolerance_minutes em python_backup.json
```

#### 4. Erro: "locale failed" (PostgreSQL)

**Solução**:

```bash
# Instalar locale
sudo locale-gen pt_BR.UTF-8
sudo update-locale LANG=pt_BR.UTF-8

# Configurar variáveis de ambiente
export LC_ALL=pt_BR.UTF-8
export LANG=pt_BR.UTF-8

# Ou no systemd service
Environment="LC_ALL=pt_BR.UTF-8"
Environment="LANG=pt_BR.UTF-8"
```

#### 5. Disco cheio durante backup

**Solução**:

```bash
# 1. Limpar backups antigos
find /backup/vya_backupdb -name "*.zip" -mtime +30 -delete

# 2. Configurar retenção automática
# Em python_backup.json:
{
  "backup_options": {
    "retention_days": 7  # Reduzir de 30 para 7
  }
}

# 3. Usar compressão mais agressiva (PostgreSQL)
pg_dump -d mydb -Fc -Z9 > backup.dump
```

### Logs de Diagnóstico

```bash
# Coletar informações de diagnóstico
bash << 'EOF'
echo "=== Diagnóstico VYA Backup DB ==="
echo ""
echo "1. Versões instaladas:"
psql --version
mysql --version
python3 --version
echo ""
echo "2. Status dos serviços:"
systemctl status vya-backup-*.service --no-pager
echo ""
echo "3. Espaço em disco:"
df -h /backup
echo ""
echo "4. Últimos backups:"
ls -lht /backup/vya_backupdb/*.zip | head -n 5
echo ""
echo "5. Últimas linhas do log:"
tail -n 50 /var/log/vya_backupdb/backup.log
EOF
```

## 📚 Documentação Completa

### Documentação Técnica

- **[Postgres Backup Completo Métodos](docs/Postgres%20Backup%20Completo%20Metodos.md)**: Guia completo de backup PostgreSQL incluindo objetos globais, usuários e roles
- **[Postgres Erro no Restore](docs/Postgres%20erro%20no%20restore.md)**: Troubleshooting detalhado de erros de restore e soluções

### Documentação Sphinx

Gere a documentação HTML:

```bash
cd docs_sphinx
make html
# Abra: _build/html/index.html
```

Conteúdo:
- Quick Start: Primeiro backup em 5 minutos
- Backup Operations: Operações de backup detalhadas
- Restore Operations: Operações de restore detalhadas
- Configuration Guide: Guia de configuração completo
- Database Setup: Configuração de bancos de dados
- Schedule System: Sistema de agendamento

### Exemplos Práticos

Ver diretório `servers/wf004/` para exemplo completo de servidor configurado.

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo LICENSE para detalhes.

## 👥 Autores

- **Yves Marinho** - *Desenvolvimento Inicial* - [@yvesmarinho](https://github.com/yvesmarinho)

## 🙏 Agradecimentos

- Comunidade PostgreSQL por documentação excelente
- Comunidade Python por bibliotecas robustas
- Contributors e testers

## 📞 Suporte

- **Issues**: [GitHub Issues](https://github.com/vyatechnologies/enterprise-python-backup/issues)
- **Documentação**: [Wiki do Projeto](https://github.com/vyatechnologies/enterprise-python-backup/wiki)
- **Email**: suporte@vyatechnologies.com.br

---

**Versão**: 1.0.0  
**Última Atualização**: 2025-01-16  
**Status**: Produção ✅