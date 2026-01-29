# Recursos Python para Aplicação Enterprise N8N Backup/Restore

## Introdução

Este documento detalha os recursos e bibliotecas Python 3 necessários para implementar uma aplicação **segura, robusta e enterprise-grade** para backup/restore de N8N integrada ao Docker. O foco está em garantir operações atômicas, verificações de integridade e recuperação automática em cenários de falha.

---

## Índice

1. [Bibliotecas Core do Python](#bibliotecas-core-do-python)
2. [Integração Docker](#integração-docker)
3. [Gerenciamento de Estado de Container](#gerenciamento-de-estado-de-container)
4. [Verificação de Integridade e Healthchecks](#verificação-de-integridade-e-healthchecks)
5. [Segurança e Gestão de Credenciais](#segurança-e-gestão-de-credenciais)
6. [Logging e Auditoria](#logging-e-auditoria)
7. [Manipulação de Dados e Validação](#manipulação-de-dados-e-validação)
8. [Integração com Repositórios de Backup](#integração-com-repositórios-de-backup)
9. [Tratamento de Erros e Recovery](#tratamento-de-erros-e-recovery)
10. [Testes e Qualidade](#testes-e-qualidade)
11. [Configuração e Environment](#configuração-e-environment)
12. [Cenários Críticos - Análise Detalhada](#cenários-críticos---análise-detalhada)

---

## Bibliotecas Core do Python

### 1. **docker** (docker-py / Docker SDK for Python)

**Instalação**: `pip install docker`

**Propósito**: Interface Python oficial para Docker Engine API, permitindo controle programático completo de containers, imagens, volumes e redes.

**Capacidades Críticas**:
- Comunicação com Docker daemon via socket Unix (`/var/run/docker.sock`) ou TCP
- Operações síncronas e assíncronas em containers
- Stream de logs em tempo real
- Gerenciamento de eventos Docker
- Inspeção detalhada de estado de containers

**Por que é essencial**:
- **Controle fino**: Diferente de `subprocess` chamando `docker` CLI, a API nativa oferece controle granular e retornos estruturados
- **Atomicidade**: Operações podem ser encadeadas com tratamento de erro preciso
- **Performance**: Comunicação direta com daemon, sem overhead de spawnar processos
- **Dados estruturados**: Respostas em formato Python (dicts, objetos), não parsing de texto

**Alternativas consideradas e descartadas**:
- `subprocess + docker CLI`: Parsing de texto frágil, difícil tratamento de erros
- `sh` library: Abstração desnecessária sobre subprocess, mesmos problemas

---

### 2. **requests** ou **httpx**

**Instalação**: `pip install requests` ou `pip install httpx`

**Propósito**: Cliente HTTP robusto para verificar healthchecks de aplicações, APIs REST e endpoints de monitoramento.

**Capacidades Críticas**:
- Requisições HTTP/HTTPS com retry automático configurável
- Timeout granular (connect, read)
- SSL/TLS verification
- Session management para reutilizar conexões
- Tratamento de redirects e cookies

**Por que é essencial para N8N**:
- **Verificar N8N operacional**: Após iniciar container, consultar `http://localhost:5678/healthz` ou `/rest/workflows`
- **Healthcheck inteligente**: Não basta container "running", precisa verificar se N8N responde
- **Timeout configurável**: Evitar bloqueio infinito se N8N travou
- **Retry logic**: Tentativas com backoff exponencial durante startup

**httpx vs requests**:
- **requests**: Biblioteca madura, amplamente usada, síncrona
- **httpx**: Suporta async/await, HTTP/2, API moderna, melhor para aplicações assíncronas
- **Recomendação**: `requests` para simplicidade inicial, `httpx` se precisar operações assíncronas

---

### 3. **pathlib** (stdlib)

**Instalação**: Nativa (Python 3.4+)

**Propósito**: Manipulação orientada a objetos de caminhos de sistema de arquivos, substituindo `os.path`.

**Capacidades Críticas**:
- Operações de caminho cross-platform (Linux, Windows, macOS)
- Verificação de existência, permissões, tipo (arquivo/diretório)
- Criação de diretórios com `mkdir(parents=True, exist_ok=True)`
- Iteração de arquivos com `glob()` e `rglob()`
- Leitura/escrita de arquivos com métodos integrados

**Por que é essencial**:
- **Segurança**: `Path.resolve()` normaliza caminhos, evita directory traversal attacks
- **Legibilidade**: `backup_dir / "credentials" / "file.json"` vs concatenação de strings
- **Type safety**: Objetos `Path` são tipados, IDEs detectam erros
- **Cross-platform**: Funciona em Linux (produção) e Windows (dev) sem mudanças

**Exemplo de uso crítico**:
- Verificar `/tmp/bkpfile` existe antes de montar volume
- Validar arquivos JSON baixados do repositório
- Criar estrutura de diretórios com timestamp `YYYYMMDD-HHMMSS-{server}-n8n-*`

---

### 4. **subprocess** (stdlib)

**Instalação**: Nativa

**Propósito**: Executar comandos externos quando necessário (exemplo: `rsync`, `tar`, `rclone`).

**Capacidades Críticas**:
- Executar processos com controle de stdin/stdout/stderr
- Timeout para evitar processos travados
- Captura de exit codes e tratamento de erros
- Streams de output em tempo real
- Environment variables isoladas por processo

**Por que ainda é necessário**:
- **Ferramentas externas**: Algumas operações são melhores com tools nativos (rsync, tar)
- **Compatibilidade**: Scripts legados podem precisar ser chamados
- **Performance**: `rsync` otimizado em C é mais rápido que implementação Python pura

**Cuidados de segurança**:
- **NUNCA** usar `shell=True` com input do usuário (shell injection)
- Sempre usar lista de argumentos: `["rsync", "-avz", source, dest]`
- Validar paths antes de passar para comandos externos
- Capturar e logar stderr para auditoria

---

## Integração Docker

### 5. **docker.models.containers.Container**

**Propósito**: Objeto Python representando um container Docker com métodos para controle de ciclo de vida.

**Métodos Críticos**:

#### **`container.stop(timeout=10)`**
- **Comportamento**: Envia SIGTERM para processo principal, aguarda `timeout` segundos, então envia SIGKILL se necessário
- **Retorno**: None (síncrono, bloqueia até parada)
- **Exceções**: `docker.errors.APIError` se falha na comunicação com daemon
- **Uso crítico**: Parar N8N gracefully antes de restore, permitindo finalização de workflows em execução

#### **`container.start()`**
- **Comportamento**: Inicia container previamente parado (não cria novo)
- **Retorno**: None (síncrono)
- **Exceções**: `docker.errors.APIError` se container não existe ou já está running
- **Uso crítico**: Reiniciar N8N após backup/restore completados

#### **`container.restart(timeout=10)`**
- **Comportamento**: Equivalente a `stop()` + `start()`, mas atômico
- **Vantagem**: Operação única, menor janela de inconsistência
- **Uso crítico**: Aplicar mudanças de configuração que requerem reinício

#### **`container.wait(timeout=None, condition='not-running')`**
- **Comportamento**: Bloqueia até container atingir condição especificada
- **Conditions**: `'not-running'`, `'next-exit'`, `'removed'`
- **Retorno**: Dict com `StatusCode` e `Error` (se houver)
- **Uso crítico**: Garantir parada completa antes de executar backup

#### **`container.reload()`**
- **Comportamento**: Atualiza atributos do objeto com estado atual do container no daemon
- **Por que necessário**: Estado em memória pode ficar desatualizado se outro processo modificar container
- **Uso crítico**: Sempre chamar antes de verificar `container.status` após operações

#### **`container.logs(timestamps=True, tail='all')`**
- **Comportamento**: Retorna logs do container
- **Retorno**: Generator (stream) ou string completa
- **Parâmetros úteis**: `since`, `until`, `follow` (stream contínuo)
- **Uso crítico**: Capturar logs de erro durante falhas de backup/restore

---

### 6. **docker.client.DockerClient**

**Propósito**: Cliente principal para interagir com Docker daemon.

**Inicialização**:
- `docker.from_env()`: Usa variáveis de ambiente (DOCKER_HOST, DOCKER_TLS_VERIFY, etc.)
- `docker.DockerClient(base_url='unix://var/run/docker.sock')`: Configuração explícita

**Métodos Críticos**:

#### **`client.containers.get(container_id_or_name)`**
- **Comportamento**: Retorna objeto `Container` pelo ID ou nome
- **Exceções**: `docker.errors.NotFound` se não existe
- **Uso crítico**: Buscar container N8N no início da operação

#### **`client.containers.list(filters={'name': 'n8n'})`**
- **Comportamento**: Lista containers com filtros
- **Filters úteis**: `{'status': 'running'}`, `{'label': 'app=n8n'}`
- **Uso crítico**: Descobrir containers N8N dinamicamente se nome pode variar

#### **`client.containers.run(image, command, volumes, detach=True, remove=True)`**
- **Comportamento**: Cria e inicia novo container (usado para `docker run --rm`)
- **Parâmetros críticos**:
  - `volumes`: Dict mapeando host:container paths
  - `volumes_from`: Lista de container IDs para `--volumes-from`
  - `remove=True`: Equivalente a `--rm`
  - `detach=True`: Retorna imediatamente, não espera término
- **Uso crítico**: Executar comandos `n8n export/import` em container temporário

#### **`client.api.inspect_container(container_id)`**
- **Comportamento**: Retorna JSON completo com TODOS os detalhes do container
- **Informações incluídas**: Config, State, NetworkSettings, Mounts, HostConfig
- **Uso crítico**: Verificar volumes montados, environment variables, health status detalhado

---

### 7. **docker.errors** (Módulo de Exceções)

**Exceções Críticas**:

#### **`docker.errors.NotFound`**
- **Quando ocorre**: Container, imagem ou volume não existe
- **Tratamento**: Verificar pré-requisitos, criar recursos faltantes, ou abortar com mensagem clara

#### **`docker.errors.APIError`**
- **Quando ocorre**: Erro na comunicação com Docker daemon ou operação rejeitada
- **Atributos úteis**: `response.status_code`, `explanation`
- **Tratamento**: Logar detalhes, verificar permissões do daemon, validar estado do sistema

#### **`docker.errors.ContainerError`**
- **Quando ocorre**: Container encerrou com exit code diferente de 0
- **Atributos úteis**: `exit_status`, `stderr`, `image`, `command`
- **Tratamento**: Extrair stderr, logar comando que falhou, possível retry se transiente

#### **`docker.errors.ImageNotFound`**
- **Quando ocorre**: Tentar rodar container com imagem não baixada
- **Tratamento**: Pull automático da imagem ou abortar com instruções para pull manual

**Estratégia de tratamento**:
- Sempre capturar exceções específicas antes de genéricas
- Logar stack trace completo para debugging
- Retornar códigos de erro específicos para diferentes falhas
- Implementar retry logic para erros transientes (timeout de rede, daemon ocupado)

---

## Gerenciamento de Estado de Container

### Estados do Docker Container

**Estados possíveis** (atributo `container.status`):
- `'created'`: Container criado mas nunca iniciado
- `'running'`: Processo principal em execução
- `'paused'`: Execução congelada (via `docker pause`)
- `'restarting'`: Em processo de restart automático
- `'removing'`: Sendo removido
- `'exited'`: Parado (processo encerrou)
- `'dead'`: Falha irrecuperável (OOM, erro de driver)

### Verificação de Parada Completa

**Desafio**: `container.stop()` retorna antes do container estar completamente parado em alguns casos (processos filhos, cleanup de volumes).

**Solução robusta**:
1. Chamar `container.stop(timeout=30)`
2. Aguardar com `container.wait(condition='not-running', timeout=60)`
3. Fazer polling de `container.status` com `reload()` até confirmar `'exited'`
4. Verificar exit code no retorno de `wait()` - se != 0, processo encerrou anormalmente

**Por que múltiplas verificações**:
- **Race condition**: Status pode estar desatualizado se não chamar `reload()`
- **Graceful shutdown**: N8N pode ter workflows longos que atrasam shutdown
- **Processos zumbis**: Containers podem ficar em estado intermediário se daemon travou

### Verificação de Integridade do Container

**Aspectos a verificar ANTES de operação**:

#### **1. Container existe**
- Método: `client.containers.get(name)` não lança `NotFound`
- Motivo: Evitar criar operações em container inexistente

#### **2. Volumes montados estão acessíveis**
- Método: `container.attrs['Mounts']` contém volumes esperados
- Verificar: `/home/node/.n8n` (dados N8N), `/tmp/bkpfile:/backup` (backups)
- Motivo: Sem volumes, backup não exporta/importa dados corretos

#### **3. Environment variables críticas presentes**
- Método: `container.attrs['Config']['Env']` contém `N8N_ENCRYPTION_KEY`
- Motivo: Sem chave, export/import falha silenciosamente ou gera arquivos inutilizáveis

#### **4. Estado de health (se configurado)**
- Método: `container.attrs['State']['Health']['Status']`
- Estados: `'healthy'`, `'unhealthy'`, `'starting'`, `null` (sem healthcheck)
- Motivo: Container "running" mas unhealthy indica N8N travado

#### **5. Exit code do último encerramento** (se reiniciado)
- Método: `container.attrs['State']['ExitCode']`
- Valores: `0` = encerramento normal, `137` = SIGKILL (OOM?), `143` = SIGTERM
- Motivo: Exit code anormal indica problema subjacente

#### **6. OOMKilled flag**
- Método: `container.attrs['State']['OOMKilled']`
- Motivo: Se `True`, container foi morto por falta de memória - reiniciar sem correção causará nova falha

### Inicialização e Verificação de Startup

**Processo robusto**:

#### **Fase 1: Start básico**
1. `container.start()`
2. Aguardar 2-3 segundos (tempo mínimo de boot do processo)

#### **Fase 2: Verificação de estado running**
1. `container.reload()` para atualizar status
2. Verificar `container.status == 'running'`
3. Se `'exited'` ou `'dead'`, capturar logs e abortar

#### **Fase 3: Polling de logs para indicadores de startup**
1. Stream de logs com `container.logs(stream=True, follow=True)`
2. Buscar padrões: "Server started", "Listening on port 5678", "Initialization complete"
3. Timeout: 60 segundos (configurável)
4. Se timeout ou erro nos logs, abortar

#### **Fase 4: Healthcheck de aplicação** (mais crítico)
1. Usar `requests` para consultar endpoint N8N
2. Tentar `http://localhost:5678/healthz` (se disponível) ou `/rest/workflows`
3. Retry com backoff exponencial: 1s, 2s, 4s, 8s, 16s (total ~31s)
4. Verificar `status_code == 200` E conteúdo da resposta válido
5. **Importante**: Container "running" ≠ N8N operacional (pode estar em crash loop)

#### **Fase 5: Verificação funcional básica** (opcional mas recomendado)
1. Fazer query simples na API REST: `GET /rest/credentials?limit=1`
2. Verificar que retorna JSON válido (mesmo que vazio)
3. Confirma que banco de dados está acessível e schema OK

**Por que tantas fases**:
- **Container running**: Processo `node` iniciou
- **Logs de startup**: N8N passou fase de inicialização
- **Healthcheck HTTP**: Servidor web está respondendo
- **Verificação funcional**: Banco de dados e core logic operacionais

---

## Verificação de Integridade e Healthchecks

### 8. **requests com Retry Logic**

**Biblioteca adicional recomendada**: `pip install urllib3` (já vem com requests)

**Estratégia de Healthcheck Robusto**:

#### **Timeout Granular**
- **Connect timeout**: 5s (tempo para estabelecer conexão TCP)
- **Read timeout**: 15s (tempo para receber resposta completa)
- **Motivo**: N8N pode estar slow mas funcional (workflows pesados) - não queremos falso negativo

#### **Retry com Backoff Exponencial**
- **Backoff**: `[1, 2, 4, 8, 16]` segundos entre tentativas
- **Total tentativas**: 5 (total ~31s esperando)
- **Status codes para retry**: `502`, `503`, `504` (server temporariamente indisponível)
- **Não fazer retry em**: `404`, `401`, `500` (erros permanentes ou de configuração)

#### **Validação de Resposta**
- Não basta `status_code == 200`
- Validar `Content-Type: application/json`
- Parsear JSON e verificar estrutura esperada
- **Exemplo**: `/rest/workflows` deve retornar `{"data": [...], "nextCursor": null}`

#### **Circuit Breaker Pattern** (avançado)
- Após N falhas consecutivas (ex: 3), entrar em "open state"
- Em "open", falhar imediatamente sem tentar requisição (evitar latência)
- Após timeout (ex: 60s), tentar uma requisição de teste ("half-open")
- Se sucesso, voltar a "closed" (operação normal)
- **Biblioteca recomendada**: `pybreaker` (`pip install pybreaker`)

### Endpoints N8N Críticos para Healthcheck

#### **`/healthz`** (se disponível em versão 2.3.0+)
- **Propósito**: Endpoint dedicado de health
- **Resposta**: `{"status": "ok"}` ou similar
- **Vantagem**: Lightweight, não consulta banco
- **Desvantagem**: Pode não existir em todas as versões

#### **`/rest/workflows?limit=1`**
- **Propósito**: Consulta mínima ao banco de dados
- **Resposta**: JSON com array `data` (mesmo vazio)
- **Vantagem**: Confirma banco operacional
- **Desvantagem**: Requer autenticação em alguns setups

#### **`/rest/active`**
- **Propósito**: Lista workflows ativos
- **Vantagem**: Valida que engine de execução está OK
- **Desvantagem**: Mais pesado que `/healthz`

**Recomendação de estratégia**:
1. Tentar `/healthz` primeiro (rápido)
2. Se 404, fallback para `/rest/workflows?limit=1`
3. Se ambos falham, considerar N8N unhealthy

### Verificação de Porta Listening

**Biblioteca**: `socket` (stdlib)

**Por que é útil**:
- Confirmar que porta 5678 está em LISTEN antes de fazer requisição HTTP
- Evitar timeout longo se N8N nem iniciou servidor web ainda
- Mais rápido que requisição HTTP completa

**Limitações**:
- Porta aberta ≠ N8N operacional (pode ser nginx proxy, ou N8N travado após bind)
- Deve ser combinada com healthcheck HTTP, não substituída

---

## Segurança e Gestão de Credenciais

### 9. **python-dotenv**

**Instalação**: `pip install python-dotenv`

**Propósito**: Carregar variáveis de ambiente de arquivo `.env` de forma segura, sem hardcode no código.

**Capacidades**:
- Carregar `.env` do diretório do script ou path customizado
- Não sobrescreve variáveis já definidas no sistema (seguro)
- Suporta comentários e multiline values
- Interpolação de variáveis dentro do `.env`

**Uso crítico para N8N**:
- Armazenar `N8N_ENCRYPTION_KEY` em `.env` (NÃO committado no Git)
- Configurações sensíveis: credenciais AWS, tokens de repositório, etc.
- Diferentes `.env` por ambiente: `.env.production`, `.env.staging`

**Estrutura de `.env` recomendada**:
```
# N8N Configuration
N8N_ENCRYPTION_KEY=sua-chave-super-secreta-32-chars
N8N_CONTAINER_NAME=n8n-container
N8N_DOCKER_IMAGE=n8nio/n8n:latest

# Backup Configuration
BACKUP_BASE_PATH=/tmp/bkpfile
BACKUP_RETENTION_DAYS=7
SERVER_NAME=prod-server-01

# Repository Configuration (escolher um)
AWS_S3_BUCKET=empresa-backups-n8n
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/n8n-backup.log
```

**Segurança do `.env`**:
- Adicionar ao `.gitignore`
- Permissões: `chmod 600 .env` (somente owner pode ler/escrever)
- Nunca logar conteúdo de variáveis sensíveis
- Usar `.env.example` com placeholders para documentação

### 10. **hvac** (HashiCorp Vault Client)

**Instalação**: `pip install hvac`

**Propósito**: Integração oficial com HashiCorp Vault para gestão enterprise de secrets.

**Por que é essencial em produção**:
- `.env` é OK para dev/staging, mas produção precisa de rotação de secrets
- Vault oferece auditoria completa de acessos
- Secrets são criptografados em rest e transit
- TTL (Time To Live) automático para secrets temporários

**Fluxo de uso**:
1. Autenticar no Vault (AppRole, Kubernetes, AWS IAM, etc.)
2. Ler secret: `client.secrets.kv.v2.read_secret_version(path='n8n/encryption-key')`
3. Secret retornado como dict Python
4. Secret pode ter metadata (versão, created_time, etc.)

**Fallback hierarchy recomendado**:
1. Tentar Vault primeiro (produção)
2. Se Vault indisponível, fallback para `.env` (staging)
3. Se `.env` não existe, fallback para variável de ambiente do sistema
4. Se nenhum funcionar, abortar com erro claro

**Rotação de secrets**:
- Vault permite versionar secrets (v1, v2, v3...)
- Script pode buscar versão específica ou latest
- Facilita rotação sem downtime (novo backup usa v2, old ainda pode restaurar com v1)

### 11. **cryptography**

**Instalação**: `pip install cryptography`

**Propósito**: Biblioteca de criptografia robusta e auditada para operações avançadas.

**Quando é necessária**:
- N8N já faz criptografia com `N8N_ENCRYPTION_KEY`, então não precisa re-criptografar
- **MAS**: útil para criptografar logs sensíveis antes de enviar para repositório
- Validar formato de dados criptografados sem descriptografar
- Gerar checksums (SHA256) para verificar integridade de backups

**Operações críticas**:

#### **Hash de verificação de integridade**
- Calcular SHA256 de arquivo de backup
- Armazenar hash em arquivo separado `.sha256`
- Antes de restore, recalcular hash e comparar
- Detecta corrupção durante transferência de rede ou storage

#### **Criptografia de logs**
- Logs podem conter trechos de credenciais em mensagens de erro
- Criptografar logs antes de upload para S3 public bucket
- Descriptografar somente quando necessário para debugging

#### **Validação de formato AES-256-CBC** (usado pelo N8N)
- Verificar que `data` field em credenciais segue formato base64(iv + ciphertext)
- Não descriptografa, mas valida estrutura
- Detecta backups corrompidos antes de tentar import

---

## Logging e Auditoria

### 12. **logging** (stdlib) com configuração estruturada

**Propósito**: Sistema nativo de logging do Python, altamente configurável.

**Componentes críticos**:

#### **Loggers hierárquicos**
- Logger raiz: `logging.getLogger()`
- Loggers específicos: `logging.getLogger('n8n.backup')`, `logging.getLogger('n8n.restore')`
- Hierarquia permite controle granular de níveis

#### **Handlers (destinos de log)**
- `FileHandler`: Escrever em arquivo `/var/log/n8n-backup.log`
- `RotatingFileHandler`: Rotacionar logs por tamanho (ex: max 10MB, keep 5 backups)
- `TimedRotatingFileHandler`: Rotacionar por tempo (diário, semanal)
- `StreamHandler`: Output para stdout/stderr (útil em containers)
- `SysLogHandler`: Enviar para syslog do sistema (integração com logrotate)

#### **Formatters (estrutura da mensagem)**
- Simples: `'%(asctime)s - %(levelname)s - %(message)s'`
- Completo: `'%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'`
- JSON estruturado (requer biblioteca adicional):
  ```
  {
    "timestamp": "2026-01-20T14:30:00Z",
    "level": "ERROR",
    "logger": "n8n.backup",
    "message": "Falha ao exportar credenciais",
    "context": {
      "container_id": "abc123",
      "backup_path": "/tmp/bkpfile/20260120-143000"
    }
  }
  ```

#### **Níveis de log**
- `DEBUG` (10): Informação detalhada para debugging (ex: cada arquivo exportado)
- `INFO` (20): Confirmação que operações funcionam como esperado (ex: backup iniciado/concluído)
- `WARNING` (30): Algo inesperado mas recuperável (ex: retry após timeout)
- `ERROR` (40): Erro grave que impediu operação (ex: container não encontrado)
- `CRITICAL` (50): Erro catastrófico que pode derrubar sistema (ex: disco cheio)

**Configuração recomendada para produção**:
- **Console (stdout)**: `INFO` (para monitoramento em tempo real via Docker logs)
- **Arquivo**: `DEBUG` (para investigação post-mortem)
- **Syslog**: `WARNING+` (para alertas de monitoramento)

### 13. **python-json-logger** (opcional)

**Instalação**: `pip install python-json-logger`

**Propósito**: Formatter que converte logs em JSON estruturado, ideal para ferramentas de análise (ELK, Splunk, CloudWatch).

**Vantagens de JSON logs**:
- **Parseável**: Ferramentas podem filtrar/agregar sem regex complexo
- **Campos customizados**: Adicionar `container_id`, `backup_id`, `user` automaticamente
- **Integração cloud**: AWS CloudWatch Insights, Azure Log Analytics processam JSON nativamente

**Desvantagens**:
- Menos legível para humanos (usar JSON somente em produção)
- Requer ferramenta para visualizar (jq, online JSON viewers)

### Auditoria Completa

**O que logar para auditoria**:

#### **Início de operação**
- Timestamp, usuário/processo que iniciou, tipo de operação (backup/restore)
- Parâmetros: container name, backup path, flags usadas

#### **Mudanças de estado**
- Container parado: timestamp, graceful vs forceful (SIGTERM vs SIGKILL)
- Container iniciado: timestamp, exit code da parada anterior

#### **Operações de dados**
- Arquivos criados: path completo, tamanho, checksum SHA256
- Arquivos lidos: path, se validação passou (JSON válido, não-vazio)
- Uploads para repositório: destination URL, tamanho transferido, duração

#### **Erros e exceções**
- Stack trace completo (usar `logger.exception()` que captura automaticamente)
- Contexto: estado do sistema no momento do erro
- Tentativas de recovery e resultado

#### **Resultado final**
- Sucesso/falha, duração total, recursos consumidos (CPU, RAM, disk I/O se disponível)
- Para restore: número de credenciais/workflows restaurados

**Retenção de logs**:
- Logs operacionais: 30 dias (logs diários)
- Logs de auditoria: 1 ano mínimo (compliance)
- Logs de erro: indefinido (ou até investigação completa)

---

## Manipulação de Dados e Validação

### 14. **json** (stdlib)

**Propósito**: Parser JSON nativo, rápido e confiável.

**Operações críticas**:

#### **Validação de backup após export**
- `json.load(file)` em cada arquivo exportado
- Se lança `json.JSONDecodeError`, arquivo está corrompido
- Verificar estrutura esperada: `{'id': str, 'name': str, 'data': str}`

#### **Inspeção de dados sem modificação**
- Abrir backup, contar número de credenciais/workflows
- Extrair metadados (created_at, updated_at) para relatório
- Comparar IDs antes e depois de restore

**Cuidados**:
- `json.load()` carrega arquivo inteiro em memória - OK para backups individuais (~KB), mas cuidado com consolidados grandes (>100MB)
- Usar `json.load(fp, object_hook=...)` para validação customizada durante parsing

### 15. **pydantic** ou **marshmallow**

**Instalação**: `pip install pydantic` ou `pip install marshmallow`

**Propósito**: Validação de schema de dados com type checking em runtime.

**Por que é importante**:
- JSON pode estar sintaticamente válido mas semanticamente errado
- Exemplo: `id` pode estar presente mas ser string vazia (inválido)
- Schema muda entre versões N8N - validação detecta incompatibilidades

**pydantic - Recomendado para Python 3.7+**:
- Usa type hints nativos do Python
- Validação automática em atribuição
- Serialização/deserialização JSON integrada
- Performance excelente (usa Rust internamente em v2)

**Exemplo de schema para credencial**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class N8NCredential(BaseModel):
    id: str = Field(..., min_length=1, description="UUID da credencial")
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., regex=r'^[a-zA-Z0-9]+$')  # Ex: 'googleSheetsOAuth2Api'
    data: str = Field(..., min_length=1)  # Base64 encrypted data
    createdAt: datetime
    updatedAt: datetime
    
    @validator('data')
    def validate_base64(cls, v):
        import base64
        try:
            base64.b64decode(v)
        except Exception:
            raise ValueError('data deve ser base64 válido')
        return v
    
    @validator('createdAt', 'updatedAt')
    def validate_dates(cls, v):
        if v > datetime.now():
            raise ValueError('Data não pode estar no futuro')
        return v
```

**Uso**:
```python
# Carregar e validar backup
with open('credential.json') as f:
    data = json.load(f)
    credential = N8NCredential(**data)  # Lança ValidationError se inválido
```

**Benefícios em produção**:
- Detecta backups corrompidos ANTES de tentar import
- Valida dados baixados de repositório remoto (proteção contra tampering)
- Documenta estrutura esperada (schema é documentação viva)

---

## Integração com Repositórios de Backup

### 16. **boto3** (AWS S3)

**Instalação**: `pip install boto3`

**Propósito**: SDK oficial da AWS para Python, controle completo de serviços AWS.

**Operações críticas para backup**:

#### **Upload de arquivo com Server-Side Encryption**
```python
import boto3
s3 = boto3.client('s3')

s3.upload_file(
    Filename='/tmp/bkpfile/20260120-140000-prod-n8n-credentials.tar.gz',
    Bucket='empresa-backups',
    Key='n8n/20260120-140000-prod-n8n-credentials.tar.gz',
    ExtraArgs={
        'ServerSideEncryption': 'aws:kms',  # Criptografia gerenciada pela AWS
        'SSEKMSKeyId': 'arn:aws:kms:us-east-1:123456789012:key/abc-def',
        'StorageClass': 'STANDARD_IA',  # Infrequent Access (mais barato)
        'Metadata': {
            'backup-date': '2026-01-20',
            'server': 'prod-server-01',
            'n8n-version': '2.3.0'
        }
    }
)
```

#### **Download de backup para restore**
```python
s3.download_file(
    Bucket='empresa-backups',
    Key='n8n/20260120-140000-prod-n8n-credentials.tar.gz',
    Filename='/tmp/bkpfile/downloaded-backup.tar.gz'
)
```

#### **Listagem de backups disponíveis**
```python
response = s3.list_objects_v2(
    Bucket='empresa-backups',
    Prefix='n8n/',
    MaxKeys=100
)

backups = [obj['Key'] for obj in response.get('Contents', [])]
# ['n8n/20260120-140000-...', 'n8n/20260119-140000-...', ...]
```

#### **Rotação automática (Lifecycle Policy)**
```python
# Definir regra de lifecycle via boto3 (fazer uma vez, fica permanente)
s3.put_bucket_lifecycle_configuration(
    Bucket='empresa-backups',
    LifecycleConfiguration={
        'Rules': [
            {
                'Id': 'DeleteOldN8NBackups',
                'Status': 'Enabled',
                'Prefix': 'n8n/',
                'Expiration': {'Days': 30},  # Deletar após 30 dias
                'Transitions': [
                    {
                        'Days': 7,
                        'StorageClass': 'GLACIER'  # Mover para Glacier após 7 dias (muito mais barato)
                    }
                ]
            }
        ]
    }
)
```

**Vantagens sobre aws-cli**:
- Controle programático: pode fazer retry, validação, etc.
- Progress callback para uploads grandes
- Multipart upload automático para arquivos >5GB
- Melhor tratamento de erros (exceções tipadas)

### 17. **azure-storage-blob** (Azure Blob Storage)

**Instalação**: `pip install azure-storage-blob`

**Propósito**: SDK oficial da Azure para blob storage.

**Operações similares a S3**:
```python
from azure.storage.blob import BlobServiceClient, ContainerClient

blob_service = BlobServiceClient.from_connection_string(
    "DefaultEndpointsProtocol=https;AccountName=empresabackups;AccountKey=..."
)

container = blob_service.get_container_client("n8n-backups")

# Upload
with open('/tmp/bkpfile/backup.tar.gz', 'rb') as data:
    container.upload_blob(
        name='20260120-140000-prod-n8n-credentials.tar.gz',
        data=data,
        metadata={'server': 'prod-01', 'date': '2026-01-20'}
    )

# Download
with open('/tmp/downloaded.tar.gz', 'wb') as file:
    blob_client = container.get_blob_client('20260120-140000-...')
    file.write(blob_client.download_blob().readall())
```

### 18. **Integração com rsync via subprocess**

**Por que rsync ainda é relevante**:
- Transferência incremental (só envia diff, não arquivo completo)
- Compressão on-the-fly
- Retomada de transferências interrompidas
- Amplamente disponível em Linux

**Execução segura**:
```python
import subprocess
from pathlib import Path

def rsync_backup(source: Path, destination: str):
    """
    Args:
        source: Path local (/tmp/bkpfile/20260120-140000-*)
        destination: Remote path (backup-server:/backups/n8n/)
    """
    cmd = [
        'rsync',
        '-avz',  # archive, verbose, compress
        '--progress',
        '--timeout=300',  # Timeout se rede travar
        str(source),
        destination
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,  # Lança CalledProcessError se exit code != 0
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos max
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        # Logar stderr para debugging
        logger.error(f"rsync falhou: {e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logger.error("rsync timeout após 10 minutos")
        raise
```

**Validação SSH antes de rsync**:
- Testar conexão: `ssh -o BatchMode=yes -o ConnectTimeout=5 backup-server echo OK`
- Se falhar, não tentar rsync (vai travar aguardando senha)

---

## Tratamento de Erros e Recovery

### 19. **tenacity** (Retry com Backoff)

**Instalação**: `pip install tenacity`

**Propósito**: Biblioteca para retry automático de operações com lógica configurável de backoff, stop e exceções.

**Por que é crítico**:
- Erros transientes são comuns: timeout de rede, Docker daemon temporariamente ocupado, S3 throttling
- Retry manual com loops é verboso e propenso a bugs
- tenacity oferece controle declarativo e logging integrado

**Exemplo: Retry em healthcheck**:
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import requests

@retry(
    stop=stop_after_attempt(5),  # Máximo 5 tentativas
    wait=wait_exponential(multiplier=1, min=1, max=16),  # 1s, 2s, 4s, 8s, 16s
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError))
)
def check_n8n_healthy(url: str) -> bool:
    """Verifica se N8N está respondendo, com retry automático"""
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Lança HTTPError se 4xx/5xx
    data = response.json()
    # Validar estrutura da resposta
    assert 'data' in data or 'status' in data
    return True
```

**Estratégias de retry**:

#### **Stop conditions (quando parar)**:
- `stop_after_attempt(n)`: Após N tentativas
- `stop_after_delay(seconds)`: Após X segundos totais
- Combinação: `stop=(stop_after_attempt(5) | stop_after_delay(60))`

#### **Wait strategies (quanto aguardar entre tentativas)**:
- `wait_fixed(seconds)`: Intervalo fixo
- `wait_exponential()`: Backoff exponencial (1, 2, 4, 8, 16...)
- `wait_random(min, max)`: Intervalo aleatório (evita thundering herd)
- `wait_exponential_jitter()`: Exponencial + jitter (recomendado)

#### **Retry conditions (quando tentar novamente)**:
- `retry_if_exception_type(Exception)`: Somente para exceções específicas
- `retry_if_result(lambda x: x is None)`: Se resultado não é o esperado
- Combinação: `retry=(retry_if_exception_type(Timeout) | retry_if_result(lambda x: x.status == 'starting'))`

**Logging de retries**:
```python
import logging

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    before=lambda retry_state: logger.info(f"Tentativa {retry_state.attempt_number}..."),
    after=lambda retry_state: logger.info(f"Resultado: {retry_state.outcome}")
)
def operacao_com_retry():
    pass
```

### Recovery Strategies

**Cenário 1: Falha durante backup após container parado**
1. Capturar exceção
2. Logar erro completo (stack trace, contexto)
3. **Recovery**: Reiniciar container IMEDIATAMENTE
4. Notificar equipe (email, Slack, PagerDuty)
5. **NÃO** tentar re-executar backup automaticamente (pode ter problema persistente)

**Cenário 2: Falha durante restore (import falhou)**
1. **CRÍTICO**: Container está parado e estado inconsistente
2. **Recovery**: Importar backup de segurança (feito antes do restore)
3. Se backup de segurança também falha: restaurar snapshot de VM/container inteiro (disaster recovery)
4. Logar incidente como CRITICAL
5. Investigação manual obrigatória antes de nova tentativa

**Cenário 3: Upload para repositório falhou (backup local OK)**
1. Manter backup local (NÃO deletar)
2. Retry upload após intervalo (1 hora)
3. Se falha persiste: alertar equipe, backup local é temporário
4. Após sucesso de upload futuro, verificar se backup antigo ainda está local e fazer upload tardio

**Cenário 4: Download de backup para restore falhou**
1. Verificar conectividade de rede
2. Listar backups disponíveis no repositório (garantir que existe)
3. Retry download com backoff
4. Se persiste: tentar download de backup alternativo (dia anterior)
5. **NÃO** prosseguir com restore sem backup válido

**Princípios de recovery**:
- **Fail-safe**: Em caso de dúvida, deixar sistema no estado anterior (não piorar)
- **Idempotência**: Operação pode ser repetida sem efeito colateral
- **Auditoria**: Toda tentativa de recovery é logada
- **Alertas graduais**: WARNING para retry bem-sucedido, ERROR para falha após retries, CRITICAL para falha de recovery

---

## Testes e Qualidade

### 20. **pytest**

**Instalação**: `pip install pytest`

**Propósito**: Framework de testes mais popular em Python, sintaxe simples e recursos avançados.

**Tipos de teste essenciais**:

#### **Testes Unitários** (funções isoladas)
- Testar parsing de JSON
- Validação de schemas com pydantic
- Formatação de timestamps
- Construção de comandos Docker

#### **Testes de Integração** (com Docker)
- Iniciar container de teste, fazer backup, verificar arquivos gerados
- Importar backup em container limpo, verificar credenciais restauradas
- Simular falhas (kill container durante backup) e verificar recovery

#### **Fixtures** (setup/teardown de ambiente)
```python
import pytest
import docker

@pytest.fixture(scope='session')
def docker_client():
    """Cliente Docker compartilhado entre testes"""
    client = docker.from_env()
    yield client
    client.close()

@pytest.fixture
def n8n_container(docker_client):
    """Container N8N temporário para testes"""
    container = docker_client.containers.run(
        image='n8nio/n8n:latest',
        detach=True,
        remove=True,  # Auto-remove após teste
        environment={'N8N_ENCRYPTION_KEY': 'test-key-32-chars-minimum-here'},
        ports={'5678/tcp': None}  # Porta aleatória
    )
    
    # Aguardar startup
    import time
    time.sleep(10)
    
    yield container
    
    # Teardown
    container.stop()
```

#### **Mocking** (simular dependências externas)
```python
from unittest.mock import Mock, patch

@patch('boto3.client')
def test_upload_to_s3(mock_boto3):
    """Testa upload sem realmente chamar AWS"""
    mock_s3 = Mock()
    mock_boto3.return_value = mock_s3
    
    # Executar função que usa boto3
    upload_backup_to_s3('/tmp/backup.tar.gz', 'empresa-backups')
    
    # Verificar que upload_file foi chamado
    mock_s3.upload_file.assert_called_once()
```

**Cobertura de testes** (pytest-cov):
```bash
pip install pytest-cov
pytest --cov=n8n_backup --cov-report=html
```
- Gera relatório HTML mostrando linhas não cobertas
- Meta: >80% de cobertura em código crítico

### 21. **mypy** (Type Checking Estático)

**Instalação**: `pip install mypy`

**Propósito**: Analisa código Python e detecta erros de tipo antes da execução.

**Por que é importante**:
- Python é dinamicamente tipado - erros de tipo só aparecem em runtime
- mypy + type hints = detecção de erros em tempo de desenvolvimento
- IDEs usam type hints para autocomplete e refactoring

**Exemplo de erro detectado**:
```python
def stop_container(container_name: str) -> None:
    client = docker.from_env()
    container = client.containers.get(container_name)
    container.stop(timeout="30")  # ❌ mypy detecta: esperava int, recebeu str
```

**Configuração (mypy.ini)**:
```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True  # Forçar type hints em todas as funções

# Ignorar bibliotecas sem stubs (types)
[mypy-docker.*]
ignore_missing_imports = True
```

### 22. **black** (Formatação de Código)

**Instalação**: `pip install black`

**Propósito**: Formatter automático, opinionated, sem configuração.

**Por que é importante**:
- Consistência de código entre desenvolvedores
- Diffs menores em Git (sem mudanças de estilo)
- Zero debates sobre estilo (black decide)

**Uso**:
```bash
black n8n_backup/*.py
# Formata todos os arquivos Python automaticamente
```

---

## Configuração e Environment

### 23. **click** ou **argparse** (CLI)

**Instalação**: `pip install click` ou usar `argparse` (stdlib)

**Propósito**: Criar interface de linha de comando para scripts.

**click - Recomendado**:
- Sintaxe mais limpa que argparse
- Validação de tipos automática
- Help messages gerados automaticamente
- Suporte a subcomandos (como git: `git commit`, `git push`)

**Estrutura recomendada**:
```python
import click

@click.group()
def cli():
    """N8N Backup & Restore Tool"""
    pass

@cli.command()
@click.option('--container', default='n8n-container', help='Nome do container N8N')
@click.option('--output', required=True, help='Diretório de saída')
@click.option('--upload/--no-upload', default=True, help='Upload para repositório')
def backup(container, output, upload):
    """Executa backup de credenciais e workflows"""
    click.echo(f'Iniciando backup do container {container}...')
    # Lógica de backup

@cli.command()
@click.option('--container', default='n8n-container')
@click.option('--input', required=True, help='Diretório de backup')
@click.option('--backup-current/--no-backup-current', default=True)
def restore(container, input, backup_current):
    """Restaura credenciais e workflows"""
    click.echo(f'Restaurando backup de {input}...')
    # Lógica de restore

if __name__ == '__main__':
    cli()
```

**Uso**:
```bash
python n8n_backup.py backup --container n8n-prod --output /tmp/bkpfile
python n8n_backup.py restore --input /tmp/bkpfile/20260120-140000-prod-n8n --no-backup-current
python n8n_backup.py --help  # Mostra ajuda automática
```

### 24. **configparser** (Arquivos INI)

**Instalação**: Nativa (stdlib)

**Propósito**: Ler configurações de arquivos `.ini` (alternativa a `.env` para configurações não-sensíveis).

**Exemplo de config.ini**:
```ini
[n8n]
container_name = n8n-container
docker_image = n8nio/n8n:latest
healthcheck_url = http://localhost:5678/healthz

[backup]
base_path = /tmp/bkpfile
retention_days = 7
timestamp_format = %%Y%%m%%d-%%H%%M%%S

[repository]
type = s3  # s3, azure, rsync
s3_bucket = empresa-backups
s3_prefix = n8n/

[logging]
level = INFO
file = /var/log/n8n-backup.log
format = %%(asctime)s - %%(levelname)s - %%(message)s
```

**Leitura**:
```python
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

container_name = config.get('n8n', 'container_name')
retention_days = config.getint('backup', 'retention_days')
```

**Quando usar config.ini vs .env**:
- **config.ini**: Configurações não-sensíveis, pode commitar no Git
- **.env**: Secrets, credenciais, nunca commitar

---

## Gerenciamento de Ambiente Python

### 25. **uv** (Gerenciador Moderno de Ambientes e Pacotes)

**Instalação**: 
```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Via pip (se já tem Python)
pip install uv

# Via Homebrew (macOS)
brew install uv
```

**Propósito**: Ferramenta ultra-rápida desenvolvida em Rust pela Astral para gerenciar ambientes virtuais e pacotes Python, substituindo pip, virtualenv, poetry e pipenv com performance 10-100x superior.

**Por que é essencial para projetos enterprise**:

#### **Performance Excepcional**
- **10-100x mais rápido** que pip tradicional
- Resolução de dependências em paralelo (multi-threaded)
- Cache global compartilhado entre projetos
- Instalação de pacotes otimizada com HTTP/2
- Compilação de wheels em paralelo

**Benchmark comparativo**:
```
Instalação de 50 pacotes (django, pandas, numpy, etc.):
- pip: ~120 segundos
- poetry: ~90 segundos
- uv: ~8 segundos ⚡
```

#### **Reprodutibilidade Garantida**
- Lockfile automático (`uv.lock`) com hashes SHA256
- Resolução determinística de dependências
- Compatível com `requirements.txt` e `pyproject.toml`
- Evita "works on my machine" em ambientes enterprise

#### **Simplicidade e Compatibilidade**
- Drop-in replacement para pip: `uv pip install` funciona igual
- Não requer mudança de workflow existente
- Compatível com virtualenv padrão do Python
- Integração nativa com Docker

---

### **Comandos Essenciais do uv**

#### **Criar ambiente virtual**
```bash
# Criar venv com Python específico
uv venv .venv --python 3.11

# Criar com Python do sistema
uv venv .venv

# Ativar (igual virtualenv tradicional)
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

#### **Instalar dependências**
```bash
# Instalar de requirements.txt (compatível com pip)
uv pip install -r requirements.txt

# Instalar pacote individual
uv pip install docker requests pydantic

# Instalar com versão específica
uv pip install "docker>=7.0.0,<8.0.0"

# Sync exato de requirements.txt (remove pacotes não listados)
uv pip sync requirements.txt
```

#### **Gerar lockfile**
```bash
# Compilar requirements.txt com versões exatas e hashes
uv pip compile requirements.in -o requirements.txt

# Atualizar dependências respeitando constraints
uv pip compile requirements.in -o requirements.txt --upgrade
```

#### **Listar pacotes instalados**
```bash
# Equivalente a pip list
uv pip list

# Equivalente a pip freeze
uv pip freeze
```

---

### **Integração uv com Projeto N8N Backup**

#### **Estrutura de Dependências Recomendada**

**requirements.in** (dependências diretas, sem versões fixas):
```txt
# Core Docker
docker>=7.0.0

# HTTP e API
requests>=2.31.0
httpx>=0.25.0

# Segurança e Secrets
python-dotenv>=1.0.0
hvac>=2.1.0
cryptography>=41.0.0

# Validação e Dados
pydantic>=2.5.0

# Cloud/Storage
boto3>=1.34.0
azure-storage-blob>=12.19.0

# Retry e Resiliência
tenacity>=8.2.0

# CLI
click>=8.1.0

# Logging
python-json-logger>=2.0.0

# Dev/Test (separar em requirements-dev.in em produção)
pytest>=7.4.0
pytest-cov>=4.1.0
mypy>=1.7.0
black>=23.12.0
```

**Gerar requirements.txt com lockfile**:
```bash
# Gerar arquivo com versões exatas e hashes
uv pip compile requirements.in -o requirements.txt

# Conteúdo de requirements.txt (exemplo):
# docker==7.0.0 \
#     --hash=sha256:abc123...
# requests==2.31.0 \
#     --hash=sha256:def456...
# ...
```

**Instalar em ambiente de produção** (reproduzível):
```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip sync requirements.txt  # Instala EXATAMENTE o que está no lock
```

---

#### **Dockerfile Otimizado com uv**

```dockerfile
FROM python:3.11-slim

# Instalar uv (mais rápido que pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Criar usuário não-root
RUN useradd -m -u 1000 n8n-backup
WORKDIR /app

# Copiar apenas requirements primeiro (cache layer)
COPY requirements.txt .

# Criar venv e instalar dependências com uv (muito mais rápido)
RUN uv venv /app/.venv && \
    uv pip install --no-cache -r requirements.txt

# Ativar venv permanentemente
ENV PATH="/app/.venv/bin:$PATH"

# Copiar código da aplicação
COPY --chown=n8n-backup:n8n-backup . .

USER n8n-backup

# Verificar instalação
RUN python -c "import docker, requests, pydantic; print('Dependencies OK')"

CMD ["python", "src/main.py"]
```

**Vantagens desta abordagem**:
- Build time reduzido em 70-80% comparado a pip
- Layer caching eficiente (requirements muda menos que código)
- Imagem final menor (sem cache de pip)
- Reproduzível (lockfile garante mesmas versões)

---

#### **Scripts de Automação com uv**

**setup.sh** (Setup inicial do projeto):
```bash
#!/bin/bash
set -euo pipefail

echo "🔧 Configurando ambiente N8N Backup com uv..."

# Verificar se uv está instalado
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv não encontrado. Instalando..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Criar ambiente virtual com Python 3.11
echo "📦 Criando ambiente virtual..."
uv venv .venv --python 3.11

# Ativar ambiente
source .venv/bin/activate

# Instalar dependências
echo "📥 Instalando dependências (com uv - super rápido)..."
uv pip sync requirements.txt

# Verificar instalação
echo "✅ Verificando instalação..."
python -c "import docker, requests, pydantic, boto3; print('✓ Todas as dependências instaladas')"

# Copiar .env.example se não existe .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Arquivo .env criado. IMPORTANTE: Configure N8N_ENCRYPTION_KEY!"
fi

echo "✅ Setup completo! Ative o ambiente com: source .venv/bin/activate"
```

**update-deps.sh** (Atualizar dependências):
```bash
#!/bin/bash
set -euo pipefail

echo "🔄 Atualizando dependências..."

# Recompilar com versões mais recentes
uv pip compile requirements.in -o requirements.txt --upgrade

# Instalar novas versões
source .venv/bin/activate
uv pip sync requirements.txt

echo "✅ Dependências atualizadas e sincronizadas"
echo "📋 Revise o diff de requirements.txt antes de commitar"
```

---

### **uv vs pip vs poetry vs pipenv**

| Aspecto | uv ⚡ | pip | poetry | pipenv |
|---------|------|-----|--------|--------|
| **Performance** | 10-100x mais rápido | Base | 2-3x mais lento que pip | 2-3x mais lento que pip |
| **Resolução de dependências** | Paralela, Rust | Linear, Python | SAT solver | Pipfile.lock |
| **Lockfile** | `uv.lock` com hashes | Manual | `poetry.lock` | `Pipfile.lock` |
| **Compatibilidade** | 100% pip | Padrão | Requer pyproject.toml | Requer Pipfile |
| **Learning curve** | Mínima (comandos iguais pip) | Zero | Média | Média |
| **Adoção em produção** | Crescendo rápido | Universal | Alta em Python moderno | Menor que poetry |
| **Cache compartilhado** | ✅ Sim | ❌ Não | ✅ Sim | ❌ Não |
| **Maturidade** | Novo (2023+) | Muito maduro | Maduro | Maduro |

**Recomendação para N8N Enterprise Backup**:
- **Use uv**: Performance crítica em CI/CD e deploys frequentes
- **Mantenha compatibilidade pip**: `requirements.txt` funciona em ambos
- **Transição gradual**: Pode usar `uv pip` como drop-in replacement sem reescrever código

---

### **CI/CD com uv (GitHub Actions exemplo)**

```yaml
name: Test N8N Backup

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v1
        with:
          version: "latest"
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Create venv and install deps
        run: |
          uv venv
          source .venv/bin/activate
          uv pip sync requirements.txt
      
      - name: Run tests
        run: |
          source .venv/bin/activate
          pytest tests/ -v --cov=src
      
      - name: Type check
        run: |
          source .venv/bin/activate
          mypy src/
      
      - name: Lint
        run: |
          source .venv/bin/activate
          black --check src/
```

**Tempo de build comparado**:
- Com pip: ~3-4 minutos
- Com uv: ~30-45 segundos ⚡

---

### **Troubleshooting com uv**

#### **Conflito de dependências**
```bash
# uv mostra conflitos claramente durante compile
$ uv pip compile requirements.in

error: Because package-a==1.0.0 depends on package-b>=2.0.0
    and package-c==1.0.0 depends on package-b<2.0.0,
    we can conclude that package-a==1.0.0 and package-c==1.0.0 are incompatible.

# Solução: Ajustar versões em requirements.in
```

#### **Cache corrompido**
```bash
# Limpar cache global do uv
uv cache clean

# Reinstalar tudo do zero
rm -rf .venv
uv venv .venv
uv pip sync requirements.txt
```

#### **Migrar projeto existente de pip para uv**
```bash
# 1. Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Criar requirements.in do requirements.txt atual
cp requirements.txt requirements.in

# 3. Gerar lockfile com uv
uv pip compile requirements.in -o requirements.txt

# 4. Criar novo venv com uv
uv venv .venv --python 3.11
source .venv/bin/activate

# 5. Instalar com sync
uv pip sync requirements.txt

# 6. Testar aplicação
pytest tests/

# 7. Se tudo OK, commitar requirements.txt atualizado
```

---

### **Práticas Recomendadas com uv**

#### ✅ **DO's**
- Sempre usar `uv pip sync` em produção (garante ambiente exato)
- Manter `requirements.in` no Git (fonte de verdade)
- Gerar `requirements.txt` com hashes (`uv pip compile`)
- Usar `uv venv` para ambientes isolados
- Aproveitar cache global (não usar `--no-cache` sem motivo)

#### ❌ **DON'Ts**
- Não misturar pip e uv no mesmo workflow (escolher um)
- Não editar `requirements.txt` manualmente (sempre regenerar)
- Não ignorar warnings de resolução de dependências
- Não usar `uv pip install` diretamente em prod (usar `sync`)
- Não commitar `.venv/` no Git (adicionar ao .gitignore)

---

### **Recursos e Documentação uv**

- **Documentação Oficial**: https://docs.astral.sh/uv/
- **GitHub**: https://github.com/astral-sh/uv
- **Benchmarks**: https://astral.sh/blog/uv
- **Comparação com pip**: https://docs.astral.sh/uv/pip/compatibility/
- **Guia de Migração**: https://docs.astral.sh/uv/guides/integration/

---

## Cenários Críticos - Análise Detalhada

### Cenário 1: Parar o Container

**Desafios**:
- Container pode ter workflows em execução (podem ser interrompidos)
- N8N pode estar salvando dados no banco (risk de corrupção)
- Processos filhos podem não encerrar gracefully
- Container pode estar em estado instável (travado, OOM)

**Implementação Robusta**:

#### **Etapa 1: Verificação pré-parada**
- Confirmar que container existe e está running
- Verificar se há workflows ativos executando (via API REST se possível)
- Se workflows críticos estão rodando, considerar aguardar término ou avisar usuário

#### **Etapa 2: Graceful shutdown**
- `container.stop(timeout=30)`: Envia SIGTERM, aguarda 30s
- SIGTERM permite N8N finalizar operações pendentes
- Se N8N não encerra em 30s, Docker envia SIGKILL (force)

#### **Etapa 3: Confirmação de parada**
- `container.wait(condition='not-running', timeout=60)`
- Retorna exit code: `0` = encerramento limpo, `137` = SIGKILL (forçado), `143` = SIGTERM
- Exit code `137` indica que timeout expirou e foi forçado - **registrar como WARNING**

#### **Etapa 4: Verificação de estado final**
- `container.reload()` + verificar `container.status == 'exited'`
- Inspecionar `container.attrs['State']['OOMKilled']` - se `True`, container foi morto por falta de memória
- Verificar `container.attrs['State']['Error']` - pode conter mensagem de erro do Docker

#### **Tratamento de casos extremos**:

**Container já estava parado**:
- `container.stop()` lança `docker.errors.APIError` com código 304 (Not Modified)
- Tratar como sucesso (idempotente), logar como INFO: "Container já estava parado"

**Container não responde a SIGTERM**:
- Se `wait()` timeout expira, container ainda está running
- Forçar: `container.kill(signal='SIGKILL')`
- Logar como ERROR: "Container não encerrou gracefully, forçado com SIGKILL"
- Investigar logs do container para identificar causa

**Container em estado 'dead'**:
- Não pode ser parado (já está "morto" mas não removido)
- Tentar `container.remove(force=True)` para limpar
- Logar como CRITICAL: "Container em estado irrecuperável"

---

### Cenário 2: Verificar Parada Completa

**Por que não confiar apenas em `stop()` retornar**:
- `stop()` é assíncrono internamente - retorna antes da parada completa em alguns casos
- Race condition: status pode estar desatualizado se outro processo modificou container
- Processos filhos (webhooks, executions) podem continuar rodando por alguns segundos

**Método Robusto de Verificação**:

#### **Polling com Retry**
```python
import time
from docker.errors import NotFound

def wait_for_container_stopped(container, max_wait=60):
    """
    Aguarda até container estar completamente parado.
    
    Retorna:
        True se parou, False se timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            container.reload()  # Atualizar estado do daemon
            
            if container.status == 'exited':
                # Verificar exit code
                exit_code = container.attrs['State']['ExitCode']
                if exit_code == 0:
                    logger.info(f"Container {container.name} parou gracefully")
                else:
                    logger.warning(f"Container {container.name} encerrou com código {exit_code}")
                return True
            
            elif container.status in ('dead', 'removing'):
                logger.error(f"Container {container.name} em estado anormal: {container.status}")
                return False
            
            # Ainda rodando, aguardar mais
            time.sleep(2)
            
        except NotFound:
            # Container foi removido (exemplo: restart policy auto-removeu)
            logger.warning(f"Container {container.name} não encontrado - foi removido?")
            return False
    
    # Timeout expirou
    logger.error(f"Timeout aguardando parada de {container.name}")
    return False
```

#### **Verificação de Processos**
- Após `status == 'exited'`, confirmar que nenhum processo com PID do container está ativo
- Usar `docker.api.top(container_id)` ANTES da parada, confirmar vazio DEPOIS

#### **Verificação de Rede**
- Se N8N estava escutando porta 5678, confirmar que porta está fechada
- Usar `socket.socket().connect_ex(('localhost', 5678))` - deve retornar erro (porta fechada)

---

### Cenário 3: Verificar Integridade do Container

**Aspectos a Verificar**:

#### **1. Configuração de Volumes**
```python
def verify_container_volumes(container):
    """Verifica que volumes críticos estão montados"""
    mounts = container.attrs.get('Mounts', [])
    
    required_mounts = {
        '/home/node/.n8n': 'rw',  # Dados N8N (read-write)
        '/backup': 'rw'            # Volume de backup (read-write)
    }
    
    for mount in mounts:
        destination = mount['Destination']
        mode = mount.get('Mode', 'rw')
        
        if destination in required_mounts:
            if mode != required_mounts[destination]:
                logger.error(f"Volume {destination} tem modo {mode}, esperado {required_mounts[destination]}")
                return False
            del required_mounts[destination]
    
    if required_mounts:
        logger.error(f"Volumes faltando: {list(required_mounts.keys())}")
        return False
    
    return True
```

#### **2. Environment Variables**
```python
def verify_container_env(container):
    """Verifica que variáveis críticas estão configuradas"""
    env_vars = container.attrs['Config']['Env']
    env_dict = dict(e.split('=', 1) for e in env_vars)
    
    required_vars = ['N8N_ENCRYPTION_KEY', 'N8N_HOST', 'N8N_PORT']
    
    for var in required_vars:
        if var not in env_dict:
            logger.error(f"Variável de ambiente faltando: {var}")
            return False
        
        if var == 'N8N_ENCRYPTION_KEY' and len(env_dict[var]) < 32:
            logger.error("N8N_ENCRYPTION_KEY muito curta (mínimo 32 caracteres)")
            return False
    
    return True
```

#### **3. Health Status** (se configurado)
```python
def verify_container_health(container):
    """Verifica health do container (se healthcheck configurado)"""
    health = container.attrs['State'].get('Health')
    
    if health is None:
        logger.info("Container não tem healthcheck configurado")
        return None  # Não é erro, apenas não configurado
    
    status = health['Status']
    
    if status == 'healthy':
        return True
    elif status == 'unhealthy':
        # Capturar últimos logs de health
        failing_streak = health.get('FailingStreak', 0)
        last_log = health.get('Log', [])[-1] if health.get('Log') else {}
        logger.error(f"Container unhealthy (failing streak: {failing_streak})")
        logger.error(f"Último healthcheck: {last_log.get('Output', 'N/A')}")
        return False
    elif status == 'starting':
        logger.info("Container ainda em startup (health: starting)")
        return None  # Aguardar mais tempo
    
    return False
```

#### **4. Integridade de Dados (arquivos críticos)**
```python
def verify_n8n_data_integrity(container):
    """Verifica que arquivos críticos N8N existem e estão acessíveis"""
    # Executar comando dentro do container para verificar arquivos
    exit_code, output = container.exec_run('ls -la /home/node/.n8n/database.sqlite')
    
    if exit_code != 0:
        logger.error("Banco de dados N8N não encontrado")
        return False
    
    # Verificar tamanho mínimo (banco vazio é ~100KB)
    exit_code, output = container.exec_run('stat -c %s /home/node/.n8n/database.sqlite')
    
    if exit_code == 0:
        size = int(output.decode().strip())
        if size < 100000:  # 100KB
            logger.warning(f"Banco de dados muito pequeno: {size} bytes")
    
    return True
```

---

### Cenário 4: Iniciar o Container

**Desafios**:
- Container pode não iniciar se configuração inválida
- Pode iniciar mas crashar imediatamente (crash loop)
- Pode iniciar mas N8N não fica operacional (travado)

**Implementação Robusta**:

#### **Etapa 1: Pré-verificações**
```python
def pre_start_checks(container):
    """Verificações antes de iniciar container"""
    # 1. Confirmar que está parado
    container.reload()
    if container.status == 'running':
        logger.info("Container já está rodando")
        return True
    
    # 2. Verificar exit code da parada anterior
    exit_code = container.attrs['State'].get('ExitCode')
    if exit_code not in [0, None]:
        logger.warning(f"Container parou anormalmente (exit code {exit_code})")
    
    # 3. Verificar se OOMKilled
    if container.attrs['State'].get('OOMKilled'):
        logger.error("Container foi morto por falta de memória na execução anterior")
        logger.error("AÇÃO REQUERIDA: Aumentar memory_limit do container")
        return False
    
    # 4. Verificar espaço em disco
    # (executar no host, não no container)
    import shutil
    stat = shutil.disk_usage('/')
    free_gb = stat.free / (1024**3)
    if free_gb < 1:  # Menos de 1GB livre
        logger.error(f"Disco cheio! Apenas {free_gb:.2f} GB livres")
        return False
    
    return True
```

#### **Etapa 2: Start com captura de erro imediato**
```python
def start_container_safely(container):
    """Inicia container e detecta falhas imediatas"""
    try:
        container.start()
        logger.info(f"Container {container.name} iniciado")
    except docker.errors.APIError as e:
        logger.error(f"Falha ao iniciar container: {e.explanation}")
        return False
    
    # Aguardar alguns segundos para detectar crash imediato
    time.sleep(5)
    
    container.reload()
    if container.status != 'running':
        logger.error(f"Container crashou imediatamente após start (status: {container.status})")
        
        # Capturar logs de erro
        logs = container.logs(tail=50).decode('utf-8')
        logger.error(f"Logs do container:\n{logs}")
        
        return False
    
    return True
```

#### **Etapa 3: Monitorar startup via logs**
```python
def monitor_startup_logs(container, timeout=60):
    """Monitora logs de startup para detectar sucesso ou erro"""
    start_time = time.time()
    
    # Padrões que indicam startup bem-sucedido
    success_patterns = [
        'Server started',
        'Listening on port',
        'Editor is now accessible',
        'Webhook waiting'
    ]
    
    # Padrões que indicam erro
    error_patterns = [
        'Error:',
        'FATAL',
        'Cannot connect to database',
        'EADDRINUSE'  # Porta já em uso
    ]
    
    log_stream = container.logs(stream=True, follow=True)
    
    for log_line in log_stream:
        line = log_line.decode('utf-8').strip()
        logger.debug(f"[N8N] {line}")
        
        # Verificar sucesso
        for pattern in success_patterns:
            if pattern in line:
                logger.info(f"Startup detectado: {pattern}")
                return True
        
        # Verificar erro
        for pattern in error_patterns:
            if pattern in line:
                logger.error(f"Erro de startup detectado: {line}")
                return False
        
        # Timeout
        if time.time() - start_time > timeout:
            logger.error("Timeout aguardando startup (logs não indicaram sucesso)")
            return False
    
    return False
```

---

### Cenário 5: Verificar Inicialização Correta

**Verificação em Múltiplas Camadas**:

#### **Layer 1: Container Status** (Docker)
```python
container.reload()
assert container.status == 'running'
```

#### **Layer 2: Process Running** (processo N8N vivo)
```python
# Verificar que processo node está rodando
exit_code, output = container.exec_run('ps aux | grep node')
assert exit_code == 0
assert 'n8n' in output.decode()
```

#### **Layer 3: Port Listening** (servidor iniciou)
```python
import socket

def check_port_open(host, port, timeout=5):
    """Verifica se porta está aceitando conexões"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0  # 0 = sucesso (porta aberta)

assert check_port_open('localhost', 5678, timeout=10)
```

#### **Layer 4: HTTP Response** (web server respondendo)
```python
import requests

response = requests.get('http://localhost:5678', timeout=10)
assert response.status_code in [200, 302]  # 302 = redirect para /login
```

#### **Layer 5: Application Ready** (N8N completamente operacional)
```python
# Verificar endpoint healthcheck
response = requests.get('http://localhost:5678/healthz', timeout=10)
assert response.status_code == 200

# OU verificar API REST funcional
response = requests.get('http://localhost:5678/rest/workflows?limit=1', timeout=10)
assert response.status_code == 200
data = response.json()
assert 'data' in data
```

**Estratégia combinada**:
- Executar Layer 1 imediatamente após `start()` (2 segundos)
- Layer 2 após 5 segundos (tempo mínimo de boot)
- Layer 3 com retry: polling a cada 2s por até 30s
- Layer 4 com retry: após porta abrir, tentar HTTP
- Layer 5 apenas quando Layer 4 passar

---

### Cenário 6: Verificar N8N Operacional (E2E)

**Teste Funcional Completo**:

#### **1. Health Endpoint**
```python
def check_n8n_health():
    """Verifica endpoint de health dedicado"""
    try:
        response = requests.get(
            'http://localhost:5678/healthz',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # Estrutura esperada: {"status": "ok"}
            if data.get('status') == 'ok':
                return True
        
        return False
    except requests.RequestException as e:
        logger.error(f"Healthcheck falhou: {e}")
        return False
```

#### **2. API REST Funcional**
```python
def check_n8n_api():
    """Verifica que API REST está funcional"""
    endpoints_to_test = [
        '/rest/workflows?limit=1',
        '/rest/credentials?limit=1',
        '/rest/executions?limit=1'
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(
                f'http://localhost:5678{endpoint}',
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Endpoint {endpoint} retornou {response.status_code}")
                return False
            
            data = response.json()
            if 'data' not in data:
                logger.error(f"Endpoint {endpoint} retornou estrutura inválida")
                return False
            
        except requests.RequestException as e:
            logger.error(f"Erro ao consultar {endpoint}: {e}")
            return False
    
    return True
```

#### **3. Banco de Dados Acessível**
```python
def check_n8n_database(container):
    """Verifica que banco está acessível e schema OK"""
    # Executar query simples no SQLite
    exit_code, output = container.exec_run(
        'sqlite3 /home/node/.n8n/database.sqlite "SELECT COUNT(*) FROM credentials_entity;"'
    )
    
    if exit_code != 0:
        logger.error("Erro ao consultar banco de dados")
        return False
    
    try:
        count = int(output.decode().strip())
        logger.info(f"Banco acessível: {count} credenciais encontradas")
        return True
    except ValueError:
        logger.error(f"Query retornou valor inválido: {output}")
        return False
```

#### **4. Teste de Workflow Simples** (máxima confiança)
```python
def create_and_execute_test_workflow():
    """Cria workflow de teste e executa para confirmar funcionamento completo"""
    workflow_data = {
        "name": "_HEALTHCHECK_TEST_",
        "active": False,
        "nodes": [
            {
                "id": "start",
                "type": "n8n-nodes-base.start",
                "position": [250, 300],
                "parameters": {}
            },
            {
                "id": "set",
                "type": "n8n-nodes-base.set",
                "position": [450, 300],
                "parameters": {
                    "values": {
                        "string": [
                            {
                                "name": "status",
                                "value": "ok"
                            }
                        ]
                    }
                }
            }
        ],
        "connections": {
            "start": {
                "main": [[{"node": "set", "type": "main", "index": 0}]]
            }
        }
    }
    
    try:
        # Criar workflow
        response = requests.post(
            'http://localhost:5678/rest/workflows',
            json=workflow_data,
            timeout=10
        )
        assert response.status_code == 200
        workflow_id = response.json()['id']
        
        # Executar workflow
        response = requests.post(
            f'http://localhost:5678/rest/workflows/{workflow_id}/execute',
            timeout=30
        )
        assert response.status_code == 200
        
        # Deletar workflow de teste
        requests.delete(f'http://localhost:5678/rest/workflows/{workflow_id}')
        
        logger.info("Teste funcional E2E passou: workflow executado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Teste funcional E2E falhou: {e}")
        return False
```

**Recomendação de uso**:
- **Desenvolvimento**: Executar somente Layers 1-4 (mais rápido)
- **Staging**: Executar todos incluindo teste E2E
- **Produção**: Executar 1-4 rotineiramente, E2E somente após restore/upgrade

---

## Resumo de Bibliotecas e Ferramentas por Categoria

### Gerenciamento de Ambiente (ESSENCIAL)
0. **uv** - Gerenciador ultra-rápido de ambientes virtuais e pacotes (10-100x mais rápido que pip)

### Essenciais (OBRIGATÓRIAS)
1. **docker** - Controle de containers
2. **requests** ou **httpx** - Healthchecks HTTP
3. **pathlib** (stdlib) - Manipulação de caminhos
4. **logging** (stdlib) - Auditoria
5. **json** (stdlib) - Validação de backups

### Segurança (ALTAMENTE RECOMENDADAS)
6. **python-dotenv** - Gestão de secrets
7. **hvac** - Integração Vault (produção)
8. **cryptography** - Operações cripto avançadas

### Repositórios (escolher conforme infraestrutura)
9. **boto3** - AWS S3
10. **azure-storage-blob** - Azure
11. **subprocess** (stdlib) - rsync/rclone

### Qualidade (RECOMENDADAS)
12. **pydantic** - Validação de schemas
13. **tenacity** - Retry logic
14. **pytest** - Testes
15. **mypy** - Type checking
16. **black** - Formatação

### Usabilidade
17. **click** - Interface CLI
18. **python-json-logger** - Logs estruturados

---
Setup de ambiente com uv**:
   ```bash
   # Instalar uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Criar projeto
   mkdir n8n-backup && cd n8n-backup
   uv venv .venv --python 3.11
   source .venv/bin/activate
   ```

2. **Definir arquitetura**: Decidir entre script monolítico ou módulos separados (backup.py, restore.py, docker_manager.py)

3. **Criar estrutura de projeto**:
   ```
   n8n-backup/
   ├── src/
   │   ├── __init__.py
   │   ├── backup.py
   │   ├── restore.py
   │   ├── docker_manager.py
   │   ├── healthcheck.py
   │   └── repository.py
   ├── tests/
4. **Configurar dependências com uv**:
   ```bash
   # Criar requirements.in com dependências diretas
   # Gerar lockfile
   uv pip compile requirements.in -o requirements.txt
   # Instalar
6. **Adicionar testes**:
   - Testes unitários para cada função
   - Testes de integração com container real
   - Mock de APIs externas (S3, Vault)

7. **Documentar**:
   - Docstrings em todas as funções
   - README com instruções de setup (incluindo uv)
   - Runbook para operações de emergência

8. **Integrar com CI/CD**:
   - GitHub Actions com uv (build 10x mais rápido)
   - Lint com black + mypy
   - Build de imagem Docker otimizada com uv
   └── README.md
   ```

3. **Implementar módulos core**:
   - Docker manager (start/stop/verify)
   - Healthcheck (todas as layers)
   - Backup logic (export + upload)
   - Restore logic (download + import)

4. **Adicionar testes**:
   - Testes unitários para cada função
   - Testes de integração com container real
   - Mock de APIs externas (S3, Vault)

5. **Documentar**:
   - Docstrings em todas as funções
   - README com instruções de setup
   - Runbook para operações de emergência

6. **Integrar com CI/CD**:
   - GitHub Actions para rodar testes
   - Lint com black + mypy
   - Build de imagem Docker (opcional)

---

Este documento serve como especificação técnica completa para implementação da solução Python. Todos os recursos mencionados são **produção-ready** e seguem melhores práticas da indústria.
