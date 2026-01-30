# Análise de Disaster Recovery - PostgreSQL Backup/Restore
**Data**: 2026-01-30  
**Problema**: Restore do PostgreSQL não inclui usuários e permissões  
**Objetivo**: Implementar backup/restore completo para Disaster Recovery

---

## 🔍 Problema Identificado

### Situação Atual
O backup do PostgreSQL usando `pg_dump` captura apenas:
- Estrutura das tabelas (DDL)
- Dados das tabelas (DML)
- Views, functions, sequences

**O que está faltando:**
- ❌ Usuários/Roles do banco
- ❌ Permissões (GRANT/REVOKE)
- ❌ Ownership dos objetos

### Evidências
```bash
# Teste realizado:
python -m python_backup restore \
  --file /tmp/bkp_test/botpress_db_20260130_180526.sql.gz \
  --instance home011-postgres --force

# Resultado:
✓ Banco restaurado
✗ Usuários não existem
✗ Permissões não aplicadas
```

---

## 📚 Especificações da Documentação

### 1. Requisito Original (PRODUCTION_READINESS_PLAN)
```
Goal: Complete UsersManager restore functionality

Tasks:
- T095: Implement _restore_mysql_users()
- T096: Implement _restore_postgresql_roles()
- T097: Unit tests for restore functionality

Implementation:
- Parse PostgreSQL pg_dumpall output
- Execute CREATE ROLE + GRANT commands
```

### 2. Comando Correto para Backup Completo
**Fonte**: `Postgres erro no restore.md`

Para **Disaster Recovery**, o PostgreSQL precisa:

```bash
# ERRADO (atual) - só backup de dados:
pg_dump --username=backup \
  --host=wfdb02.vya.digital \
  --port=5432 \
  --clean --create --if-exists \
  --format=plain database_name > backup.sql

# CORRETO - backup completo para DR:
# 1. Backup de roles (usuários globais):
pg_dumpall --username=postgres \
  --host=wfdb02.vya.digital \
  --port=5432 \
  --roles-only > roles.sql

# 2. Backup do banco (SEM ownership):
pg_dump --username=postgres \
  --host=wfdb02.vya.digital \
  --port=5432 \
  --clean --create --if-exists \
  --no-owner \
  --no-privileges \
  --format=plain database_name > database.sql
```

### 3. Problema com --no-owner e --no-privileges
**Fonte**: Análise da documentação PostgreSQL

- `--no-owner`: Não define o dono dos objetos (evita erro se usuário não existe)
- `--no-privileges`: Não exporta GRANT/REVOKE (evita erro de permissões)

**Mas**: Isso significa que **precisamos gerenciar roles separadamente**!

---

## 🎯 Solução Proposta

### Arquitetura para Disaster Recovery

```
BACKUP COMPLETO = roles.sql + database.sql
```

**Estrutura de arquivos:**
```
/backups/
  ├── botpress_db_20260130_180526.sql.gz      # Dados do banco
  └── botpress_db_20260130_180526_roles.sql.gz # Roles/usuários
```

### Fluxo de Backup
```
1. Conectar ao servidor PostgreSQL
2. Executar pg_dumpall --roles-only > roles.sql
3. Executar pg_dump database > database.sql
4. Comprimir ambos arquivos
5. Armazenar com nomenclatura consistente
```

### Fluxo de Restore (Disaster Recovery)
```
1. [STEP 1/5] Verificar conectividade com servidor
2. [STEP 2/5] Restaurar roles (se arquivo existe)
   - Descompactar roles.sql.gz
   - Executar: psql -f roles.sql
3. [STEP 3/5] Criar database (se não existe)
4. [STEP 4/5] Restaurar database
   - Descompactar database.sql.gz
   - Executar: psql -d database -f database.sql
5. [STEP 5/5] Verificar ownership e permissões
```

---

## ⚠️ Problema Atual no Código

### postgresql.py - get_backup_command()
```python
# ATUAL - INCORRETO para DR:
cmd_parts = [
    "pg_dump",
    f"--username={self.config.username}",
    f"--host={self.config.host}",
    f"--port={self.config.port}",
    "--clean",
    "--create",
    "--if-exists",
    "--no-privileges",  # ❌ Remove permissões
    "--no-owner",       # ❌ Remove ownership
]
```

**Problemas:**
1. `--no-privileges` e `--no-owner` foram adicionados mas SEM backup de roles
2. Não existe backup de `pg_dumpall --roles-only`
3. Restore tenta criar usuário 'backup' (hardcoded) mas não restaura usuários reais

---

## 🔧 Mudanças Necessárias

### 1. Modificar backup_database() - PostgreSQL
```python
def backup_database(self, database: str, output_path: str) -> bool:
    # Paths dos arquivos
    base_path = output_path.replace('.sql.gz', '')
    database_file = f"{base_path}.sql.gz"
    roles_file = f"{base_path}_roles.sql.gz"
    
    # STEP 1: Backup de roles
    logger.info("[PHASE 1/3] Backing up PostgreSQL roles...")
    success = self._backup_roles(roles_file)
    if not success:
        logger.warning("Roles backup failed, continuing with database only")
    
    # STEP 2: Backup do database
    logger.info("[PHASE 2/3] Backing up database structure and data...")
    # ... código atual de pg_dump ...
    
    # STEP 3: Criar arquivo .manifest com lista de arquivos
    logger.info("[PHASE 3/3] Creating backup manifest...")
    manifest = {
        'database': database,
        'timestamp': datetime.now().isoformat(),
        'files': {
            'database': os.path.basename(database_file),
            'roles': os.path.basename(roles_file) if os.path.exists(roles_file) else None
        }
    }
    with open(f"{base_path}.manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
```

### 2. Implementar _backup_roles()
```python
def _backup_roles(self, output_path: str) -> bool:
    """Backup PostgreSQL roles using pg_dumpall --roles-only"""
    try:
        temp_sql = output_path.replace('.gz', '')
        
        cmd = [
            "pg_dumpall",
            f"--username={self.config.username}",
            f"--host={self.config.host}",
            f"--port={self.config.port}",
            "--roles-only",
            f"> {temp_sql}"
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.config.password
        
        result = subprocess.run(
            ' '.join(cmd),
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"pg_dumpall failed: {result.stderr}")
            return False
        
        # Compress
        subprocess.run(f"gzip -f '{temp_sql}'", shell=True)
        return True
        
    except Exception as e:
        logger.error(f"Roles backup failed: {e}")
        return False
```

### 3. Modificar restore_database()
```python
def restore_database(self, database: str, backup_file: str) -> bool:
    base_path = backup_file.replace('.sql.gz', '').replace('.sql', '')
    database_file = backup_file
    roles_file = f"{base_path}_roles.sql.gz"
    
    # STEP 1: Verificar conectividade
    logger.info("[STEP 1/5] Verifying server connectivity...")
    # ... código atual ...
    
    # STEP 2: Restaurar roles (se arquivo existe)
    if os.path.exists(roles_file):
        logger.info("[STEP 2/5] Restoring PostgreSQL roles...")
        success = self._restore_roles(roles_file)
        if not success:
            logger.warning("Roles restore failed, continuing...")
    else:
        logger.warning("[STEP 2/5] Roles file not found, skipping...")
    
    # STEP 3: Criar database se não existe
    logger.info("[STEP 3/5] Checking if database exists...")
    # ... código atual ...
    
    # STEP 4: Restaurar database
    logger.info("[STEP 4/5] Restoring database content...")
    # ... código atual de psql ...
    
    # STEP 5: Verificar ownership
    logger.info("[STEP 5/5] Verifying database ownership...")
    self._fix_ownership(database)
```

### 4. Implementar _restore_roles()
```python
def _restore_roles(self, roles_file: str) -> bool:
    """Restore PostgreSQL roles from pg_dumpall backup"""
    try:
        # Decompress
        temp_sql = roles_file.replace('.gz', '')
        subprocess.run(f"gunzip -c '{roles_file}' > '{temp_sql}'", shell=True)
        
        # Execute
        cmd = [
            "psql",
            f"--username={self.config.username}",
            f"--host={self.config.host}",
            f"--port={self.config.port}",
            "--dbname=postgres",
            f"--file={temp_sql}"
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.config.password
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300
        )
        
        # Cleanup
        os.remove(temp_sql)
        
        if result.returncode != 0:
            logger.error(f"Roles restore failed: {result.stderr}")
            return False
            
        logger.info("Roles restored successfully")
        return True
        
    except Exception as e:
        logger.error(f"Roles restore error: {e}")
        return False
```

### 5. Remover código incorreto do restore
```python
# REMOVER este código que cria usuário hardcoded:
"""
# Step 3: Check and create backup user if needed
logger.info(f"[STEP 3/4] Verifying backup user exists...")
check_user_cmd = [...]
if '1' not in user_result.stdout:
    logger.info(f"[STEP 3/4] Creating backup user...")
    create_user_cmd = [...]
"""
```

---

## 📋 Task List

### Prioridade ALTA
- [ ] **T001**: Remover `--no-privileges` e `--no-owner` de get_backup_command()
- [ ] **T002**: Implementar método `_backup_roles()` em PostgreSQLAdapter
- [ ] **T003**: Modificar `backup_database()` para chamar `_backup_roles()`
- [ ] **T004**: Implementar método `_restore_roles()` em PostgreSQLAdapter
- [ ] **T005**: Modificar `restore_database()` para restaurar roles primeiro
- [ ] **T006**: Remover código de criação de usuário 'backup' hardcoded
- [ ] **T007**: Criar arquivo `.manifest.json` com lista de arquivos do backup
- [ ] **T008**: Testar backup completo (database + roles)
- [ ] **T009**: Testar restore completo em servidor limpo
- [ ] **T010**: Atualizar documentação com novo fluxo

### Prioridade MÉDIA
- [ ] **T011**: Implementar método `_fix_ownership()` para corrigir ownership pós-restore
- [ ] **T012**: Adicionar verificação de privilégios suficientes para pg_dumpall
- [ ] **T013**: Melhorar tratamento de erro quando roles backup falha
- [ ] **T014**: Adicionar opção CLI `--skip-roles` para backup sem roles

### Prioridade BAIXA
- [ ] **T015**: Implementar backup diferencial de roles (só mudanças)
- [ ] **T016**: Criar comando `vya-backupdb roles backup` separado
- [ ] **T017**: Documentar requisitos de permissões para pg_dumpall

---

## 🧪 Testes Necessários

### Teste 1: Backup Completo
```bash
# Executar backup
python -m python_backup backup \
  --instance wfdb02-postgres-botpress

# Verificar arquivos gerados:
ls -lh /var/backups/vya_backupdb/wfdb02/botpress_db/
# Esperado:
# - botpress_db_YYYYMMDD_HHMMSS.sql.gz
# - botpress_db_YYYYMMDD_HHMMSS_roles.sql.gz
# - botpress_db_YYYYMMDD_HHMMSS.manifest.json
```

### Teste 2: Restore em Servidor Limpo
```bash
# 1. Preparar servidor limpo (home011)
psql -U postgres -h 192.168.15.197 -c "DROP DATABASE IF EXISTS botpress_db_test;"

# 2. Verificar que não há usuários:
psql -U postgres -h 192.168.15.197 -c "\du"

# 3. Executar restore
python -m python_backup restore \
  --file /var/backups/.../botpress_db_YYYYMMDD_HHMMSS.sql.gz \
  --instance home011-postgres \
  --target botpress_db_test \
  --force

# 4. Verificar restauração:
# - Database existe
psql -U postgres -h 192.168.15.197 -l | grep botpress_db_test

# - Usuários foram criados
psql -U postgres -h 192.168.15.197 -c "\du"

# - Permissões aplicadas
psql -U postgres -h 192.168.15.197 -d botpress_db_test -c "\dp"

# - Ownership correto
psql -U postgres -h 192.168.15.197 -d botpress_db_test -c "\dt"
```

---

## 📊 Estimativa de Tempo

| Task | Descrição | Tempo |
|------|-----------|-------|
| T001-T003 | Implementar backup de roles | 2h |
| T004-T006 | Implementar restore de roles | 2h |
| T007 | Criar manifest | 30min |
| T008-T009 | Testes integração | 1h |
| T010 | Documentação | 30min |
| **TOTAL** | | **6h** |

---

## 🎯 Resultado Esperado

Após implementação:

```bash
# Backup gera 3 arquivos:
/var/backups/vya_backupdb/wfdb02/botpress_db/20260130/
├── botpress_db_20260130_180526.sql.gz         # Dados
├── botpress_db_20260130_180526_roles.sql.gz   # Usuários
└── botpress_db_20260130_180526.manifest.json  # Metadados

# Restore em servidor novo:
python -m python_backup restore \
  --file /path/to/botpress_db_20260130_180526.sql.gz \
  --instance home011-postgres \
  --force

# Output:
[STEP 1/5] Verifying server connectivity... ✓
[STEP 2/5] Restoring PostgreSQL roles... ✓
[STEP 3/5] Checking if database exists... ✓
[STEP 4/5] Restoring database content... ✓
[STEP 5/5] Verifying database ownership... ✓

✓ Restore completed successfully
  - Database: botpress_db
  - Users: 3 created
  - Tables: 45 restored
  - Permissions: Applied
```

---

## 📝 Notas Importantes

1. **Permissões necessárias**: O usuário de backup precisa ser SUPERUSER ou ter privilégios para executar `pg_dumpall`

2. **MySQL**: Situação similar - precisa backup de usuários com `SELECT * FROM mysql.user`

3. **Compatibilidade**: Testar restore entre versões diferentes do PostgreSQL

4. **Segurança**: Arquivos de roles contêm senhas hashadas - proteger adequadamente

5. **Performance**: `pg_dumpall --roles-only` é rápido (< 1s), não impacta backup
