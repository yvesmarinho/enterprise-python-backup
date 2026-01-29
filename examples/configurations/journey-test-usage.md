# Exemplo: Usando o novo formato de filtragem de databases

Este exemplo demonstra como usar o arquivo de configuração com os novos parâmetros `database` e `db_ignore`.

## Formato do Arquivo de Configuração

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
      "id": "journey-dev-postgres",
      "username": "journeydb_user",
      "password": "i@w123Mudar#2025",
      "host": "journeydb-dev.postgres.database.azure.com",
      "database": ["app_workforce"],
      "db_ignore": [],
      "port": 5432,
      "sslmode": "allow"
    }
  ]
}
```

## Como usar com vya-backupdb

### 1. Migrar credenciais para o vault

```bash
# Adicionar credencial no vault
vya-backupdb vault-add \
  --id journey-dev-postgres \
  --username journeydb_user \
  --password "i@w123Mudar#2025" \
  --description "Azure PostgreSQL Journey Dev"
```

### 2. Configurar no vya_backupbd.json (Formato Legado)

```json
{
  "db_config": [
    {
      "id_dbms": 1,
      "dbms": "postgresql",
      "host": "journeydb-dev.postgres.database.azure.com",
      "port": 5432,
      "user": "journeydb_user",
      "secret": "i@w123Mudar#2025",
      "database": ["app_workforce"],
      "db_ignore": [],
      "enabled": true
    }
  ]
}
```

### 3. Fazer backup

```bash
# Backup da database específica
vya-backupdb backup --instance 1

# Ou backup direto especificando database
vya-backupdb backup --instance 1 --database app_workforce
```

## Cenários de Uso

### Cenário 1: Backup apenas de app_workforce

```json
{
  "database": ["app_workforce"],
  "db_ignore": []
}
```

**Resultado**: Apenas `app_workforce` será backupeado.

### Cenário 2: Backup de todas exceto test

```json
{
  "database": [],
  "db_ignore": ["test_db", "dev_db"]
}
```

**Resultado**: Todas as databases exceto `test_db`, `dev_db` e databases de sistema.

### Cenário 3: Backup de múltiplas databases específicas

```json
{
  "database": ["app_workforce", "app_analytics", "app_reports"],
  "db_ignore": []
}
```

**Resultado**: Apenas as 3 databases especificadas.

### Cenário 4: Whitelist com exclusão

```json
{
  "database": ["tenant1", "tenant2", "tenant3"],
  "db_ignore": ["tenant2"]
}
```

**Resultado**: `tenant1` e `tenant3` (tenant2 excluído).

## Precedência de Filtragem

```
1. INCLUSÃO (database)  → Define quais incluir
2. EXCLUSÃO (db_ignore) → Remove do conjunto
3. SISTEMA              → Remove postgres, template0, template1 (sempre)
```

## Compatibilidade

O sistema mantém compatibilidade com o formato antigo:

- `db_list` → `database` (automaticamente convertido)
- `exclude_databases` → `db_ignore` (automaticamente convertido)
- String CSV → Lista (automaticamente convertido)

## Validação

Para testar se a configuração está correta:

```bash
# Testar conexão
vya-backupdb test-connection --instance 1

# Listar databases disponíveis
vya-backupdb backup --instance 1 --dry-run
```

## Logs

Durante o backup, você verá logs detalhados da filtragem:

```
INFO: Processing instance journey-dev-postgres
DEBUG: All databases found: ['app_workforce', 'app_test', 'postgres', 'template0']
DEBUG: Applying database filter (whitelist): ['app_workforce']
DEBUG: Applying db_ignore filter (blacklist): []
DEBUG: Removing system databases: ['postgres', 'template0']
INFO: Final databases to backup: ['app_workforce']
```

---

**Documentação Completa**: [DATABASE_FILTERING_SPECIFICATION.md](../technical/DATABASE_FILTERING_SPECIFICATION.md)
