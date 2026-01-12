# Relatório de Erro - PostgreSQL Authentication Failed

**Data**: 2026-01-12 17:36:31  
**Arquivo**: tests/generate_test_data.py  
**Linha**: 415  
**Severidade**: ERRO  
**Tipo**: OperationalError - Authentication

---

## Resumo do Erro

Script de geração de dados conseguiu conectar ao MySQL com sucesso mas falhou ao tentar autenticar no PostgreSQL servidor remoto.

## Contexto da Execução

### Progresso antes do erro:
✅ **MySQL - 100% Completo**
- Database `test_ecommerce` criado
- 4 tabelas criadas: customers, products, orders, order_items
- 1.000 clientes inseridos
- 500 produtos inseridos
- 2.000 pedidos inseridos
- 8.068 itens de pedidos inseridos
- 4 usuários MySQL criados com privilégios

❌ **PostgreSQL - Falhou na autenticação**
- Conexão de rede estabelecida (TCP handshake OK)
- Autenticação rejeitada pelo servidor

## Detalhes Técnicos

### Mensagem de Erro Principal
```
psycopg.OperationalError: connection failed: connection to server at "192.168.15.197", 
port 5432 failed: FATAL: password authentication failed for user "postgres"
```

### Stack Trace Resumido
```
File "tests/generate_test_data.py", line 415, in setup_postgresql_database
    with engine.connect() as conn:
File "sqlalchemy/engine/base.py", line 3285, in connect
    return self._connection_cls(self)
File "psycopg/connection.py", line 122, in connect
    raise last_ex.with_traceback(None)
sqlalchemy.exc.OperationalError: password authentication failed for user "postgres"
```

### Parâmetros de Conexão Utilizados
```python
POSTGRESQL_HOST = '192.168.15.197'
POSTGRESQL_PORT = 5432
POSTGRESQL_USER = 'postgres'
POSTGRESQL_PASSWORD = 'W123Mudar'
PG_ADMIN_URL = "postgresql+psycopg://postgres:W123Mudar@192.168.15.197:5432/postgres"
```

## Análise

### Possíveis Causas

1. **Senha incorreta**: A senha 'W123Mudar' pode estar diferente no servidor PostgreSQL
2. **Configuração pg_hba.conf**: Servidor pode não permitir autenticação por senha de hosts remotos
3. **Método de autenticação diferente**: PostgreSQL pode estar configurado para usar trust, peer, ou certificados
4. **Usuário não existe**: Usuário 'postgres' pode não estar criado no servidor
5. **Senha expirada**: PostgreSQL pode ter política de expiração de senhas

### Comparação MySQL vs PostgreSQL

| Aspecto | MySQL | PostgreSQL |
|---------|-------|------------|
| Conexão de rede | ✅ Sucesso | ✅ Sucesso |
| Autenticação | ✅ Sucesso | ❌ Falhou |
| Credenciais | root/W123Mudar | postgres/W123Mudar |
| Porta | 3306 | 5432 |

**Observação**: Como o MySQL autenticou com sucesso usando as mesmas credenciais de padrão, é provável que o PostgreSQL tenha senha ou configuração diferente.

## Diagnóstico Recomendado

### Verificações no Servidor Remoto

1. **Testar conexão direta**:
```bash
psql -h 192.168.15.197 -U postgres -d postgres -W
```

2. **Verificar pg_hba.conf**:
```bash
# No servidor
cat /etc/postgresql/*/main/pg_hba.conf | grep -v "^#" | grep -v "^$"
```

Procurar por linhas como:
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
host    all             all             192.168.15.0/24         md5
host    all             postgres        0.0.0.0/0               scram-sha-256
```

3. **Verificar se container PostgreSQL está rodando**:
```bash
docker ps | grep postgres
docker logs <postgres-container-id>
```

4. **Tentar resetar senha do usuário postgres**:
```bash
docker exec -it <postgres-container-id> psql -U postgres
ALTER USER postgres WITH PASSWORD 'W123Mudar';
```

### Possíveis Soluções

#### Solução 1: Verificar senha correta no servidor
```bash
# Conectar via docker
docker exec -it <postgres-container-id> bash
psql -U postgres
\password postgres
# Digite a nova senha: W123Mudar
```

#### Solução 2: Ajustar pg_hba.conf para permitir conexões remotas
```bash
# Editar no container ou host
echo "host all postgres 0.0.0.0/0 md5" >> /etc/postgresql/*/main/pg_hba.conf
docker restart <postgres-container-id>
```

#### Solução 3: Usar variável de ambiente para senha
```python
# No script, adicionar fallback
import os
POSTGRESQL_PASSWORD = os.getenv('PGPASSWORD', 'W123Mudar')
```

## Impacto

### Funcionalidades Bloqueadas
- ❌ Geração de dados PostgreSQL (suppliers, categories, inventory_items, stock_movements)
- ❌ Criação de roles PostgreSQL (app_role, readonly_role, backup_role, analytics_role)
- ❌ Testes de backup de usuários PostgreSQL (Phase 10)
- ❌ Validação de pg_dumpall --roles-only

### Funcionalidades Disponíveis
- ✅ Dados MySQL completos para testes
- ✅ Usuários MySQL para validar SHOW GRANTS
- ✅ Testes de backup/restore MySQL

## Workaround Temporário

Enquanto a senha PostgreSQL não for corrigida, é possível:

1. **Prosseguir com implementação Phase 10 MySQL**:
   - Implementar UsersManager para MySQL
   - Testar backup de usuários MySQL
   - Validar SHOW GRANTS extraction

2. **Criar script separado apenas para PostgreSQL**:
```python
# generate_postgresql_data.py
# Permite testar diferentes senhas sem re-gerar MySQL
```

3. **Usar PostgreSQL local para desenvolvimento**:
```bash
docker run -d -p 5433:5432 -e POSTGRES_PASSWORD=W123Mudar postgres:15
# Usar porta 5433 localmente para não conflitar
```

## Status

- ✅ **MySQL**: 100% completo - dados e usuários criados
- ❌ **PostgreSQL**: Bloqueado por autenticação
- ⏳ **Próximo passo**: Validar senha PostgreSQL no servidor remoto

## Ações Necessárias

### Imediato (Crítico)
1. Acessar servidor 192.168.15.197
2. Verificar senha do usuário postgres no PostgreSQL
3. Confirmar configuração pg_hba.conf permite conexões remotas
4. Testar conexão manualmente com psql

### Curto Prazo
1. Documentar senha correta em local seguro (não em código)
2. Re-executar script após correção de autenticação
3. Validar criação completa de dados PostgreSQL

### Médio Prazo
1. Implementar gestão de credenciais com variables de ambiente
2. Adicionar retry logic para falhas de conexão
3. Criar health check antes de executar operações bulk

## Referências

- [PostgreSQL Authentication Methods](https://www.postgresql.org/docs/current/auth-methods.html)
- [pg_hba.conf Configuration](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)
- [psycopg Connection Parameters](https://www.psycopg.org/psycopg3/docs/api/connections.html)
- [SQLAlchemy PostgreSQL Dialects](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)

## Log Completo

Ver arquivo: [logs/generate_test_data_error_2026-01-12.log](../../logs/)

```
================================================================================
  POSTGRESQL - Setup Database
================================================================================

❌ Erro durante execução: (psycopg.OperationalError) connection failed: 
connection to server at "192.168.15.197", port 5432 failed: 
FATAL:  password authentication failed for user "postgres"
```
