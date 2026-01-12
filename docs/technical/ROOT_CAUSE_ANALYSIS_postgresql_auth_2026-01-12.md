# Análise de Causa Raiz - Falha de Autenticação PostgreSQL

**Data**: 2026-01-12 17:50  
**Container**: postgresql (b3d23fd1b086)  
**Imagem**: postgres:18-alpine3.21  
**Status**: ✅ PROBLEMA IDENTIFICADO  

---

## Diagnóstico Completo

### Configuração Esperada vs Real

| Parâmetro | Configuração (.env) | Container (env) | Banco de Dados Real |
|-----------|---------------------|-----------------|---------------------|
| POSTGRES_PASSWORD | W123Mudar | W123Mudar | ❌ **DIFERENTE** |
| Usuário padrão | postgres | postgres | postgres |
| Volume | Persistente | Persistente | ✅ Existente |

### Causa Raiz Identificada

🔴 **VOLUME PERSISTENTE COM SENHA ANTIGA**

O container PostgreSQL está configurado com volume persistente:
```yaml
volumes:
  - postgresql_data:/var/lib/postgresql
```

Mapeado para:
```
/home/yves_marinho/Documentos/DevOps/docker/postgres/postgres_data/
```

### O Problema

1. **Volume contém banco de dados pré-existente**
   - O PostgreSQL foi inicializado anteriormente com senha diferente
   - Volume persistente mantém todos os dados, incluindo usuários e senhas
   
2. **Container recriado há 4 minutos**
   - Timestamp do container: "4 minutes ago"
   - Variável `POSTGRES_PASSWORD=W123Mudar` foi setada
   - **MAS**: PostgreSQL ignora `POSTGRES_PASSWORD` quando o volume já tem dados inicializados

3. **Comportamento do PostgreSQL**
   ```
   if [ -s "$PGDATA/PG_VERSION" ]; then
       # Database already initialized, skip password setup
   else
       # Initialize database with POSTGRES_PASSWORD
   fi
   ```

### Evidências

#### 1. Container rodando com variáveis corretas
```bash
$ docker exec postgresql env | grep POSTGRES
POSTGRES_PASSWORD=W123Mudar
POSTGRESQL_POSTGRES_PASSWORD=W123Mudar
```

#### 2. Conexão falha de fora do container
```bash
$ PGPASSWORD='W123Mudar' psql -h 192.168.15.197 -U postgres -d postgres
psql: error: FATAL: password authentication failed for user "postgres"
```

#### 3. Banco de dados contém usuários antigos
```sql
List of roles:
- admin@vya.digital (Superuser)
- ai_process_user
- airflow_user
- app_workforce_user
- authelia_user
- backup (Superuser)
- botpress_user
- calendso_user
- chatwoot_user (Superuser, Create DB)
- confluence_user
... (17+ usuários)
```

**Conclusão**: Este não é um banco de dados novo, é um PostgreSQL em produção com múltiplas aplicações.

---

## Impacto da Descoberta

### ⚠️ ALERTA CRÍTICO

Este servidor PostgreSQL está sendo usado por **múltiplas aplicações em produção**:
- Airflow
- Botpress (incluindo Vivo)
- Chatwoot
- Calendso
- Confluence
- Authelia
- E outras aplicações

### Riscos Identificados

1. ❌ **Não podemos criar database test_inventory neste servidor**
   - Risco de interferir com aplicações em produção
   - Possível conflito de recursos
   
2. ❌ **Não devemos executar massa de dados de teste**
   - Pode impactar performance de aplicações reais
   - Banco de dados está em uso ativo

3. ❌ **Não é um ambiente de desenvolvimento isolado**
   - Este é claramente um servidor de produção/staging
   - Contém dados reais de múltiplas aplicações

---

## Soluções Recomendadas

### Opção 1: Usar Container PostgreSQL Isolado (RECOMENDADO)

Criar container PostgreSQL dedicado para testes:

```bash
# No servidor remoto ou local
docker run -d \
  --name postgres-test \
  -e POSTGRES_PASSWORD=W123Mudar \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=postgres \
  -p 5433:5432 \
  postgres:18-alpine3.21

# Atualizar script para usar porta 5433
```

**Vantagens**:
- ✅ Isolamento completo
- ✅ Não interfere com produção
- ✅ Pode ser destruído e recriado à vontade
- ✅ Senha conhecida e controlada

### Opção 2: PostgreSQL Local

Executar PostgreSQL localmente:

```bash
# Via Docker local
docker run -d \
  --name postgres-local-test \
  -e POSTGRES_PASSWORD=W123Mudar \
  -p 5432:5432 \
  postgres:15

# Atualizar script para usar localhost
POSTGRESQL_HOST = 'localhost'
```

**Vantagens**:
- ✅ Totalmente isolado do servidor remoto
- ✅ Mais rápido (sem latência de rede)
- ✅ Controle total

### Opção 3: Descobrir Senha Real (NÃO RECOMENDADO)

Tentar descobrir senha real do servidor de produção:

```bash
# Resetar senha do usuário postgres
docker exec -it postgresql psql -U postgres
ALTER USER postgres WITH PASSWORD 'W123Mudar';
```

**Desvantagens**:
- ❌ Modifica configuração de produção
- ❌ Pode quebrar aplicações existentes
- ❌ Risco de segurança
- ❌ Ainda compartilha recursos com produção

### Opção 4: Criar Usuário Dedicado

Criar usuário específico para testes no servidor existente:

```bash
# Dentro do container (descobrir senha do superuser primeiro)
docker exec postgresql psql -U admin@vya.digital -c "
CREATE USER test_user WITH PASSWORD 'W123Mudar' CREATEDB;
CREATE DATABASE test_inventory OWNER test_user;
"

# Atualizar script
POSTGRESQL_USER = 'test_user'
POSTGRESQL_PASSWORD = 'W123Mudar'
```

**Vantagens**:
- ✅ Não modifica usuários existentes
- ✅ Isolamento lógico

**Desvantagens**:
- ❌ Ainda compartilha recursos com produção
- ❌ Requer conhecer senha de superuser existente

---

## Descoberta da Senha Real

Para continuar usando este servidor, precisamos:

### Método 1: Verificar arquivo .pgpass
```bash
ssh yves_marinho@192.168.15.197 'cat ~/.pgpass'
```

### Método 2: Verificar docker-compose.yml histórico
```bash
ssh yves_marinho@192.168.15.197 'cd /caminho/do/compose && git log -p -- docker-compose.yaml'
```

### Método 3: Verificar variáveis de ambiente das aplicações
```bash
# Exemplo: Chatwoot
ssh yves_marinho@192.168.15.197 'docker inspect chatwoot_container | grep -i postgres'
```

### Método 4: Logs do container (improvável)
```bash
ssh yves_marinho@192.168.15.197 'docker logs postgresql 2>&1 | grep -i password'
```

---

## Recomendação Final

### ✅ SOLUÇÃO IMEDIATA

**Criar container PostgreSQL isolado para testes:**

1. **No servidor remoto** (porta 5433):
```bash
ssh yves_marinho@192.168.15.197
docker run -d \
  --name postgres-test-vya-backup \
  -e POSTGRES_PASSWORD=W123Mudar \
  -e POSTGRES_USER=postgres \
  -p 5433:5432 \
  --network app-network \
  postgres:15
```

2. **Atualizar script de teste**:
```python
POSTGRESQL_HOST = '192.168.15.197'
POSTGRESQL_PORT = 5433  # Nova porta
POSTGRESQL_USER = 'postgres'
POSTGRESQL_PASSWORD = 'W123Mudar'
```

3. **Re-executar geração de dados**:
```bash
python tests/generate_test_data.py
```

### Por que esta solução?

- ✅ Não interfere com produção
- ✅ Senha conhecida e controlada
- ✅ Pode ser destruído após testes
- ✅ Isolamento completo
- ✅ Implementação rápida (5 minutos)

---

## Lições Aprendidas

### 1. Sempre verificar ambiente antes de executar
- Listar usuários do banco de dados
- Verificar se há dados existentes
- Confirmar se é ambiente de desenvolvimento

### 2. Volume persistente != Senha reconfigurável
- PostgreSQL não reseta senha em volumes existentes
- `POSTGRES_PASSWORD` só funciona na inicialização

### 3. Identificar servidores de produção
- Múltiplos usuários = múltiplas aplicações
- Nomes como "chatwoot", "airflow" indicam produção
- Volume em `/docker/postgres/` sugere uso persistente

### 4. Isolamento de ambientes de teste
- Sempre usar containers/databases dedicados para testes
- Nunca testar em bancos de produção
- Usar portas diferentes para evitar conflitos

---

## Arquivos para Atualização

Após implementar container de teste, atualizar:

1. **tests/generate_test_data.py** - linha 34
   ```python
   POSTGRESQL_PORT = 5433  # Container de teste
   ```

2. **docs/technical/ERROR_REPORT_2026-01-12_postgresql_auth.md**
   - Adicionar esta análise de causa raiz
   - Marcar como resolvido

3. **docs/technical/TEST_DATA_GENERATION_SUMMARY_2026-01-12.md**
   - Atualizar status PostgreSQL
   - Documentar solução implementada

---

## Próximos Passos

1. ✅ **Criar container PostgreSQL isolado** (porta 5433)
2. ✅ **Atualizar script** para nova porta
3. ✅ **Re-executar geração de dados**
4. ✅ **Validar dados PostgreSQL**
5. ✅ **Prosseguir com Phase 10**

---

## Conclusão

🔴 **Problema Real**: Container PostgreSQL em **produção** com volume persistente mantendo senha antiga diferente de W123Mudar.

✅ **Solução**: Criar container PostgreSQL **isolado** para testes na porta 5433, mantendo produção intacta.

⚠️ **Alerta**: Servidor 192.168.15.197:5432 está em **uso ativo** por múltiplas aplicações. Não usar para testes.
