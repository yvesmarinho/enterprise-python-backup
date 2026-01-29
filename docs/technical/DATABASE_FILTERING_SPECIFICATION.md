# Especificação: Filtragem de Databases para Backup

**Versão:** 2.0  
**Data:** 2026-01-26  
**Status:** Proposta de Implementação  

## Visão Geral

Este documento especifica o comportamento e precedência dos parâmetros `database` e `db_ignore` no sistema de backup, definindo regras claras para determinar quais databases serão incluídas ou excluídas durante operações de backup.

## Contexto Atual

### Situação Existente (v1.x)

O sistema atual possui:

```python
# config/loader.py - DatabaseConfig
db_list: List[str]      # Databases específicas (vazio = todas)
db_ignore: List[str]    # Databases a ignorar
```

**Limitações:**
- Nomes inconsistentes (`db_list` vs `database`)
- Comportamento não documentado claramente
- Falta de especificação de precedência
- Não alinhado com formatos de configuração externos (Azure, AWS, etc.)

### Formato Proposto (v2.0)

```python
# config/models.py - DatabaseConfig
database: List[str]     # Databases específicas a incluir (vazio = todas)
db_ignore: List[str]    # Databases a excluir (vazio = não exclui nada)
```

**Alinhamento:**
- Compatible com formatos Azure PostgreSQL/MySQL
- Nomenclatura mais intuitiva
- Comportamento explícito e documentado

## Definição dos Parâmetros

### 1. Parâmetro `database`

**Tipo:** `List[str]`  
**Função:** Especifica quais databases devem ser incluídas no backup  
**Valores Possíveis:**
- `[]` (lista vazia) → Todas as databases disponíveis
- `["db1"]` → Apenas a database "db1"
- `["db1", "db2", "db3"]` → Apenas as databases especificadas

**Exemplos:**

```json
// Todas as databases
{
  "id": "prod-postgres",
  "type": "postgresql",
  "host": "postgres.example.com",
  "database": [],
  "db_ignore": []
}

// Apenas app_workforce
{
  "id": "journey-dev",
  "type": "postgresql",
  "host": "journeydb-dev.postgres.database.azure.com",
  "database": ["app_workforce"],
  "db_ignore": []
}

// Múltiplas databases específicas
{
  "id": "multi-app",
  "type": "mysql",
  "host": "mysql.example.com",
  "database": ["erp", "crm", "analytics"],
  "db_ignore": []
}
```

### 2. Parâmetro `db_ignore`

**Tipo:** `List[str]`  
**Função:** Especifica quais databases devem ser excluídas do backup  
**Valores Possíveis:**
- `[]` (lista vazia) → Nenhuma database é excluída (exceto databases de sistema)
- `["test_db"]` → Exclui a database "test_db"
- `["test_*", "dev_*"]` → Exclui databases que correspondem aos padrões (futura implementação com glob patterns)

**Comportamento Especial:**
- Databases de sistema são **sempre excluídas** automaticamente, independente de `db_ignore`
- `db_ignore` é aplicado **após** a inclusão definida por `database`

**Exemplos:**

```json
// Todas exceto test/dev
{
  "id": "prod-mysql",
  "type": "mysql",
  "host": "mysql.example.com",
  "database": [],
  "db_ignore": ["test_db", "dev_db", "staging_db"]
}

// Específicas, excluindo algumas
{
  "id": "multi-tenant",
  "type": "postgresql",
  "host": "postgres.example.com",
  "database": ["tenant1", "tenant2", "tenant3", "tenant4"],
  "db_ignore": ["tenant3"]  // tenant3 será excluído
}
```

## Regras de Precedência

### Ordem de Aplicação (Prioridade)

A filtragem de databases segue a seguinte ordem de precedência:

```
1. INCLUSÃO (database)     ← Define o conjunto inicial
2. EXCLUSÃO (db_ignore)    ← Remove databases do conjunto
3. SISTEMAS INTERNOS       ← Remove databases de sistema (sempre)
```

### Matriz de Decisão

| `database` | `db_ignore` | Resultado | Descrição |
|------------|-------------|-----------|-----------|
| `[]` | `[]` | Todas (exceto sistema) | Comportamento padrão |
| `[]` | `["test"]` | Todas exceto "test" (e sistema) | Blacklist approach |
| `["app"]` | `[]` | Apenas "app" | Whitelist approach |
| `["a", "b"]` | `["b"]` | Apenas "a" | Inclusão com exclusão |
| `["app"]` | `["test"]` | Apenas "app" | `db_ignore` não tem efeito se DB não está em `database` |

### Pseudocódigo de Filtragem

```python
def get_databases_to_backup(all_dbs, database, db_ignore):
    """
    Determina quais databases devem ser backupeadas.
    
    Args:
        all_dbs: Lista de todas as databases disponíveis no servidor
        database: Lista de databases a incluir ([] = todas)
        db_ignore: Lista de databases a excluir
    
    Returns:
        Lista final de databases para backup
    """
    # Etapa 1: Aplicar INCLUSÃO (database)
    if database == [] or database is None:
        # Lista vazia = TODAS as databases
        included = all_dbs
    else:
        # Lista não vazia = APENAS as especificadas
        included = [db for db in all_dbs if db in database]
    
    # Etapa 2: Aplicar EXCLUSÃO (db_ignore)
    if db_ignore != [] and db_ignore is not None:
        included = [db for db in included if db not in db_ignore]
    
    # Etapa 3: Remover DATABASES DE SISTEMA (sempre)
    system_databases = get_system_databases(db_type)
    included = [db for db in included if db not in system_databases]
    
    return included
```

## Databases de Sistema

Databases de sistema são **sempre excluídas** automaticamente:

### MySQL
```python
MYSQL_SYSTEM_DATABASES = [
    "information_schema",
    "performance_schema", 
    "mysql",
    "sys"
]
```

### PostgreSQL
```python
POSTGRESQL_SYSTEM_DATABASES = [
    "postgres",
    "template0",
    "template1"
]
```

**Importante:** Mesmo se uma database de sistema for explicitamente incluída em `database`, ela será removida na Etapa 3.

## Cenários de Uso

### Cenário 1: Backup Completo (Padrão)

**Requisito:** Fazer backup de todas as databases de uma instância, excluindo apenas as de sistema.

```json
{
  "database": [],
  "db_ignore": []
}
```

**Resultado:**
```
all_dbs = ["app1", "app2", "test", "mysql", "information_schema"]
↓ Etapa 1 (inclusão): ["app1", "app2", "test", "mysql", "information_schema"]
↓ Etapa 2 (exclusão): ["app1", "app2", "test", "mysql", "information_schema"]
↓ Etapa 3 (sistema):  ["app1", "app2", "test"]
✓ Databases backupeadas: app1, app2, test
```

### Cenário 2: Backup Seletivo (Whitelist)

**Requisito:** Fazer backup apenas da database de produção, ignorando dev/test.

```json
{
  "database": ["app_workforce"],
  "db_ignore": []
}
```

**Resultado:**
```
all_dbs = ["app_workforce", "app_test", "app_dev", "postgres"]
↓ Etapa 1 (inclusão): ["app_workforce"]
↓ Etapa 2 (exclusão): ["app_workforce"]
↓ Etapa 3 (sistema):  ["app_workforce"]
✓ Databases backupeadas: app_workforce
```

### Cenário 3: Backup Completo com Exclusões (Blacklist)

**Requisito:** Fazer backup de todas as databases, exceto ambientes de teste.

```json
{
  "database": [],
  "db_ignore": ["test_db", "dev_db", "staging_db"]
}
```

**Resultado:**
```
all_dbs = ["prod", "test_db", "dev_db", "staging_db", "analytics", "mysql"]
↓ Etapa 1 (inclusão): ["prod", "test_db", "dev_db", "staging_db", "analytics", "mysql"]
↓ Etapa 2 (exclusão): ["prod", "analytics", "mysql"]
↓ Etapa 3 (sistema):  ["prod", "analytics"]
✓ Databases backupeadas: prod, analytics
```

### Cenário 4: Combinação (Whitelist + Blacklist)

**Requisito:** Fazer backup de databases específicas, mas excluir uma delas temporariamente.

```json
{
  "database": ["tenant1", "tenant2", "tenant3", "tenant4"],
  "db_ignore": ["tenant3"]
}
```

**Resultado:**
```
all_dbs = ["tenant1", "tenant2", "tenant3", "tenant4", "tenant5", "admin"]
↓ Etapa 1 (inclusão): ["tenant1", "tenant2", "tenant3", "tenant4"]
↓ Etapa 2 (exclusão): ["tenant1", "tenant2", "tenant4"]
↓ Etapa 3 (sistema):  ["tenant1", "tenant2", "tenant4"]
✓ Databases backupeadas: tenant1, tenant2, tenant4
```

### Cenário 5: Exclusão Redundante (Sem Efeito)

**Requisito:** Lista específica com exclusão de database não presente.

```json
{
  "database": ["app_prod"],
  "db_ignore": ["app_test"]  // Sem efeito: app_test não está em database
}
```

**Resultado:**
```
all_dbs = ["app_prod", "app_test", "app_dev"]
↓ Etapa 1 (inclusão): ["app_prod"]
↓ Etapa 2 (exclusão): ["app_prod"]  // db_ignore não encontra "app_test"
↓ Etapa 3 (sistema):  ["app_prod"]
✓ Databases backupeadas: app_prod
```

## Compatibilidade com Formato Legado

### Migração de `db_list` para `database`

**Formato Antigo (vya_backupbd.json):**
```json
{
  "db_config": [
    {
      "id_dbms": 1,
      "dbms": "postgresql",
      "host": "postgres.example.com",
      "db_list": ["app1", "app2"],
      "db_ignore": "test,dev"  // String separada por vírgula
    }
  ]
}
```

**Formato Novo (config.yaml / vault integration):**
```json
{
  "credentials": [
    {
      "id": "prod-postgres",
      "type": "postgresql",
      "host": "postgres.example.com",
      "database": ["app1", "app2"],
      "db_ignore": ["test", "dev"]  // Lista
    }
  ]
}
```

### Adapter de Compatibilidade

```python
def migrate_db_config(old_config: dict) -> dict:
    """Converte formato legado para novo formato."""
    new_config = {
        "id": f"{old_config['dbms']}-{old_config['id_dbms']}",
        "type": old_config["dbms"],
        "host": old_config["host"],
        "port": old_config["port"],
        "username": old_config["user"],
        "password": old_config["secret"],
        "database": old_config.get("db_list", []),
        "db_ignore": (
            old_config["db_ignore"].split(",")
            if isinstance(old_config.get("db_ignore"), str)
            else old_config.get("db_ignore", [])
        ),
    }
    return new_config
```

## Validações e Erros

### Validações no Carregamento

```python
class DatabaseConfig(BaseModel):
    database: List[str] = Field(default_factory=list)
    db_ignore: List[str] = Field(default_factory=list)
    
    @field_validator("database")
    def validate_database_names(cls, v):
        """Valida nomes de databases."""
        for db_name in v:
            if not db_name or not db_name.strip():
                raise ValueError("Database name cannot be empty")
            if any(char in db_name for char in [";", "--", "/*"]):
                raise ValueError(f"Invalid database name: {db_name}")
        return v
    
    @field_validator("db_ignore")
    def validate_ignore_names(cls, v):
        """Valida nomes de databases a ignorar."""
        for db_name in v:
            if not db_name or not db_name.strip():
                raise ValueError("Database name cannot be empty")
        return v
```

### Tratamento de Erros

| Erro | Causa | Comportamento |
|------|-------|---------------|
| `database` especifica DB inexistente | DB não existe no servidor | ⚠️ Warning no log, continua sem ela |
| `db_ignore` referencia DB inexistente | DB não existe no servidor | ℹ️ Info no log, sem impacto |
| `database` e `db_ignore` vazios | Configuração padrão | ✓ Backup de todas (exceto sistema) |
| Todas as DBs excluídas | Combinação resulta em lista vazia | ❌ Erro, aborta backup da instância |
| Nome de DB inválido | Caracteres especiais SQL | ❌ Erro na validação, aborta |

## Logging e Auditoria

### Log de Filtragem

```
INFO: Processing instance journey-dev-postgres
DEBUG: All databases found: ['app_workforce', 'app_test', 'postgres', 'template0']
DEBUG: Applying database filter (whitelist): ['app_workforce']
DEBUG: Applying db_ignore filter (blacklist): []
DEBUG: Removing system databases: ['postgres', 'template0']
INFO: Final databases to backup: ['app_workforce']
```

### Métricas

```python
{
  "instance_id": "journey-dev-postgres",
  "total_databases": 4,
  "included_by_whitelist": 1,
  "excluded_by_blacklist": 0,
  "excluded_system": 2,
  "final_count": 1,
  "databases_backed_up": ["app_workforce"]
}
```

## Implementação

### Mudanças Necessárias

#### 1. Models ([config/models.py](cci:7://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/src/python_backup/config/models.py:0:0-0:0))

```python
class DatabaseConfig(BaseModel):
    # ...
    database: list[str] = Field(
        default_factory=list,
        description="Databases to include (empty = all)"
    )
    db_ignore: list[str] = Field(
        default_factory=list,
        description="Databases to exclude"
    )
    # Remover: exclude_databases (substituído por lógica interna)
```

#### 2. Loader Legado ([config/loader.py](cci:7://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/src/python_backup/config/loader.py:0:0-0:0))

```python
@dataclass
class DatabaseConfig:
    # ...
    database: List[str]  # Renomear de db_list
    db_ignore: List[str]
    
    @classmethod
    def from_dict(cls, data: dict):
        # Suporte a ambos os nomes para backward compatibility
        database = data.get("database") or data.get("db_list", [])
        # ...
```

#### 3. Base Adapter ([db/base.py](cci:7://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/src/python_backup/db/base.py:65:4-83:51))

```python
def get_filtered_databases(self, all_databases: list[str]) -> list[str]:
    """
    Apply database filtering with precedence rules.
    
    Order:
    1. Include (database)
    2. Exclude (db_ignore)
    3. System databases
    """
    # Etapa 1: Aplicar inclusão
    if not self.config.database:
        included = all_databases
    else:
        included = [db for db in all_databases if db in self.config.database]
    
    # Etapa 2: Aplicar exclusão
    if self.config.db_ignore:
        included = [db for db in included if db not in self.config.db_ignore]
    
    # Etapa 3: Remover sistema
    included = self.filter_system_databases(included)
    
    return included
```

#### 4. CLI ([cli.py](cci:7://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/src/python_backup/cli.py:220:8-223:103))

```python
# Substituir lógica de filtragem manual por:
temp_adapter = get_database_adapter(temp_config)
all_databases = temp_adapter.get_databases()
databases_to_backup = temp_adapter.get_filtered_databases(all_databases)
```

### Testes Necessários

```python
# tests/unit/test_database_filtering.py

def test_empty_database_and_empty_ignore():
    """Cenário 1: Backup completo."""
    
def test_whitelist_single():
    """Cenário 2: Backup seletivo."""
    
def test_blacklist_multiple():
    """Cenário 3: Backup com exclusões."""
    
def test_whitelist_with_blacklist():
    """Cenário 4: Combinação."""
    
def test_redundant_ignore():
    """Cenário 5: Exclusão sem efeito."""
    
def test_system_databases_always_excluded():
    """Databases de sistema sempre removidas."""
    
def test_all_excluded_error():
    """Erro quando todas as DBs são excluídas."""
```

## Roadmap

### Versão 2.0 (Atual)
- ✅ Especificação completa
- ⏳ Renomear `db_list` → `database`
- ⏳ Implementar lógica de precedência
- ⏳ Testes unitários
- ⏳ Testes de integração
- ⏳ Migração de configurações legadas

### Versão 2.1 (Futuro)
- [ ] Suporte a glob patterns em `db_ignore` (`test_*`, `dev_*`)
- [ ] Suporte a regex patterns (`^app_\d+$`)
- [ ] Validação de existência de databases antes do backup
- [ ] Cache de lista de databases (reduzir queries)

### Versão 3.0 (Futuro Distante)
- [ ] Filtragem por tags/labels
- [ ] Filtragem por tamanho de database
- [ ] Filtragem por última modificação
- [ ] Políticas de backup hierárquicas (instance → database → table)

## Referências

- **Issue Original:** [journey-test.json compatibility](cci:1://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/.secrets/journey-test.json:0:0-0:0)
- **Código Atual:** 
  - [config/loader.py](cci:7://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/src/python_backup/config/loader.py:0:0-0:0)
  - [config/models.py](cci:7://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/src/python_backup/config/models.py:0:0-0:0)
  - [db/base.py](cci:7://file:///home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup/src/python_backup/db/base.py:0:0-0:0)
- **Azure PostgreSQL:** https://learn.microsoft.com/azure/postgresql/flexible-server/
- **AWS RDS:** https://docs.aws.amazon.com/rds/

---

**Última Atualização:** 2026-01-26  
**Autor:** Sistema de Backup VYA  
**Status:** ⏳ Aguardando Implementação
