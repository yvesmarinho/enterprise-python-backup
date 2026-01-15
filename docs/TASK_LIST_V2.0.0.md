# Task List - Versão v2.0.0 - Melhorias Futuras

**Data de Criação**: 15 de Janeiro de 2026  
**Status Geral**: 🔵 Planejado (0/6 completas)  
**Tempo Total Estimado**: 30-41 horas  
**Dependências Base**: Phase 2 completa (80.2%)

---

## 📊 Visão Geral das Tarefas

| ID | Tarefa | Prioridade | Status | Tempo | Dependências |
|----|--------|------------|--------|-------|--------------|
| T-SECURITY-001 | Proteção dados conexão | 🔴 ALTA | ⏳ Pendente | 6-8h | Nenhuma |
| T-SECURITY-002 | Auditoria arquivos sensíveis | 🔴 CRÍTICA | ⏳ Pendente | 4-6h | Nenhuma |
| T-SORT-001 | Ordenar databases | 🟡 MÉDIA | ⏳ Pendente | 2-3h | Nenhuma |
| T-AUDIT-001 | Relatório auditoria | 🔴 ALTA | ⏳ Pendente | 6-8h | Nenhuma |
| T-DEPLOY-001 | Script deploy automático | 🔴 ALTA | ⏳ Pendente | 8-10h | T-SECURITY-001 |
| T-RENAME-001 | Renomear projeto | 🟢 BAIXA | ⏳ Pendente | 4-6h | T-DEPLOY-001 |

---

## 🔐 T-SECURITY-001: Proteção de Dados de Conexão

### Objetivo
Migrar senhas e credenciais de `python_backup.json` para sistema seguro usando CredentialsManager existente.

### Prioridade
🔴 ALTA - Segurança crítica

### Status
⏳ Pendente (0/12 subtarefas)

### Tempo Estimado
6-8 horas

### Dependências
Nenhuma (pode iniciar imediatamente)

### Subtarefas

#### 1. Análise e Planejamento (1h)
- [ ] 1.1. Revisar CredentialsManager existente (`src/python_backup/security/credentials.py`)
- [ ] 1.2. Analisar estrutura atual de `python_backup.json`
- [ ] 1.3. Identificar todos os campos sensíveis:
  - `db_config[].password`
  - `email_config.smtp_password`
  - Outros campos sensíveis
- [ ] 1.4. Desenhar estrutura do vault seguro (`.secrets/vault.json.enc`)
- [ ] 1.5. Planejar retrocompatibilidade (suporte JSON por 1 versão)

#### 2. Implementação do Vault (2-3h)
- [ ] 2.1. Criar módulo `src/python_backup/security/vault.py`
  - Classe `VaultManager` com métodos CRUD
  - Integração com `CredentialsManager`
  - Suporte a múltiplas credenciais por DBMS
- [ ] 2.2. Implementar criptografia Fernet para vault
  - Usar chave baseada em hostname (mesmo padrão)
  - Formato: `{id_dbms: {username, password, encrypted_at}}`
- [ ] 2.3. Criar estrutura de pastas `.secrets/`
  - `.secrets/vault.json.enc` (credenciais criptografadas)
  - `.secrets/.gitignore` (garantir não-versionamento)
- [ ] 2.4. Implementar migração automática
  - Detectar senhas em `python_backup.json`
  - Migrar para vault automaticamente
  - Manter marcador de migração

#### 3. CLI Commands (2h)
- [ ] 3.1. Implementar `credentials add`
  ```bash
  python -m python_backup.cli credentials add \
    --id-dbms 1 \
    --username postgres \
    --password <senha>
  ```
- [ ] 3.2. Implementar `credentials update`
  ```bash
  python -m python_backup.cli credentials update \
    --id-dbms 1 \
    --password <nova-senha>
  ```
- [ ] 3.3. Implementar `credentials remove`
  ```bash
  python -m python_backup.cli credentials remove --id-dbms 1
  ```
- [ ] 3.4. Implementar `credentials list`
  ```bash
  python -m python_backup.cli credentials list
  # Output: id_dbms | username | last_updated | status
  ```

#### 4. Integração (1-2h)
- [ ] 4.1. Atualizar `config/loader.py` para usar vault
  - Primeiro tentar vault
  - Fallback para JSON (retrocompatibilidade)
  - Warning se usar JSON
- [ ] 4.2. Atualizar todos os adapters (MySQL, PostgreSQL, Files)
  - Receber credenciais do vault
  - Manter compatibilidade com JSON
- [ ] 4.3. Adicionar testes de integração
  - Test vault encryption/decryption
  - Test migration from JSON
  - Test CLI commands

#### 5. Documentação e Testes (1h)
- [ ] 5.1. Criar guia de migração (`docs/guides/VAULT_MIGRATION_GUIDE.md`)
  - Passo a passo de migração
  - Exemplos de uso do CLI
  - Troubleshooting
- [ ] 5.2. Atualizar README.md com nova seção de segurança
- [ ] 5.3. Criar 20+ testes unitários para VaultManager
- [ ] 5.4. Criar 10+ testes de integração E2E

### Arquivos Afetados
```
src/python_backup/
├── security/
│   └── vault.py (NEW - 250 lines)
├── config/
│   └── loader.py (MODIFY - +50 lines)
├── cli.py (MODIFY - +150 lines, 4 commands)
└── db/
    ├── mysql.py (MODIFY - +20 lines)
    └── postgresql.py (MODIFY - +20 lines)

tests/
├── unit/
│   └── test_vault.py (NEW - 20 tests)
└── integration/
    └── test_vault_migration.py (NEW - 10 tests)

docs/guides/
└── VAULT_MIGRATION_GUIDE.md (NEW - 300 lines)

.secrets/
├── vault.json.enc (NEW - encrypted credentials)
└── .gitignore (NEW)
```

### Critérios de Aceitação
- ✅ Vault criptografado funcionando
- ✅ CLI commands completos e testados
- ✅ Migração automática de JSON para vault
- ✅ Retrocompatibilidade por 1 versão
- ✅ 30+ testes passando
- ✅ Documentação completa
- ✅ Zero senhas em plain text no código

### Riscos e Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Perda de credenciais durante migração | 🔴 ALTO | Backup automático antes de migrar |
| Incompatibilidade com sistema existente | 🟡 MÉDIO | Manter retrocompatibilidade |
| Performance degradation | 🟢 BAIXO | Cache de credenciais descriptografadas |

---

## 🔍 T-SECURITY-002: Auditoria e Relocação de Arquivos Sensíveis

### Objetivo
Identificar, relocar e proteger todos os arquivos com informações sensíveis do projeto.

### Prioridade
🔴 CRÍTICA - Segurança e compliance (alerta Github Dependabot)

### Status
⏳ Pendente (0/10 subtarefas)

### Tempo Estimado
4-6 horas

### Dependências
Nenhuma (pode executar em paralelo com T-SECURITY-001)

### Subtarefas

#### 1. Auditoria de Segurança (1-2h)
- [ ] 1.1. Executar varredura completa do projeto
  ```bash
  grep -r "password\|secret\|key\|token\|credential" \
    --include="*.py" \
    --include="*.json" \
    --include="*.yaml" \
    --include="*.txt" \
    --exclude-dir=".venv" \
    --exclude-dir="htmlcov" \
    .
  ```
- [ ] 1.2. Identificar arquivos com dados sensíveis
  - Arquivos de log com senhas
  - Configurações com credenciais
  - Backups com dados sensíveis
  - Scripts com tokens hardcoded
- [ ] 1.3. Classificar por nível de sensibilidade
  - 🔴 CRÍTICO: Credenciais em plain text
  - 🟡 MÉDIO: Logs com informações de sistema
  - 🟢 BAIXO: Configurações exemplo
- [ ] 1.4. Gerar relatório de auditoria (`SECURITY_AUDIT_2026-01-15.md`)

#### 2. Padronização de Pasta Secrets (1h)
- [ ] 2.1. Criar/padronizar estrutura `.secrets/`
  ```
  .secrets/
  ├── .gitignore (garantir não-versionamento)
  ├── credentials.json.enc (do CredentialsManager)
  ├── vault.json.enc (do T-SECURITY-001)
  ├── logs/ (logs com informações sensíveis)
  └── backups/ (backups temporários)
  ```
- [ ] 2.2. Criar `.secrets/.gitignore` robusto
  ```
  # Ignore everything in .secrets/
  *
  # But track .gitignore itself
  !.gitignore
  ```
- [ ] 2.3. Validar que `.secrets/` está no `.gitignore` principal
- [ ] 2.4. Verificar histórico do git (nenhum arquivo sensível versionado)

#### 3. Relocação de Arquivos (1h)
- [ ] 3.1. Mover arquivos sensíveis identificados para `.secrets/`
  - Logs com credenciais → `.secrets/logs/`
  - Configs com senhas → `.secrets/configs/`
  - Backups temporários → `.secrets/backups/`
- [ ] 3.2. Atualizar referências no código
  - `src/python_backup/utils/logging_config.py`
  - `src/python_backup/config/loader.py`
  - Scripts de backup/restore
- [ ] 3.3. Atualizar paths em `python_backup.json`
  ```json
  {
    "logging": {
      "path": ".secrets/logs/"
    }
  }
  ```

#### 4. Limpeza e Validação (1h)
- [ ] 4.1. Remover arquivos sensíveis do git history
  ```bash
  git filter-branch --force --index-filter \
    'git rm --cached --ignore-unmatch <arquivo-sensível>' \
    --prune-empty --tag-name-filter cat -- --all
  ```
- [ ] 4.2. Validar que nenhum dado sensível está versionado
  ```bash
  git log --all --full-history -- .secrets/
  ```
- [ ] 4.3. Executar scan de segurança
  ```bash
  # Usar ferramenta como git-secrets ou gitleaks
  gitleaks detect --source . --verbose
  ```
- [ ] 4.4. Gerar relatório de validação

#### 5. Documentação (1h)
- [ ] 5.1. Criar `docs/security/SECURITY_GUIDELINES.md`
  - Estrutura de pastas seguras
  - Boas práticas de armazenamento
  - Checklist de segurança
- [ ] 5.2. Atualizar README.md com seção de segurança
- [ ] 5.3. Criar `.secrets/README.md` explicando estrutura
- [ ] 5.4. Atualizar guia de contribuição com regras de segurança

### Arquivos Afetados
```
.secrets/ (NEW)
├── .gitignore (NEW)
├── README.md (NEW)
├── logs/ (NEW)
├── configs/ (NEW)
└── backups/ (NEW)

.gitignore (MODIFY - adicionar .secrets/)

src/python_backup/
├── utils/
│   └── logging_config.py (MODIFY - novo path)
└── config/
    └── loader.py (MODIFY - novo path)

docs/security/
└── SECURITY_GUIDELINES.md (NEW - 200 lines)

SECURITY_AUDIT_2026-01-15.md (NEW - report)
```

### Critérios de Aceitação
- ✅ 100% dos arquivos sensíveis identificados
- ✅ Todos movidos para `.secrets/`
- ✅ `.secrets/` não versionado (validado)
- ✅ Nenhum arquivo sensível no histórico do git
- ✅ Scan de segurança passando
- ✅ Documentação completa
- ✅ Código atualizado com novos paths

### Riscos e Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Exposição de dados durante migração | 🔴 ALTO | Fazer em branch separada |
| Quebra de funcionalidade | 🟡 MÉDIO | Testes completos após mudanças |
| Histórico git comprometido | 🔴 ALTO | Usar git filter-branch corretamente |

---

## 📊 T-SORT-001: Ordenar Databases por Nome

### Objetivo
Implementar ordenação alfabética dos databases dentro de cada DBMS para melhor UX.

### Prioridade
🟡 MÉDIA - Melhoria de UX

### Status
⏳ Pendente (0/5 subtarefas)

### Tempo Estimado
2-3 horas

### Dependências
Nenhuma

### Subtarefas

#### 1. Análise (30min)
- [ ] 1.1. Identificar onde databases são carregados
  - `src/python_backup/config/loader.py` → `load_vya_config()`
- [ ] 1.2. Verificar estrutura de `db_config[].db_list`
- [ ] 1.3. Identificar pontos de exibição no CLI
  - `restore-list` command
  - `status` command

#### 2. Implementação (1h)
- [ ] 2.1. Adicionar sorting em `load_vya_config()`
  ```python
  for db_config in config['db_config']:
      if 'db_list' in db_config:
          db_config['db_list'] = sorted(db_config['db_list'])
  ```
- [ ] 2.2. Adicionar sorting no CLI `restore-list`
  ```python
  backups = sorted(backups, key=lambda x: x['database'])
  ```
- [ ] 2.3. Adicionar sorting no CLI `status`

#### 3. Testes (30min)
- [ ] 3.1. Criar teste unitário para sorting em config loader
  ```python
  def test_databases_sorted_alphabetically():
      config = load_vya_config()
      for db in config['db_config']:
          assert db['db_list'] == sorted(db['db_list'])
  ```
- [ ] 3.2. Criar teste para CLI output
- [ ] 3.3. Validar com dados reais (PostgreSQL + MySQL)

#### 4. Documentação (30min)
- [ ] 4.1. Atualizar README.md mencionando ordenação
- [ ] 4.2. Adicionar nota em `python_backup.json` exemplo
- [ ] 4.3. Atualizar CHANGELOG.md

#### 5. Validação (30min)
- [ ] 5.1. Testar com configuração real
- [ ] 5.2. Verificar output dos comandos CLI
- [ ] 5.3. Validar que não quebrou funcionalidade

### Arquivos Afetados
```
src/python_backup/
├── config/
│   └── loader.py (MODIFY - +5 lines)
└── cli.py (MODIFY - +10 lines)

tests/unit/
└── test_config_sorting.py (NEW - 5 tests)

README.md (MODIFY - +3 lines)
CHANGELOG.md (MODIFY - +5 lines)
```

### Critérios de Aceitação
- ✅ Databases ordenados alfabeticamente em `db_list`
- ✅ CLI commands exibem databases ordenados
- ✅ 5+ testes validando ordenação
- ✅ Nenhuma funcionalidade quebrada
- ✅ Documentação atualizada

### Riscos e Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Ordem afeta backup | 🟢 BAIXO | Testes de regressão |
| Performance com muitos DBs | 🟢 BAIXO | Sorting é O(n log n) - rápido |

---

## 📋 T-AUDIT-001: Implementar Relatório de Auditoria

### Objetivo
Criar sistema completo de auditoria para tracking de operações de backup/restore.

### Prioridade
🔴 ALTA - Compliance e rastreabilidade

### Status
⏳ Pendente (0/14 subtarefas)

### Tempo Estimado
6-8 horas

### Dependências
Nenhuma

### Subtarefas

#### 1. Design do Sistema (1h)
- [ ] 1.1. Definir estrutura de dados do audit log
  ```json
  {
    "audit_id": "uuid",
    "timestamp": "2026-01-15T10:30:00Z",
    "operation": "backup|restore",
    "dbms": "postgresql|mysql|files",
    "databases": ["db1", "db2"],
    "status": "success|failure|partial",
    "duration_seconds": 120.5,
    "size_bytes": 123456789,
    "backup_file": "/path/to/backup.sql.gz",
    "user": "system",
    "errors": [],
    "metadata": {}
  }
  ```
- [ ] 1.2. Definir localização dos logs
  - Primary: `/var/log/enterprise/vya_backupdb_audit.json`
  - Secondary: `.secrets/logs/audit.json`
- [ ] 1.3. Definir formatos de output (JSON, HTML, CSV)
- [ ] 1.4. Planejar métricas agregadas

#### 2. Implementação do AuditLogger (2-3h)
- [ ] 2.1. Criar módulo `src/python_backup/audit/logger.py`
  ```python
  class AuditLogger:
      def log_operation(self, operation, dbms, databases, status, ...)
      def get_logs(self, start_date, end_date, filters)
      def generate_report(self, format='json')
      def get_metrics(self, period='week')
  ```
- [ ] 2.2. Implementar persistência (JSON Lines format)
  ```
  {"audit_id": "...", "timestamp": "...", ...}
  {"audit_id": "...", "timestamp": "...", ...}
  ```
- [ ] 2.3. Implementar rotação de logs (keep 90 days)
- [ ] 2.4. Implementar queries eficientes (indexes, filtering)

#### 3. Integração com BackupExecutor (1h)
- [ ] 3.1. Adicionar hooks no início/fim de backup
  ```python
  def execute_backup(...):
      audit_id = audit_logger.start_operation('backup', ...)
      try:
          # backup logic
          audit_logger.complete_operation(audit_id, 'success', ...)
      except Exception as e:
          audit_logger.complete_operation(audit_id, 'failure', ...)
  ```
- [ ] 3.2. Capturar métricas de duração
- [ ] 3.3. Capturar tamanho dos backups
- [ ] 3.4. Registrar erros detalhados

#### 4. Integração com RestoreExecutor (1h)
- [ ] 4.1. Adicionar hooks similar ao backup
- [ ] 4.2. Registrar source e target databases
- [ ] 4.3. Capturar tempo de restore
- [ ] 4.4. Registrar validações

#### 5. CLI Commands (1-2h)
- [ ] 5.1. Implementar `audit-report`
  ```bash
  python -m python_backup.cli audit-report \
    --start-date 2026-01-01 \
    --end-date 2026-01-15 \
    --format json|html|csv \
    --operation backup|restore \
    --status success|failure
  ```
- [ ] 5.2. Implementar `audit-metrics`
  ```bash
  python -m python_backup.cli audit-metrics \
    --period week|month|year
  # Output:
  # Total Backups: 150
  # Success Rate: 98.7%
  # Average Duration: 2m 30s
  # Total Size: 25.5 GB
  ```
- [ ] 5.3. Implementar `audit-export`
  ```bash
  python -m python_backup.cli audit-export \
    --format csv \
    --output /path/to/report.csv
  ```

#### 6. Report Generation (1h)
- [ ] 6.1. Criar gerador de relatório JSON
  ```json
  {
    "period": {"start": "...", "end": "..."},
    "summary": {
      "total_operations": 150,
      "successful": 148,
      "failed": 2,
      "success_rate": 98.7,
      "total_duration_hours": 5.5,
      "total_size_gb": 25.5
    },
    "operations": [...]
  }
  ```
- [ ] 6.2. Criar gerador de relatório HTML
  - Usar template Jinja2
  - Gráficos com Chart.js
  - Tabela interativa
- [ ] 6.3. Criar gerador de relatório CSV
  - Headers: timestamp, operation, dbms, databases, status, duration, size
  - Compatible com Excel/Google Sheets

#### 7. Email Integration (30min)
- [ ] 7.1. Adicionar opção de relatório semanal automático
  ```json
  "audit_config": {
    "weekly_report": {
      "enabled": true,
      "day": "monday",
      "time": "09:00",
      "recipients": ["manager@vya.digital"],
      "format": "html"
    }
  }
  ```
- [ ] 7.2. Integrar com EmailSender existente
- [ ] 7.3. Template de email para relatório

#### 8. Testes (1h)
- [ ] 8.1. Criar 15+ testes unitários para AuditLogger
- [ ] 8.2. Criar 10+ testes de integração
- [ ] 8.3. Testar geração de reports (JSON, HTML, CSV)
- [ ] 8.4. Testar rotação de logs

#### 9. Documentação (30min)
- [ ] 9.1. Criar guia de auditoria (`docs/guides/AUDIT_GUIDE.md`)
- [ ] 9.2. Exemplos de queries e filtros
- [ ] 9.3. Atualizar README.md
- [ ] 9.4. Exemplos de reports

### Arquivos Afetados
```
src/python_backup/
├── audit/
│   ├── __init__.py (NEW)
│   ├── logger.py (NEW - 300 lines)
│   └── reports.py (NEW - 200 lines)
├── backup/
│   └── executor.py (MODIFY - +30 lines)
├── restore/
│   └── executor.py (MODIFY - +30 lines)
└── cli.py (MODIFY - +200 lines, 3 commands)

tests/
├── unit/
│   └── test_audit_logger.py (NEW - 15 tests)
└── integration/
    └── test_audit_integration.py (NEW - 10 tests)

docs/guides/
└── AUDIT_GUIDE.md (NEW - 400 lines)

/var/log/enterprise/
└── vya_backupdb_audit.json (NEW - audit log)

templates/
└── audit_report.html (NEW - HTML template)
```

### Critérios de Aceitação
- ✅ Audit logger funcionando e integrando
- ✅ 3 CLI commands completos
- ✅ Reports em 3 formatos (JSON, HTML, CSV)
- ✅ Email semanal automático (opcional)
- ✅ 25+ testes passando
- ✅ Documentação completa com exemplos
- ✅ Rotação de logs funcionando

### Riscos e Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Performance impact no backup | 🟡 MÉDIO | Logging assíncrono |
| Disco cheio com logs | 🟡 MÉDIO | Rotação automática (90 dias) |
| Logs corrompidos | 🟢 BAIXO | JSON Lines format (resiliente) |

---

## 🚀 T-DEPLOY-001: Script Python de Deploy Automático

### Objetivo
Criar script Python completo para automação de deploy e atualização do sistema.

### Prioridade
🔴 ALTA - Facilita adoção e updates

### Status
⏳ Pendente (0/16 subtarefas)

### Tempo Estimado
8-10 horas

### Dependências
- T-SECURITY-001 (para migração de credenciais)

### Subtarefas

#### 1. Planejamento (1h)
- [ ] 1.1. Definir fluxo de deploy completo
  ```
  1. Detectar instalação existente
  2. Backup de configuração atual
  3. Validar sistema (Python, dependências)
  4. Migrar configurações
  5. Instalar nova versão
  6. Atualizar crontab
  7. Validar instalação
  8. Rollback se falhar
  ```
- [ ] 1.2. Definir estrutura de instalação
  ```
  /opt/vya-backupdb/
  ├── bin/
  ├── lib/
  ├── config/
  ├── logs/
  └── .secrets/
  ```
- [ ] 1.3. Identificar compatibilidades
  - Python 3.11+
  - Linux (Debian/Ubuntu, RHEL/CentOS)
  - Dependências do sistema

#### 2. Módulo de Detecção (1-2h)
- [ ] 2.1. Criar `scripts/deploy/detector.py`
  ```python
  class InstallationDetector:
      def detect_existing_installation() -> Optional[Path]
      def get_installed_version() -> Optional[str]
      def get_config_path() -> Optional[Path]
      def check_system_requirements() -> Dict
  ```
- [ ] 2.2. Detectar versões antigas
  - `/usr/local/bin/vya-backup`
  - `~/.local/bin/vya-backup`
  - `/opt/vya-backupdb/`
- [ ] 2.3. Validar requisitos do sistema
  - Python version
  - Disk space
  - Permissions

#### 3. Módulo de Backup (1h)
- [ ] 3.1. Criar `scripts/deploy/backup.py`
  ```python
  class ConfigBackup:
      def backup_config(source: Path, dest: Path)
      def backup_credentials(source: Path, dest: Path)
      def backup_crontab()
      def restore_backup(backup_path: Path)
  ```
- [ ] 3.2. Backup timestamped
  ```
  /opt/vya-backupdb/backups/
  └── backup_2026-01-15_10-30-00/
      ├── python_backup.json
      ├── credentials.json.enc
      └── crontab.txt
  ```

#### 4. Módulo de Migração (2-3h)
- [ ] 4.1. Criar `scripts/deploy/migrator.py`
  ```python
  class ConfigMigrator:
      def migrate_v1_to_v2(old_config: Path) -> Dict
      def migrate_credentials_to_vault(old_creds: Path)
      def migrate_crontab(old_cron: str) -> str
  ```
- [ ] 4.2. Migração de `python_backup.json`
  - Detectar formato antigo
  - Converter para novo formato
  - Validar com Pydantic
- [ ] 4.3. Migração de credenciais
  - De JSON plain text → vault criptografado
  - Usar T-SECURITY-001 VaultManager
- [ ] 4.4. Migração de crontab
  - Detectar entries antigas
  - Atualizar paths
  - Manter schedule

#### 5. Módulo de Instalação (1-2h)
- [ ] 5.1. Criar `scripts/deploy/installer.py`
  ```python
  class Installer:
      def create_virtualenv(path: Path)
      def install_dependencies(venv_path: Path)
      def install_package(venv_path: Path, package_path: Path)
      def create_symlinks()
      def set_permissions()
  ```
- [ ] 5.2. Criação de virtualenv
  ```bash
  python3 -m venv /opt/vya-backupdb/venv
  ```
- [ ] 5.3. Instalação de dependências
  ```bash
  /opt/vya-backupdb/venv/bin/pip install -r requirements.txt
  ```
- [ ] 5.4. Instalação do package
  ```bash
  /opt/vya-backupdb/venv/bin/pip install -e .
  ```

#### 6. Módulo de Crontab (1h)
- [ ] 6.1. Criar `scripts/deploy/cron_manager.py`
  ```python
  class CronManager:
      def get_current_crontab() -> str
      def backup_crontab()
      def update_crontab(new_entry: str)
      def validate_crontab()
  ```
- [ ] 6.2. Atualizar entry existente
  ```cron
  # OLD
  0 22 * * * /usr/local/bin/vya-backup backup --all
  
  # NEW
  0 22 * * * /opt/vya-backupdb/venv/bin/python -m python_backup.cli backup --all
  ```
- [ ] 6.3. Validação de syntax

#### 7. Módulo de Validação (1h)
- [ ] 7.1. Criar `scripts/deploy/validator.py`
  ```python
  class Validator:
      def validate_installation() -> bool
      def test_connection(dbms: str) -> bool
      def test_backup_dry_run() -> bool
      def validate_permissions() -> bool
  ```
- [ ] 7.2. Connection tests
  ```bash
  python -m python_backup.cli connection-test --all
  ```
- [ ] 7.3. Dry-run backup test
- [ ] 7.4. Permissions check

#### 8. Script Principal (1h)
- [ ] 8.1. Criar `scripts/deploy.py` (main script)
  ```python
  #!/usr/bin/env python3
  """
  VYA BackupDB - Automated Deployment Script
  
  Usage:
      python scripts/deploy.py --install
      python scripts/deploy.py --upgrade
      python scripts/deploy.py --rollback
  """
  
  def main():
      parser = argparse.ArgumentParser(...)
      # Orchestrate all modules
  ```
- [ ] 8.2. Implementar modo interativo
  ```
  === VYA BackupDB Deployment ===
  
  Existing installation detected: v1.5.0
  Target version: v2.0.0
  
  Steps:
  [1/7] Backup current configuration... ✓
  [2/7] Migrate credentials to vault... ✓
  [3/7] Install dependencies... ✓
  [4/7] Update crontab... ✓
  [5/7] Validate installation... ✓
  [6/7] Run connection tests... ✓
  [7/7] Cleanup... ✓
  
  Deployment completed successfully!
  ```
- [ ] 8.3. Implementar modo não-interativo (--yes flag)
- [ ] 8.4. Implementar rollback automático em caso de erro

#### 9. Testes (1h)
- [ ] 9.1. Criar 20+ testes unitários
- [ ] 9.2. Criar 10+ testes de integração
- [ ] 9.3. Testar fresh install
- [ ] 9.4. Testar upgrade v1 → v2
- [ ] 9.5. Testar rollback

#### 10. Documentação (1h)
- [ ] 10.1. Criar `docs/DEPLOYMENT_GUIDE.md`
- [ ] 10.2. Exemplos de uso do deploy script
- [ ] 10.3. Troubleshooting comum
- [ ] 10.4. Atualizar README.md

### Arquivos Afetados
```
scripts/
├── deploy.py (NEW - 400 lines, main script)
└── deploy/
    ├── __init__.py (NEW)
    ├── detector.py (NEW - 150 lines)
    ├── backup.py (NEW - 120 lines)
    ├── migrator.py (NEW - 250 lines)
    ├── installer.py (NEW - 200 lines)
    ├── cron_manager.py (NEW - 150 lines)
    └── validator.py (NEW - 180 lines)

tests/deploy/
├── test_detector.py (NEW - 10 tests)
├── test_backup.py (NEW - 8 tests)
├── test_migrator.py (NEW - 12 tests)
└── test_installer.py (NEW - 10 tests)

docs/
└── DEPLOYMENT_GUIDE.md (NEW - 500 lines)
```

### Critérios de Aceitação
- ✅ Deploy script 100% funcional
- ✅ Detecção de instalação existente
- ✅ Backup automático de configs
- ✅ Migração de credenciais para vault
- ✅ Atualização automática de crontab
- ✅ Validação pós-deploy
- ✅ Rollback automático em falhas
- ✅ 30+ testes passando
- ✅ Documentação completa
- ✅ Suporte a fresh install e upgrade

### Riscos e Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Perda de configuração | 🔴 ALTO | Backup automático antes de qualquer mudança |
| Sistema quebrado após deploy | 🔴 ALTO | Rollback automático + validação |
| Incompatibilidade de versão | 🟡 MÉDIO | Detecção de versão + migração específica |

---

## 🏷️ T-RENAME-001: Renomear Projeto para "enterprise-python-backupdb"

### Objetivo
Renomear projeto de "python_backup" para "enterprise-python-backupdb" em todo o codebase.

### Prioridade
🟢 BAIXA - Apenas branding

### Status
⏳ Pendente (0/10 subtarefas)

### Tempo Estimado
4-6 horas

### Dependências
- T-DEPLOY-001 (deploy script precisa do nome final)

### Subtarefas

#### 1. Planejamento (30min)
- [ ] 1.1. Listar todos os lugares onde "python_backup" aparece
  ```bash
  grep -r "python_backup" \
    --include="*.py" \
    --include="*.md" \
    --include="*.toml" \
    --include="*.json" \
    --exclude-dir=".venv" \
    . | wc -l
  ```
- [ ] 1.2. Definir namespace de compatibilidade
  - Manter alias `python_backup` → `python_backupdb` por 1 versão
  - Warning deprecation
- [ ] 1.3. Planejar sequência de mudanças

#### 2. Renomear Estrutura de Pastas (1h)
- [ ] 2.1. Renomear pasta principal
  ```bash
  mv src/python_backup src/python_backupdb
  ```
- [ ] 2.2. Atualizar `.venv` se necessário
- [ ] 2.3. Atualizar `.gitignore` com novos paths

#### 3. Atualizar pyproject.toml (30min)
- [ ] 3.1. Atualizar nome do package
  ```toml
  [project]
  name = "enterprise-python-backupdb"
  
  [tool.setuptools.packages.find]
  where = ["src"]
  include = ["python_backupdb*"]
  ```
- [ ] 3.2. Atualizar console scripts
  ```toml
  [project.scripts]
  vya-backupdb = "python_backupdb.cli:app"
  ```
- [ ] 3.3. Atualizar metadata

#### 4. Atualizar Imports (2-3h)
- [ ] 4.1. Usar find & replace em todos os arquivos `.py`
  ```bash
  find src tests -name "*.py" -exec sed -i 's/from python_backup/from python_backupdb/g' {} \;
  find src tests -name "*.py" -exec sed -i 's/import python_backup/import python_backupdb/g' {} \;
  ```
- [ ] 4.2. Validar cada arquivo modificado
- [ ] 4.3. Executar testes para garantir nada quebrou
  ```bash
  pytest tests/ -v
  ```

#### 5. Atualizar Documentação (1h)
- [ ] 5.1. Atualizar README.md
  - Trocar todas as menções de "python_backup"
  - Atualizar exemplos de uso
  - Atualizar comandos CLI
- [ ] 5.2. Atualizar todos os arquivos em `docs/`
  ```bash
  find docs -name "*.md" -exec sed -i 's/python_backup/python_backupdb/g' {} \;
  ```
- [ ] 5.3. Atualizar INDEX.md
- [ ] 5.4. Atualizar TODO.md

#### 6. Atualizar CLI Commands (30min)
- [ ] 6.1. Verificar todos os comandos ainda funcionam
  ```bash
  python -m python_backupdb.cli --help
  python -m python_backupdb.cli backup --help
  ```
- [ ] 6.2. Atualizar mensagens de ajuda
- [ ] 6.3. Atualizar exemplos

#### 7. Atualizar Configs (30min)
- [ ] 7.1. Renomear `python_backup.json` → `vya_backupdb.json`
- [ ] 7.2. Atualizar loader para buscar ambos (compatibilidade)
  ```python
  # Try new name first, fallback to old
  if Path("vya_backupdb.json").exists():
      config_file = "vya_backupdb.json"
  else:
      config_file = "python_backup.json"  # deprecated
  ```
- [ ] 7.3. Adicionar warning para nome antigo

#### 8. Namespace Deprecation (1h)
- [ ] 8.1. Criar alias de compatibilidade
  ```python
  # src/python_backup/__init__.py (keep for 1 version)
  import warnings
  warnings.warn(
      "python_backup is deprecated, use python_backupdb instead",
      DeprecationWarning,
      stacklevel=2
  )
  from python_backupdb import *
  ```
- [ ] 8.2. Manter por 1 versão (v2.0.x)
- [ ] 8.3. Remover em v2.1.0

#### 9. Testes (1h)
- [ ] 9.1. Executar suite completa de testes
  ```bash
  pytest tests/ -v --cov=src/python_backupdb
  ```
- [ ] 9.2. Validar 531+ testes passando
- [ ] 9.3. Testar imports deprecados
- [ ] 9.4. Testar CLI com novo nome

#### 10. Release (30min)
- [ ] 10.1. Criar tag v2.0.0
- [ ] 10.2. Atualizar CHANGELOG.md
  ```markdown
  ## [2.0.0] - 2026-01-XX
  
  ### Breaking Changes
  - Renamed package from `python_backup` to `python_backupdb`
  - Renamed config from `python_backup.json` to `vya_backupdb.json`
  - Old names deprecated, will be removed in v2.1.0
  ```
- [ ] 10.3. Criar release notes
- [ ] 10.4. Atualizar GitHub repository name (se aplicável)

### Arquivos Afetados
```
src/
├── python_backup/ → python_backupdb/ (RENAME)
│   └── (all subdirectories)
└── python_backup/ (KEEP as deprecated alias)

pyproject.toml (MODIFY)
README.md (MODIFY)
docs/*.md (MODIFY - all)
tests/*.py (MODIFY - all imports)

Configs:
├── python_backup.json (DEPRECATED)
└── vya_backupdb.json (NEW default)

CHANGELOG.md (MODIFY)
```

### Critérios de Aceitação
- ✅ Pasta renomeada: `src/python_backupdb/`
- ✅ Package name: `enterprise-python-backupdb`
- ✅ Config name: `vya_backupdb.json`
- ✅ CLI command: `vya-backupdb` ou `python -m python_backupdb.cli`
- ✅ Todos os imports atualizados
- ✅ 531+ testes passando com novo nome
- ✅ Documentação 100% atualizada
- ✅ Namespace antigo deprecated (não removido)
- ✅ Warning para uso de nomes antigos

### Riscos e Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Imports quebrados | 🔴 ALTO | Alias de compatibilidade |
| Scripts em produção quebram | 🔴 ALTO | Manter nome antigo por 1 versão |
| Confusão de usuários | 🟡 MÉDIO | Documentação clara + warnings |

---

## 📊 Resumo Geral

### Ordem de Execução Recomendada
```
1. T-SECURITY-002 (4-6h)  - CRÍTICO, pode executar AGORA
   └─ Auditoria e relocação de arquivos sensíveis

2. T-SECURITY-001 (6-8h)  - ALTO, executar logo após
   └─ Proteção de dados de conexão com vault

3. T-SORT-001 (2-3h)      - MÉDIO, quick win
   └─ Ordenar databases por nome

4. T-AUDIT-001 (6-8h)     - ALTO, importante para compliance
   └─ Sistema de auditoria completo

5. T-DEPLOY-001 (8-10h)   - ALTO, depende de T-SECURITY-001
   └─ Script de deploy automático

6. T-RENAME-001 (4-6h)    - BAIXO, última tarefa antes de release
   └─ Renomear projeto (branding final)
```

### Tempo Total
- **Mínimo**: 30 horas
- **Máximo**: 41 horas
- **Média**: 35.5 horas (~4.5 dias de desenvolvimento)

### Recursos Necessários
- 1 desenvolvedor sênior Python
- Acesso ao servidor de produção (para T-SECURITY-002)
- Ambiente de testes completo
- Revisão de código por segundo desenvolvedor
- Approval de segurança para T-SECURITY-001 e T-SECURITY-002

### Marcos (Milestones)
```
M1: Segurança Completa (T-SECURITY-001 + T-SECURITY-002)
    └─ Estimativa: 10-14 horas
    └─ Criticidade: 🔴 ALTA

M2: Melhorias de Produto (T-SORT-001 + T-AUDIT-001)
    └─ Estimativa: 8-11 horas
    └─ Criticidade: 🟡 MÉDIA

M3: Deploy e Branding (T-DEPLOY-001 + T-RENAME-001)
    └─ Estimativa: 12-16 horas
    └─ Criticidade: 🔴 ALTA
```

### Métricas de Sucesso
- ✅ Todas as 6 tarefas completas
- ✅ Zero vulnerabilidades de segurança
- ✅ 100+ novos testes passando
- ✅ Deploy script validado em staging
- ✅ Documentação completa (1000+ linhas)
- ✅ Aprovação de security review
- ✅ Pronto para release v2.0.0

---

**Documento Criado**: 15 de Janeiro de 2026  
**Mantido por**: Yves Marinho  
**Projeto**: VYA BackupDB v2.0.0  
**Status**: 🔵 Planejamento Completo

---

## 📝 Notas Finais

### Priorização Sugerida para Sprint
Se houver limitação de tempo, executar nesta ordem:
1. **T-SECURITY-002** (CRÍTICO - 4-6h)
2. **T-SECURITY-001** (ALTO - 6-8h)
3. **T-DEPLOY-001** (ALTO - 8-10h)

Estas 3 tarefas (18-24h) entregam **80% do valor** da v2.0.0.

### Tarefas Opcionais (podem ser v2.0.1)
- T-SORT-001 (nice-to-have)
- T-AUDIT-001 (importante mas não bloqueante)
- T-RENAME-001 (apenas branding)

### Revisão Necessária
- [ ] Revisão técnica por tech lead
- [ ] Security review por time de segurança
- [ ] Aprovação de roadmap por product owner
- [ ] Validação de prioridades com stakeholders
