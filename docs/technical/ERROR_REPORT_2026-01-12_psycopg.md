# Relatório de Erro - ModuleNotFoundError: psycopg2

**Data**: 2026-01-12 17:32:46  
**Arquivo**: tests/generate_test_data.py  
**Linha**: 413  
**Severidade**: ERRO  

---

## Resumo do Erro

Script de geração de dados de teste falhou ao tentar conectar ao PostgreSQL devido à incompatibilidade entre o driver instalado e o dialect SQLAlchemy especificado.

## Contexto da Execução

### Progresso antes do erro:
✅ **MySQL - Completo**
- Database `test_ecommerce` criado
- 4 tabelas criadas: customers, products, orders, order_items
- 1.000 clientes inseridos
- 500 produtos inseridos
- 2.000 pedidos inseridos
- 7.981 itens de pedidos inseridos
- 4 usuários MySQL criados (app_user, readonly_user, backup_user, analytics_user)

❌ **PostgreSQL - Falhou na inicialização**
- Erro ao criar engine de conexão

## Detalhes Técnicos

### Stack Trace
```
Traceback (most recent call last):
  File "tests/generate_test_data.py", line 737, in main
    setup_postgresql_database()
  File "tests/generate_test_data.py", line 413, in setup_postgresql_database
    engine = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool, echo=False)
  File "sqlalchemy/engine/create.py", line 617, in create_engine
    dbapi = dbapi_meth(**dbapi_args)
  File "sqlalchemy/dialects/postgresql/psycopg2.py", line 696, in import_dbapi
    import psycopg2
ModuleNotFoundError: No module named 'psycopg2'
```

### Causa Raiz

**Incompatibilidade de Driver**:
- **Dialect especificado**: `postgresql+psycopg2://` (SQLAlchemy tentando usar psycopg2)
- **Driver instalado**: `psycopg 3.3.2` e `psycopg-binary 3.3.2` (versão 3, nova geração)
- **Driver ausente**: `psycopg2` (versão 2, legado)

### Verificação do Ambiente
```bash
$ uv pip list | grep -i pg
psycopg            3.3.2
psycopg-binary     3.3.2
```

## Análise

### Por que o erro ocorreu?

1. **Connection string incorreta**: Script usava `postgresql+psycopg2://` que é o dialect para psycopg2 (v2)
2. **Driver moderno instalado**: Projeto usa psycopg v3, que é a nova geração (mais rápido, melhor suporte async)
3. **SQLAlchemy não encontrou o módulo**: Ao processar o dialect `psycopg2`, SQLAlchemy tentou `import psycopg2`, que não existe no ambiente

### Diferenças entre psycopg2 e psycopg (v3)

| Aspecto | psycopg2 (v2) | psycopg (v3) |
|---------|---------------|--------------|
| Módulo Python | `psycopg2` | `psycopg` |
| SQLAlchemy dialect | `postgresql+psycopg2://` | `postgresql+psycopg://` |
| Suporte async | Limitado | Nativo |
| Performance | Boa | Melhor |
| Status | Manutenção | Desenvolvimento ativo |

## Solução Implementada

### Alteração no Código

**Arquivo**: tests/generate_test_data.py  
**Linhas**: 43-44

**Antes**:
```python
PG_ADMIN_URL = f"postgresql+psycopg2://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/postgres"
PG_DB_URL = f"postgresql+psycopg2://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/test_inventory"
```

**Depois**:
```python
PG_ADMIN_URL = f"postgresql+psycopg://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/postgres"
PG_DB_URL = f"postgresql+psycopg://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/test_inventory"
```

### Justificativa

- Alinha o dialect SQLAlchemy com o driver realmente instalado
- Aproveita melhorias de performance do psycopg v3
- Evita instalação de dependência legada desnecessária
- Mantém compatibilidade com arquitetura moderna do projeto

## Lições Aprendidas

### Boas Práticas

1. **Verificar drivers antes de executar**: Sempre confirmar quais drivers PostgreSQL estão instalados
2. **Consistência de versões**: Manter connection strings alinhadas com drivers disponíveis
3. **Documentação de dependências**: Especificar claramente versões de drivers em pyproject.toml

### Prevenção Futura

```python
# Adicionar validação de driver no início do script
try:
    import psycopg
    PG_DIALECT = "postgresql+psycopg"
except ImportError:
    try:
        import psycopg2
        PG_DIALECT = "postgresql+psycopg2"
    except ImportError:
        raise ImportError("Nenhum driver PostgreSQL encontrado. Instale psycopg ou psycopg2-binary")
```

## Referências

- [SQLAlchemy PostgreSQL Dialects](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [psycopg 3 Documentation](https://www.psycopg.org/psycopg3/)
- [Migration Guide psycopg2 → psycopg3](https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html)

## Status

- ✅ **Erro identificado**: ModuleNotFoundError para psycopg2
- ✅ **Causa raiz determinada**: Incompatibilidade dialect vs driver
- ✅ **Solução aplicada**: Alterado dialect para psycopg (v3)
- ⏳ **Validação pendente**: Re-execução do script para confirmar funcionamento PostgreSQL

## Próximos Passos

1. Re-executar script de geração de dados: `python tests/generate_test_data.py`
2. Validar criação do database PostgreSQL `test_inventory`
3. Confirmar inserção de dados: suppliers, categories, inventory_items, stock_movements
4. Verificar criação de roles PostgreSQL (app_role, readonly_role, backup_role, analytics_role)
