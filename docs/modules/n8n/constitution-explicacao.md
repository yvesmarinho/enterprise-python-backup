utar # Explicação da Constitution N8N Enterprise

## Introdução

Este documento fornece explicações detalhadas sobre cada seção da **N8N Enterprise Backup & Restore Constitution**, servindo como guia interpretativo para equipes de DevOps, Segurança e Desenvolvimento. A Constitution estabelece padrões não-negociáveis e melhores práticas para operações críticas de backup e restore no ambiente N8N Enterprise v2.3.0.

**Linguagem de Implementação**: Python 3.11+ é a linguagem **preferencial e recomendada** para implementação de operações de backup/restore neste projeto, oferecendo robustez, tratamento de erros estruturado, e integração nativa com Docker, cloud providers e ferramentas enterprise. Scripts bash são aceitos apenas para operações simples e isoladas.

**Gerenciamento de Ambiente**: **uv** é o gerenciador oficial de ambientes virtuais e pacotes Python deste projeto, oferecendo performance 10-100x superior ao pip tradicional e lockfiles reproduzíveis para ambientes enterprise.

---

## Seção 1: Core Principles (Princípios Fundamentais)

### I. Segurança e Criptografia

**O que significa**: Este princípio estabelece que a segurança é a base de todas as operações de backup/restore.

**Por que é importante**:
- Credenciais contêm tokens de API, senhas e chaves de acesso a sistemas críticos
- Vazamento de credenciais pode comprometer toda a infraestrutura integrada ao N8N
- Criptografia garante que mesmo com acesso físico aos backups, dados permanecem protegidos

**Regra NON-NEGOTIABLE explicada**:
- **"N8N_ENCRYPTION_KEY deve ser idêntica"**: A chave é usada tanto para criptografar na exportação quanto descriptografar na importação. Se diferente, o processo falha completamente.
- **Armazenamento separado**: Nunca armazene a chave junto com os backups. É como guardar a chave do cofre dentro do cofre.

**Exemplo prático**:
```bash
# Correto: Exportar com chave configurada
export N8N_ENCRYPTION_KEY="minha-chave-super-secreta-32chars"
n8n export:credentials --backup --output=/backup/

# Incorreto: Fazer backup e guardar tudo no mesmo lugar
# /backup/
#   ├── credenciais.json
#   └── ENCRYPTION_KEY.txt  ❌ NUNCA FAZER ISSO
```

**Locais seguros para a chave**:
- HashiCorp Vault (recomendado para produção)
- AWS Secrets Manager
- Azure Key Vault
- Arquivo físico em cofre (disaster recovery offline)

---

### II. Preservação de Identidade

**O que significa**: Os IDs únicos de workflows e credenciais devem ser mantidos durante backup/restore.

**Por que é importante**:
- Workflows referenciam credenciais por ID
- Restaurar com IDs diferentes quebraria todas as conexões
- IDs preservados permitem atualizações em vez de duplicações

**Como funciona**:
```bash
# SEM --backup (ERRADO)
n8n export:credentials --output=/backup/  
# Gera: novos IDs aleatórios serão criados no restore

# COM --backup (CORRETO)
n8n export:credentials --backup --output=/backup/
# Preserva: ID original "credential-abc123" mantido
```

**Cenário real**:
- Workflow "Integração CRM" usa credencial ID "cred-salesforce-001"
- Backup sem `--backup` → Restore cria "cred-salesforce-999" (novo ID)
- Resultado: Workflow quebra, todas as 50 integrações falham ❌
- Com `--backup`: ID mantido, workflow funciona imediatamente ✅

---

### III. Integridade e Consistência

**O que significa**: Operações devem ser atômicas e verificadas, evitando estados inconsistentes.

**Por que parar o N8N**:
- Evita que um workflow sendo editado seja parcialmente salvo durante backup
- Previne corruption de dados se restore ocorrer com sistema ativo
- Garante snapshot consistente do estado completo

**Processo explicado passo-a-passo**:

1. **Antes de Restore - Backup atual**:
   ```bash
   # Preparar diretório no host
   SERVER_NAME=$(hostname)
   TIMESTAMP=$(date +%Y%m%d-%H%M%S)
   mkdir -p /tmp/bkpfile
   
   # Container DEVE estar rodando para export (com volume mount)
   docker run --rm \
     --volumes-from n8n-container \
     -v /tmp/bkpfile:/backup \
     n8nio/n8n:latest \
     n8n export:credentials --backup --output=/backup/${TIMESTAMP}-${SERVER_NAME}-n8n-credentials/
   ```
   **Razão**: Se restore falhar, você tem como voltar

2. **Parar N8N** (opcional - workflows param, mas container continua):
   ```bash
   # OPÇÃO A: Apenas desabilitar workflows (RECOMENDADO)
   curl -X POST http://localhost:5678/rest/workflows/deactivate-all
   
   # OPÇÃO B: Parar container (precisará reiniciar antes do import)
   docker stop n8n-container
   ```
   **Razão**: Evita execuções de workflows durante restore

3. **Restore** (container PRECISA estar rodando):
   ```bash
   # Se parou no passo 2, iniciar novamente
   docker start n8n-container && sleep 5
   
   # Definir arquivo de backup a restaurar
   BACKUP_FILE="20260120-143055-prod-server-n8n-credentials"  # Exemplo
   
   # Executar import com volume mount
   docker run --rm \
     --volumes-from n8n-container \
     -v /tmp/bkpfile:/backup \
     n8nio/n8n:latest \
     n8n import:credentials --separate --input=/backup/${BACKUP_FILE}/
   ```
   **⚠️ Nota Crítica**: Comandos `n8n` só funcionam com container em execução!

4. **Verificação**:
   ```bash
   # Verificar logs
   tail -f /home/node/.n8n/logs/n8n.log | grep -i "credential"
   
   # Contar credenciais importadas
   sqlite3 ~/.n8n/database.sqlite "SELECT COUNT(*) FROM credentials_entity;"
   ```

5. **Teste funcional**:
   - Criar workflow simples usando credencial restaurada
   - Executar e verificar autenticação bem-sucedida
   - Só então considerar restore completo

**Quando NÃO parar N8N**:
- Ambientes de desenvolvimento pessoal
- Backups de leitura (não afeta consistência)
- Testes em instâncias dedicadas

---

### IV. Automação e Versionamento

**O que significa**: Backups devem ser automáticos, versionados e rastreáveis.

**Por que automatizar**:
- Eliminação de erro humano (esquecer de fazer backup)
- Consistência de processo
- Backups regulares sem intervenção

**Nomenclatura com timestamp explicada**:
```bash
# Estrutura recomendada com máscara YYYYMMDD-HHMMSS-{server}-n8n.*
/tmp/bkpfile/
  ├── 20260120-020000-prod-server-n8n-credentials/
  │   ├── cred-001.json
  │   └── cred-002.json
  ├── 20260120-020000-prod-server-n8n-workflows/
  │   ├── workflow-001.json
  │   └── workflow-002.json
  ├── 20260121-020000-prod-server-n8n-credentials/
  └── 20260121-020000-prod-server-n8n-workflows/

# Componentes do nome:
# YYYYMMDD-HHMMSS: Timestamp do backup
# {server}: Nome do servidor (hostname)
# n8n: Identificador da aplicação
# credentials|workflows: Tipo de backup
```

**Vantagens**:
- Fácil identificar backup mais recente por timestamp
- Nome do servidor identifica origem do backup (útil em ambientes multi-servidor)
- Possibilidade de rollback para data específica
- Organização cronológica automática
- Compatível com ordenação alfabética (YYYYMMDD)

**Exemplo de nomenclatura completa**:
```
20260120-143055-prod-server-n8n-credentials/
│
├─ YYYYMMDD: 20260120 (20 de janeiro de 2026)
├─ HHMMSS: 143055 (14:30:55)
├─ server: prod-server (hostname do servidor)
├─ app: n8n (aplicação)
└─ type: credentials ou workflows (tipo de backup)
```

**Versionamento com Git**:
```bash
cd /backup/n8n
git init
git add credenciais/20260120-020000/
git commit -m "Backup credenciais - 20 jan 2026 02:00"
```

**Benefícios**:
- Histórico completo de mudanças
- Diff entre versões (ver o que mudou)
- Branches para diferentes ambientes (prod, staging)
- Integração com CI/CD

**Script de exemplo explicado**:
```bash
#!/bin/bash
# Variáveis de ambiente
SERVER_NAME=$(hostname)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BASE="/tmp/bkpfile"
BACKUP_PREFIX="${TIMESTAMP}-${SERVER_NAME}-n8n"

# Criar diretório base
mkdir -p "$BACKUP_BASE"

# Backup de workflows com volume mount
echo "Iniciando backup de workflows..."
docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n export:workflow --backup --output="/backup/${BACKUP_PREFIX}-workflows/"

if [ $? -eq 0 ]; then
    echo "✓ Workflows exportados: ${BACKUP_PREFIX}-workflows"
    # Enviar para repositório (exemplo: rsync, rclone, etc.)
    # rclone copy "${BACKUP_BASE}/${BACKUP_PREFIX}-workflows/" remote:n8n-backups/
else
    echo "✗ Erro no backup de workflows!"
    exit 1
fi

# Backup de credenciais
echo "Iniciando backup de credenciais..."
docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n export:credentials --backup --output="/backup/${BACKUP_PREFIX}-credentials/"

if [ $? -eq 0 ]; then
    echo "✓ Credenciais exportadas: ${BACKUP_PREFIX}-credentials"
    # Enviar para repositório
    # rclone copy "${BACKUP_BASE}/${BACKUP_PREFIX}-credentials/" remote:n8n-backups/
else
    echo "✗ Erro no backup de credenciais!"
    exit 1
fi

echo "✓ Backup completo concluído: ${BACKUP_PREFIX}"
```

**Setup de Ambiente Python com uv**:
```bash
#!/bin/bash
# setup-n8n-backup.sh - Configuração inicial do ambiente

set -euo pipefail

echo "🔧 Configurando ambiente N8N Backup..."

# Instalar uv se não existir
if ! command -v uv &> /dev/null; then
    echo "📦 Instalando uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Criar ambiente virtual
echo "🐍 Criando ambiente virtual Python 3.11..."
uv venv .venv --python 3.11

# Ativar ambiente
source .venv/bin/activate

# Instalar dependências
echo "📥 Instalando dependências (ultra-rápido com uv)..."
uv pip sync requirements.txt

# Verificar instalação
python -c "import docker, requests, pydantic; print('✅ Dependências OK')"

# Copiar configuração exemplo
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Configure N8N_ENCRYPTION_KEY em .env antes de usar!"
fi

echo "✅ Setup completo! Ative com: source .venv/bin/activate"
```

**requirements.txt** (gerado por `uv pip compile requirements.in`):
```txt
# Core
docker>=7.0.0
requests>=2.31.0
pydantic>=2.5.0

# Cloud/Storage (escolher conforme necessidade)
boto3>=1.34.0          # AWS S3
azure-storage-blob>=12.19.0  # Azure

# Segurança
python-dotenv>=1.0.0
hvac>=2.1.0            # HashiCorp Vault
cryptography>=41.0.0

# Resiliência
tenacity>=8.2.0

# CLI
click>=8.1.0

# Logging
python-json-logger>=2.0.0

# Dev/Test
pytest>=7.4.0
pytest-cov>=4.1.0
mypy>=1.7.0
black>=23.12.0
```

**Agendamento Cron explicado**:
```bash
0 2 * * * /scripts/backup-n8n.sh >> /var/log/n8n-backup.log 2>&1
│ │ │ │ │
│ │ │ │ └─── Dia da semana (0-7, 0 e 7 = domingo)
│ │ │ └───── Mês (1-12)
│ │ └─────── Dia do mês (1-31)
│ └───────── Hora (0-23)
└─────────── Minuto (0-59)

# 0 2 * * * = Todo dia às 2 AM
# >> /var/log/n8n-backup.log = Adiciona output ao log
# 2>&1 = Redireciona erros (stderr) para stdout (mesmo arquivo de log)
```

**Estratégias de retenção**:
- Diários: 7 últimos dias
- Semanais: 4 últimas semanas
- Mensais: 12 últimos meses
- Anuais: indefinido

---

### V. Separação de Responsabilidades

**O que significa**: Credenciais e workflows são entidades independentes com ciclos de vida próprios.

**Por que separar**:
- **Segurança**: Credenciais são mais sensíveis, exigem controle de acesso mais restrito
- **Granularidade**: Restaurar apenas workflows sem tocar em credenciais (ou vice-versa)
- **Performance**: Backups menores e mais rápidos

**Comandos distintos explicados**:
```bash
# Backup de credenciais apenas
n8n export:credentials --backup --output=/backup/creds/
# Gera: arquivos com dados sensíveis criptografados

# Backup de workflows apenas  
n8n export:workflow --backup --output=/backup/workflows/
# Gera: arquivos com lógica de automação (menos sensível)
```

**Flag `--separate` explicada**:
```bash
# SEM --separate (arquivo único consolidado)
n8n export:credentials --backup --output=/backup/all-credentials.json
# Gera: 1 arquivo com todas as credenciais

# COM --separate (arquivos individuais)
n8n export:credentials --backup --separate --output=/backup/creds/
# Gera:
#   /backup/creds/
#     ├── GoogleAPI.json
#     ├── SlackBot.json
#     ├── PostgreSQL.json
#     └── SalesforceAPI.json
```

**Vantagens de `--separate`**:
- **Restauração seletiva**: Importar só GoogleAPI sem tocar outras
- **Versionamento**: Git mostra mudanças específicas por credencial
- **Depuração**: Fácil identificar qual credencial tem problema
- **Organização**: Estrutura de diretórios clara

**Estrutura recomendada**:
```
/backup/n8n/
  ├── credenciais/
  │   └── 20260120-020000/
  │       ├── GoogleAPI.json
  │       └── SlackBot.json
  └── fluxos/
      └── 20260120-020000/
          ├── CRM-Integration.json
          ├── Email-Automation.json
          └── Data-Sync.json
```

---

## Seção 2: Comandos e Operações Padrão

Esta seção documenta a **sintaxe exata** dos comandos CLI do N8N.

### Anatomia de um Comando de Backup

```bash
n8n export:credentials --backup --output=/caminho/backup/credenciais/
│   │                   │        │
│   │                   │        └─── Caminho de destino (OBRIGATÓRIO)
│   │                   └──────────── Preserva IDs (OBRIGATÓRIO para restore)
│   └──────────────────────────────── Subcomando de exportação
└────────────────────────────────────── Binário N8N CLI
```

### Flags Explicadas

**`--backup`**:
- **Função**: Preserva IDs originais no export
- **Quando usar**: SEMPRE, a menos que queira clonar/duplicar
- **Efeito**: No restore, itens com IDs existentes são atualizados, não duplicados

**`--output`**:
- **Função**: Define destino dos arquivos exportados
- **Tipos aceitos**: 
  - Diretório: `/backup/creds/` (gera múltiplos arquivos)
  - Arquivo: `/backup/all.json` (gera arquivo único)
- **Recomendação**: Sempre usar diretório com `--separate`

**`--separate`** (import apenas):
- **Função**: Processa arquivos JSON individuais
- **Quando usar**: Quando backup foi feito em diretório
- **Alternativa**: Sem flag processa arquivo único

**`--all`**:
- **Função**: Exporta todos os itens
- **Padrão**: Ativo por padrão, não precisa especificar
- **Uso**: Explícito apenas para clareza em scripts

**`--id=<ID>`**:
- **Função**: Exporta/importa item específico
- **Exemplo**: `--id=abc123`
- **Quando usar**: Restore seletivo ou backup pontual

**`--pretty`**:
- **Função**: Formata JSON com indentação
- **Quando usar**: Depuração, inspeção manual
- **Custo**: Arquivos maiores (~30% mais espaço)

---

## Seção 3: Workflow de Operações

### Procedimento de Backup - Detalhado

**Passo 1: Preparação**
```bash
mkdir -p /backup/n8n/credenciais/$(date +%Y%m%d-%H%M%S)
```
- **O que faz**: Cria estrutura de diretórios com timestamp
- **Por que `-p`**: Cria pais se não existirem, não falha se já existe
- **Timestamp**: Garante unicidade, evita sobrescrever backups anteriores

**Passo 2: Parada (Produção)**
```bash
# Docker
docker stop n8n-container
# Aguarda graceful shutdown (padrão: 10s)

# Verificar parada
docker ps | grep n8n  # Não deve listar nada
```
- **Quando pular**: Dev/staging ou backups de leitura
- **Timeout**: Se processos travarem, força após 10s

**Passo 3: Exportação**
```bash
# Preparar variáveis
SERVER_NAME=$(hostname)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BASE="/tmp/bkpfile"
BACKUP_PREFIX="${TIMESTAMP}-${SERVER_NAME}-n8n"

mkdir -p "$BACKUP_BASE"

# Para Docker: usar docker run com volume mount (RECOMENDADO)
# Container N8N principal DEVE estar rodando
docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n export:credentials --backup --output="/backup/${BACKUP_PREFIX}-credentials/"

docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n export:workflow --backup --output="/backup/${BACKUP_PREFIX}-workflows/"

# Verificar arquivos gerados
ls -lh "${BACKUP_BASE}/${BACKUP_PREFIX}-"*

# Enviar para repositório de backup
# Exemplos:
# rsync -avz "${BACKUP_BASE}/" backup-server:/backups/n8n/
# rclone copy "${BACKUP_BASE}/" remote:n8n-backups/
# aws s3 sync "${BACKUP_BASE}/" s3://empresa-backups/n8n/

# ===== ALTERNATIVA: Para instalação npm/binário direto =====
# n8n export:credentials --backup --output="${BACKUP_BASE}/${BACKUP_PREFIX}-credentials/"
# n8n export:workflow --backup --output="${BACKUP_BASE}/${BACKUP_PREFIX}-workflows/"
```
- **Ordem**: Irrelevante, são independentes
- **Paralelização**: Pode rodar simultaneamente em shells diferentes
- **⚠️ Crítico**: Container principal N8N DEVE estar rodando
- **Volume mount**: `/tmp/bkpfile` no host → `/backup` no container

**Passo 4: Verificação Crítica**
```bash
# Listar arquivos gerados
ls -lh /backup/credenciais/
# -l: lista detalhada
# -h: tamanhos legíveis (KB, MB)

# Verificar não-vazio
find /backup/credenciais/ -type f -empty
# Não deve retornar nada; se retornar, arquivo vazio = erro

# Validar JSON
for file in /backup/credenciais/*.json; do
    jq empty "$file" || echo "ERRO em $file"
done
# jq empty: valida sintaxe sem output; || = "se falhar, então..."
```

**Passo 5: Armazenamento**
```bash
# Git local
git -C /backup add .
git -C /backup commit -m "Backup $(date +%Y-%m-%d)"

# Upload S3 (AWS)
aws s3 sync /backup/ s3://empresa-n8n-backups/ --sse AES256

# Upload Azure
az storage blob upload-batch \
    --destination backups \
    --source /backup/ \
    --account-name empresabackups
```

**Passo 6: Envio para Repositório de Backup**
```bash
# Após backup bem-sucedido, enviar para repositório centralizado

BACKUP_BASE="/tmp/bkpfile"
BACKUP_PREFIX="${TIMESTAMP}-${SERVER_NAME}-n8n"

# Opção 1: rsync para servidor remoto
rsync -avz --progress \
  "${BACKUP_BASE}/${BACKUP_PREFIX}-"* \
  backup-server:/backups/n8n/

# Opção 2: rclone para nuvem (S3, Google Drive, etc.)
rclone copy "${BACKUP_BASE}/" remote:n8n-backups/ \
  --include "${BACKUP_PREFIX}-*/**" \
  --progress

# Opção 3: AWS S3
aws s3 sync "${BACKUP_BASE}/" s3://empresa-backups/n8n/ \
  --exclude "*" \
  --include "${BACKUP_PREFIX}-*/*" \
  --sse AES256

# Opção 4: Tar + envio
tar -czf "/tmp/${BACKUP_PREFIX}.tar.gz" -C "${BACKUP_BASE}" \
  "${BACKUP_PREFIX}-credentials" \
  "${BACKUP_PREFIX}-workflows"
# Enviar .tar.gz para repositório

# Limpeza local após envio (manter apenas últimos 7 dias)
find "${BACKUP_BASE}" -type d -mtime +7 -name "*-n8n-*" -exec rm -rf {} +

echo "✓ Backup enviado para repositório: ${BACKUP_PREFIX}"
```

**Passo 7: Reinício**
```bash
docker start n8n-container

# Aguardar healthcheck
timeout 30 bash -c 'until curl -s http://localhost:5678/healthz; do sleep 1; done'
# Aguarda até 30s por healthcheck positivo
```

---

### Procedimento de Restore - Detalhado

**⚠️ PRÉ-REQUISITO**: Baixar backup do repositório para `/tmp/bkpfile`

```bash
# Exemplo: Baixar do repositório antes de restaurar

BACKUP_TO_RESTORE="20260120-020000-prod-server-n8n"
BACKUP_BASE="/tmp/bkpfile"

# Opção 1: rsync do servidor remoto
rsync -avz backup-server:/backups/n8n/${BACKUP_TO_RESTORE}-* "${BACKUP_BASE}/"

# Opção 2: rclone da nuvem
rclone copy remote:n8n-backups/ "${BACKUP_BASE}/" \
  --include "${BACKUP_TO_RESTORE}-*/**"

# Opção 3: AWS S3
aws s3 sync s3://empresa-backups/n8n/ "${BACKUP_BASE}/" \
  --exclude "*" \
  --include "${BACKUP_TO_RESTORE}-*/*"

# Opção 4: Se backup está em tar.gz
cd /tmp
wget https://backup-repo.empresa.com/n8n/${BACKUP_TO_RESTORE}.tar.gz
tar -xzf ${BACKUP_TO_RESTORE}.tar.gz -C ${BACKUP_BASE}/

# Verificar arquivos baixados
ls -lh "${BACKUP_BASE}/${BACKUP_TO_RESTORE}-"*
```

---

**IMPORTANTE - Ambiente Docker vs npm/binário**:
- **Docker**: Usar `docker run --rm --volumes-from n8n-container` para operações de backup/restore
- **npm/binário**: Execute diretamente `n8n <comando>` no terminal do servidor
- **Volume mount**: `/tmp/bkpfile` (host) mapeado para `/backup` (container temporário)

**Por que usar `docker run` em vez de `docker exec`?**
- ✅ **Isolamento**: Container temporário não interfere no container principal
- ✅ **Volumes**: `--volumes-from` acessa dados do container principal sem modificá-lo
- ✅ **Limpeza**: `--rm` remove container temporário automaticamente
- ✅ **Flexibilidade**: Permite mount de volumes adicionais (`-v /tmp/bkpfile:/backup`)

**Estrutura de comando explicada**:
```bash
docker run --rm \
  --volumes-from n8n-container \    # Acessa volumes do container principal
  -v /tmp/bkpfile:/backup \          # Mount adicional para backup
  n8nio/n8n:latest \                 # Imagem (mesma versão do principal)
  n8n export:credentials --backup --output=/backup/...
  │   └─ Comando executado dentro do container temporário
```

**Passo 1: Preparação e Download**
```bash
# 1. Baixar backup do repositório para /tmp/bkpfile
BACKUP_TO_RESTORE="20260120-020000-prod-server-n8n"
BACKUP_BASE="/tmp/bkpfile"
mkdir -p "${BACKUP_BASE}"

# Exemplo com rsync de servidor remoto
rsync -avz backup-server:/backups/n8n/${BACKUP_TO_RESTORE}-* "${BACKUP_BASE}/"

# Ou AWS S3
# aws s3 sync s3://empresa-backups/n8n/ "${BACKUP_BASE}/" \
#   --exclude "*" --include "${BACKUP_TO_RESTORE}-*/*"

# 2. Verificar backup existe e está íntegro
ls -lh "${BACKUP_BASE}/${BACKUP_TO_RESTORE}-credentials/"
ls -lh "${BACKUP_BASE}/${BACKUP_TO_RESTORE}-workflows/"
# Deve listar arquivos .json

# 3. Verificar integridade JSON
for f in "${BACKUP_BASE}/${BACKUP_TO_RESTORE}"-*/*.json; do
    jq . "$f" > /dev/null || echo "⚠️ Corrompido: $f"
done

echo "✓ Backup baixado e validado: ${BACKUP_TO_RESTORE}"
```

**Passo 2: Backup Atual (CRÍTICO)**
```bash
# Preparar variáveis para backup de rollback
SERVER_NAME=$(hostname)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BASE="/tmp/bkpfile"
BACKUP_PREFIX="${TIMESTAMP}-${SERVER_NAME}-n8n-rollback"

mkdir -p "$BACKUP_BASE"

# Container DEVE estar rodando para export
echo "Criando backup de segurança antes do restore..."

docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n export:credentials --backup --output="/backup/${BACKUP_PREFIX}-credentials/"

docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n export:workflow --backup --output="/backup/${BACKUP_PREFIX}-workflows/"

# Verificar sucesso
if [ -d "${BACKUP_BASE}/${BACKUP_PREFIX}-credentials" ] && \
   [ -d "${BACKUP_BASE}/${BACKUP_PREFIX}-workflows" ]; then
    echo "✓ Backup de segurança salvo: ${BACKUP_PREFIX}"
else
    echo "✗ Erro ao salvar backup de segurança!"
    exit 1
fi
```
- **Por que**: Se restore falhar, você pode reverter
- **Localização**: `/tmp/bkpfile` com sufixo `-rollback`
- **Importante**: Container precisa estar rodando para executar comandos export

**Passo 3: Modo Manutenção** (Opcional mas recomendado)
```bash
# OPÇÃO A: Parar workflows mas manter container rodando (RECOMENDADO)
# Desabilitar todos os workflows ativos via API
curl -X POST http://localhost:5678/rest/workflows/deactivate-all

# OPÇÃO B: Parar container completamente (precisará reiniciar para import)
docker stop n8n-container
# Aguardar completa parada
while docker ps | grep -q n8n; do sleep 1; done
```
**Nota**: Se escolher OPÇÃO B, precisará iniciar o container antes do Passo 4 para executar os comandos import.

**Passo 4: Importação** (Container DEVE estar rodando)
```bash
# Se parou container no Passo 3, iniciar agora
docker start n8n-container
sleep 5  # Aguardar inicialização

# Definir backup a restaurar (baixado do repositório para /tmp/bkpfile)
BACKUP_TO_RESTORE="20260120-020000-prod-server-n8n"  # Exemplo
BACKUP_BASE="/tmp/bkpfile"
BACKUP_ROLLBACK_PREFIX="$(date +%Y%m%d-%H%M%S)-$(hostname)-n8n-rollback"

echo "Restaurando de: ${BACKUP_TO_RESTORE}"

# Restore credenciais com volume mount
docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n import:credentials --separate --input="/backup/${BACKUP_TO_RESTORE}-credentials/"

# Capturar erros
if [ $? -ne 0 ]; then
    echo "✗ ERRO no restore de credenciais!"
    echo "Executando rollback..."
    # Rollback
    docker run --rm \
      --volumes-from n8n-container \
      -v "${BACKUP_BASE}:/backup" \
      n8nio/n8n:latest \
      n8n import:credentials --separate --input="/backup/${BACKUP_ROLLBACK_PREFIX}-credentials/"
    exit 1
fi

echo "✓ Credenciais restauradas com sucesso"

# Restore workflows
docker run --rm \
  --volumes-from n8n-container \
  -v "${BACKUP_BASE}:/backup" \
  n8nio/n8n:latest \
  n8n import:workflow --separate --input="/backup/${BACKUP_TO_RESTORE}-workflows/"

if [ $? -ne 0 ]; then
    echo "✗ ERRO no restore de workflows!"
    echo "Executando rollback..."
    # Rollback
    docker run --rm \
      --volumes-from n8n-container \
      -v "${BACKUP_BASE}:/backup" \
      n8nio/n8n:latest \
      n8n import:workflow --separate --input="/backup/${BACKUP_ROLLBACK_PREFIX}-workflows/"
    exit 1
fi

echo "✓ Workflows restaurados com sucesso"
```
**Importante**: 
- Container principal N8N DEVE estar rodando
- Use `docker run --rm --volumes-from` para acessar dados do container principal
- Volume mount: `/tmp/bkpfile` (host) → `/backup` (container temporário)
- Arquivos de backup devem estar em `/tmp/bkpfile` (baixados do repositório)
- Para npm/binário: execute diretamente `n8n import:* --input=/tmp/bkpfile/...`

**Passo 5: Verificação**
```bash
# Iniciar N8N
docker start n8n-container

# Aguardar startup
sleep 10

# Verificar logs
docker logs n8n-container --tail 50 | grep -i "credential\|workflow\|error"

# Contar itens no banco (SQLite)
docker exec n8n-container sqlite3 /home/node/.n8n/database.sqlite \
    "SELECT COUNT(*) FROM credentials_entity;"
    
# Deve retornar número esperado de credenciais

# Testar na UI
curl -s http://localhost:5678/rest/credentials | jq '.data | length'
```

**Passo 6: Teste Funcional**
```bash
# Criar workflow de teste via API
curl -X POST http://localhost:5678/rest/workflows \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Test Restore",
        "nodes": [
            {
                "name": "Start",
                "type": "n8n-nodes-base.start",
                "position": [250, 300]
            },
            {
                "name": "GoogleSheets",
                "type": "n8n-nodes-base.googleSheets",
                "credentials": {
                    "googleSheetsOAuth2Api": {
                        "id": "cred-google-001"  # ID restaurado
                    }
                },
                "position": [450, 300]
            }
        ]
    }'

# Executar workflow
curl -X POST http://localhost:5678/rest/workflows/[ID]/execute

# Verificar sucesso (não erro de autenticação)
```

**Passo 7: Limpeza**
```bash
# Remover backup temporário (SE teste passou)
rm -rf /tmp/n8n-pre-restore-*

# Documentar restore
echo "$(date): Restore de /backup/.../20260120-020000 concluído" \
    >> /var/log/n8n-restore.log
```

---

## Seção 4: Requisitos Técnicos

### Pré-requisitos de Sistema Explicados

**"N8N versão 2.3.0 ou superior"**:
- **Por que**: Comandos CLI `export:credentials` e `import:credentials` introduzidos na v2.x
- **Verificação**: `n8n --version` ou `docker exec n8n n8n --version`
- **Upgrade**: Consultar changelogs para breaking changes antes

**"Acesso ao terminal/CLI"**:
- **Docker**: `docker exec -it n8n-container bash`
- **npm**: Executar diretamente no shell do servidor
- **Kubernetes**: `kubectl exec -it pod/n8n-xxx -- bash`

**"Permissões adequadas"**:
```bash
# Testar permissões
touch /backup/test && rm /backup/test
# Se falhar: sudo chown $USER /backup ou ajustar ACLs

# Verificar permissões N8N
ls -la ~/.n8n/
# Deve ser owned por usuário que roda N8N
```

**"N8N_ENCRYPTION_KEY configurada"**:
```bash
# Verificar variável
echo $N8N_ENCRYPTION_KEY
# Deve retornar string de 32+ caracteres

# Em Docker
docker exec n8n printenv N8N_ENCRYPTION_KEY

# Se não configurada
export N8N_ENCRYPTION_KEY=$(openssl rand -hex 16)
# Gera chave aleatória de 32 caracteres hex

# Persistir em .env ou secrets manager
```

### Estrutura de Arquivos Explicada

**Credenciais JSON**:
```json
{
  "id": "cred-google-001",           // UUID único
  "name": "Google Sheets API",        // Nome amigável
  "type": "googleSheetsOAuth2Api",    // Tipo de credencial
  "data": "U2FsdGVkX1+ABC...XYZ==",   // Dados criptografados Base64
  "createdAt": "2026-01-15T10:30:00", // Timestamp criação
  "updatedAt": "2026-01-20T14:20:00"  // Timestamp última atualização
}
```

**Campo `data` explicado**:
- Contém OAuth tokens, API keys, passwords
- Criptografado com AES-256-CBC usando N8N_ENCRYPTION_KEY
- Codificado em Base64 para transporte JSON
- **NUNCA** edite manualmente; corrompe criptografia

**Workflows JSON**:
```json
{
  "id": "workflow-crm-sync",
  "name": "CRM Sync Daily",
  "nodes": [                          // Array de nós
    {
      "id": "node-start",
      "type": "n8n-nodes-base.start",
      "position": [250, 300]
    },
    {
      "id": "node-salesforce",
      "type": "n8n-nodes-base.salesforce",
      "credentials": {
        "salesforceOAuth2Api": {
          "id": "cred-salesforce-001" // Referência a credencial
        }
      },
      "parameters": {
        "resource": "contact",
        "operation": "getAll"
      }
    }
  ],
  "connections": {                    // Conexões entre nós
    "node-start": {
      "main": [[{"node": "node-salesforce"}]]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveDataErrorExecution": "all"
  },
  "active": true,                     // Se workflow está ativo
  "createdAt": "2026-01-10T09:00:00",
  "updatedAt": "2026-01-20T11:15:00"
}
```

**Campo `connections` explicado**:
- Define fluxo de execução entre nós
- `"main"`: canal principal de dados
- Array aninhado permite múltiplas saídas (branching)

---

## Seção 5: Troubleshooting Detalhado

### "Command not found" - Diagnóstico Completo

**Cenário 1: N8N não está no PATH**
```bash
# Verificar
which n8n
# Se retornar vazio, não está no PATH

# Solução: Encontrar binário
find /usr -name n8n 2>/dev/null
find /opt -name n8n 2>/dev/null
find ~ -name n8n 2>/dev/null

# Usar caminho absoluto
/usr/local/bin/n8n export:credentials ...

# Ou adicionar ao PATH
export PATH=$PATH:/caminho/para/n8n
```

**Cenário 2: N8N em Docker**
```bash
# Comando não funciona no host
n8n export:credentials ...  # ❌ Erro

# Solução: Executar dentro do container
docker exec n8n-container n8n export:credentials --backup --output=/data/backup/

# Copiar backup para host
docker cp n8n-container:/data/backup/ /host/backup/
```

**Cenário 3: npm global não encontrado**
```bash
# Verificar instalação npm
npm list -g n8n
# Se não listado, não instalado

# Instalar
npm install -g n8n

# Verificar novamente
which n8n  # Deve retornar /usr/local/bin/n8n ou similar
```

### Erro de Criptografia - Análise Profunda

**Mensagem de erro típica**:
```
Error: Error decrypting credentials data:
Malformed UTF-8 data
```

**Causa raiz**:
```bash
# Backup feito com chave A
export N8N_ENCRYPTION_KEY="chave-original-abc123"
n8n export:credentials --backup --output=/backup/

# Restore tentado com chave B (DIFERENTE)
export N8N_ENCRYPTION_KEY="chave-errada-xyz789"  # ❌ ERRO
n8n import:credentials --input=/backup/
# Falha: não consegue descriptografar
```

**Solução**:
```bash
# 1. Recuperar chave original
# De: Vault, Secrets Manager, documentação, .env backup

# 2. Configurar corretamente
export N8N_ENCRYPTION_KEY="chave-original-abc123"

# 3. Tentar restore novamente
n8n import:credentials --input=/backup/

# 4. Verificar sucesso
echo $?  # Deve retornar 0 (sucesso)
```

**Prevenção**:
- Armazenar chave em múltiplos locais seguros
- Documentar em runbook de disaster recovery
- Testar restore regularmente para validar chave

### Permissões Negadas - Resolução Sistemática

**Erro**: `EACCES: permission denied, open '/backup/credentials.json'`

**Diagnóstico**:
```bash
# Verificar ownership do diretório
ls -ld /backup/
# drwxr-xr-x 2 root root ...  ← Owned by root

# Verificar usuário atual
whoami
# n8n  ← N8N roda como usuário 'n8n'

# Problema: n8n tentando escrever em diretório de root
```

**Soluções por prioridade**:

1. **Mudar ownership (recomendado)**:
```bash
sudo chown -R n8n:n8n /backup/
# -R: recursivo, todos os subdiretórios
# n8n:n8n: usuário:grupo
```

2. **Ajustar permissões**:
```bash
sudo chmod 775 /backup/
# 7 (owner): rwx
# 7 (group): rwx
# 5 (others): r-x
```

3. **Usar diretório em home**:
```bash
# Como usuário n8n
mkdir -p ~/backups/n8n
n8n export:credentials --backup --output=~/backups/n8n/
# Sempre tem permissão em ~
```

4. **Sudo (último recurso, não recomendado)**:
```bash
sudo -u n8n n8n export:credentials --backup --output=/backup/
# Executa como usuário n8n via sudo
```

### Backup Vazio ou Incompleto

**Sintoma**: Arquivos JSON existem mas estão vazios ou muito pequenos.

**Diagnóstico**:
```bash
# Verificar tamanho
ls -lh /backup/credenciais/
# -rw-r--r-- 1 n8n n8n 2 Jan 20 10:30 cred-001.json  ← 2 bytes = vazio

# Inspecionar conteúdo
cat /backup/credenciais/cred-001.json
# {}  ← Vazio
```

**Causas possíveis**:

1. **Nenhuma credencial na instância**:
```bash
# Verificar no banco
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite \
    "SELECT COUNT(*) FROM credentials_entity;"
# 0  ← Nenhuma credencial para exportar

# Solução: Criar credenciais na UI primeiro
```

2. **N8N_ENCRYPTION_KEY não configurada no export**:
```bash
# Verificar variável no momento do export
docker exec n8n printenv | grep ENCRYPTION
# Se vazio, credenciais não foram criptografadas/exportadas

# Solução: Configurar e re-exportar
docker exec -e N8N_ENCRYPTION_KEY=... n8n n8n export:credentials ...
```

3. **Erro silencioso no export**:
```bash
# Verificar logs
docker logs n8n --tail 100 | grep -i error
# Pode revelar erro de banco, disco cheio, etc.

# Executar com debug
N8N_LOG_LEVEL=debug n8n export:credentials --backup --output=/backup/
# Mostra detalhes de cada credencial exportada
```

---

## Seção 6: Segurança e Compliance

### Armazenamento Seguro - Melhores Práticas

**Criptografia em Camadas**:
1. **Camada 1**: Dados já criptografados com N8N_ENCRYPTION_KEY
2. **Camada 2**: Filesystem encryption (LUKS, BitLocker)
3. **Camada 3**: Encryption at rest na nuvem (KMS, Key Vault)

**Exemplo AWS S3**:
```bash
# Upload com Server-Side Encryption
aws s3 cp /backup/credenciais/ s3://empresa-backups/n8n/credenciais/ \
    --recursive \
    --sse aws:kms \
    --sse-kms-key-id arn:aws:kms:us-east-1:123456789:key/abc-def \
    --storage-class STANDARD_IA
```

Explicação:
- `--sse aws:kms`: Usar AWS KMS para encryption
- `--sse-kms-key-id`: Chave KMS específica
- `--storage-class STANDARD_IA`: Infrequent Access (menor custo)

**Controle de Acesso (RBAC)**:
```yaml
# AWS IAM Policy exemplo
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::empresa-backups/n8n/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "192.168.1.0/24"  # Apenas de rede interna
        }
      }
    }
  ]
}
```

**Rotação de Backups**:
```bash
#!/bin/bash
# Script de rotação

BACKUP_DIR="/backup/n8n/credenciais"

# Manter últimos 7 diários
find "$BACKUP_DIR" -type d -mtime +7 -name "202*" -exec rm -rf {} +

# Mover backups de domingo para /mensais
# (assumindo backup diário às 2 AM)
if [ $(date +%u) -eq 7 ]; then  # 7 = domingo
    MONTHLY_DIR="/backup/n8n/mensais/$(date +%Y%m)"
    mkdir -p "$MONTHLY_DIR"
    cp -r "$BACKUP_DIR/$(date +%Y%m%d)*" "$MONTHLY_DIR/"
fi
```

### Gestão de Chaves - Estratégias

**HashiCorp Vault (Recomendado para Produção)**:
```bash
# Armazenar chave no Vault
vault kv put secret/n8n/encryption key="$N8N_ENCRYPTION_KEY"

# Recuperar em runtime
export N8N_ENCRYPTION_KEY=$(vault kv get -field=key secret/n8n/encryption)

# N8N usa automaticamente a variável de ambiente
```

**AWS Secrets Manager**:
```bash
# Criar secret
aws secretsmanager create-secret \
    --name n8n/encryption-key \
    --secret-string "$N8N_ENCRYPTION_KEY"

# Recuperar em script
export N8N_ENCRYPTION_KEY=$(aws secretsmanager get-secret-value \
    --secret-id n8n/encryption-key \
    --query SecretString \
    --output text)
```

**Disaster Recovery Offline**:
```markdown
# Documento físico guardado em cofre

N8N ENCRYPTION KEY - CONFIDENCIAL
Ambiente: Produção
Data: 20/01/2026
Chave: [32-caracteres-hex-aqui]
Responsável: DevOps Lead
Localização Backup: s3://empresa-backups/n8n/

Instruções de Uso:
1. Acessar servidor de produção
2. export N8N_ENCRYPTION_KEY="[chave-acima]"
3. Executar restore conforme runbook
```

---

## Seção 7: Referências e Recursos

### Documentação Oficial - Como Usar

**N8N CLI Commands**:
- URL: https://docs.n8n.io/hosting/cli-commands/
- **Quando consultar**: Verificar novos comandos em versões futuras, sintaxe exata de flags
- **Seções relevantes**: 
  - Export workflows and credentials
  - Import workflows and credentials
  - Database operations

**N8N Configuration**:
- URL: https://docs.n8n.io/hosting/configuration/
- **Quando consultar**: Configurar N8N_ENCRYPTION_KEY, outras variáveis de ambiente
- **Variáveis críticas**:
  - `N8N_ENCRYPTION_KEY`: Criptografia de credenciais
  - `N8N_HOST`: URL público do N8N
  - `DB_TYPE`: Tipo de banco (SQLite, PostgreSQL, MySQL)

**N8N Release Notes**:
- URL: https://docs.n8n.io/release-notes/
- **Quando consultar**: Antes de upgrade, para verificar breaking changes
- **Procurar por**: "credentials", "encryption", "export", "import"

### Ambiente Python e Ferramentas

**uv - Gerenciador de Ambiente Virtual e Pacotes**:
```bash
# Instalar
curl -LsSf https://astral.sh/uv/install.sh | sh

# Criar ambiente
uv venv .venv --python 3.11

# Instalar dependências (10-100x mais rápido que pip)
uv pip sync requirements.txt

# Atualizar dependências
uv pip compile requirements.in -o requirements.txt --upgrade
```

**Documentação completa**: Ver `docs/recursos-python-docker.md` para análise detalhada de todas as 25+ bibliotecas Python essenciais para o projeto.

**Bibliotecas Python Core**:
- `docker` (docker-py): API nativa para controle de containers
- `requests`/`httpx`: Cliente HTTP para healthchecks
- `pydantic`: Validação de schemas JSON com type hints
- `boto3`: AWS S3 (ou `azure-storage-blob` para Azure)
- `hvac`: HashiCorp Vault para secrets management
- `tenacity`: Retry automático com backoff exponencial
- `click`: Interface CLI robusta
- `pytest`: Framework de testes

### Ferramentas de Sistema

**jq - JSON Processor**:
```bash
# Instalar
sudo apt install jq  # Ubuntu/Debian
brew install jq      # macOS

# Validar JSON
jq empty arquivo.json
# Sem output = válido; com erro = inválido

# Extrair campo específico
jq '.name' credencial.json
# "Google Sheets API"

# Contar credenciais em diretório
jq -s 'length' /backup/credenciais/*.json
# 15
```

**rsync - Sincronização**:
```bash
# Backup incremental para servidor remoto
rsync -avz --delete \
    /backup/n8n/ \
    backup-server:/backups/n8n/
# -a: archive (preserva permissões, timestamps)
# -v: verbose
# -z: compressão
# --delete: remove no destino arquivos deletados na origem
```

**aws-cli - Upload S3**:
```bash
# Instalar
pip install awscli

# Configurar
aws configure
# Pedir Access Key ID, Secret, região

# Sync para S3
aws s3 sync /backup/n8n/ s3://empresa-backups/n8n/ \
    --exclude "*.log" \
    --storage-class GLACIER
```

---

## Apêndice: Scripts Completos de Produção

### Script Completo de Backup Automatizado

```bash
#!/bin/bash
#
# n8n-backup.sh - Script automatizado de backup N8N
# Uso: ./n8n-backup.sh
#

set -euo pipefail  # Sair em caso de erro

# ==================== CONFIGURAÇÕES ====================
SERVER_NAME=$(hostname)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BASE="/tmp/bkpfile"
BACKUP_PREFIX="${TIMESTAMP}-${SERVER_NAME}-n8n"
N8N_CONTAINER="n8n-container"
N8N_IMAGE="n8nio/n8n:latest"

# Configuração de repositório remoto
REMOTE_BACKUP_SERVER="backup-server"
REMOTE_BACKUP_PATH="/backups/n8n"

# ==================== FUNÇÕES ====================
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

cleanup() {
    log "Limpando backups antigos (>7 dias)..."
    find "${BACKUP_BASE}" -type d -mtime +7 -name "*-n8n-*" -exec rm -rf {} + 2>/dev/null || true
}

# ==================== PRÉ-VERIFICAÇÕES ====================
log "Iniciando backup N8N - ${BACKUP_PREFIX}"

# Verificar se container N8N está rodando
if ! docker ps --format '{{.Names}}' | grep -q "^${N8N_CONTAINER}$"; then
    error "Container ${N8N_CONTAINER} não está rodando!"
fi

# Criar diretório base
mkdir -p "${BACKUP_BASE}"

# ==================== BACKUP WORKFLOWS ====================
log "Exportando workflows..."
docker run --rm \
  --volumes-from "${N8N_CONTAINER}" \
  -v "${BACKUP_BASE}:/backup" \
  "${N8N_IMAGE}" \
  n8n export:workflow --backup --output="/backup/${BACKUP_PREFIX}-workflows/"

if [ $? -eq 0 ]; then
    WORKFLOW_COUNT=$(find "${BACKUP_BASE}/${BACKUP_PREFIX}-workflows" -name "*.json" | wc -l)
    log "✓ ${WORKFLOW_COUNT} workflows exportados"
else
    error "Falha ao exportar workflows"
fi

# ==================== BACKUP CREDENCIAIS ====================
log "Exportando credenciais..."
docker run --rm \
  --volumes-from "${N8N_CONTAINER}" \
  -v "${BACKUP_BASE}:/backup" \
  "${N8N_IMAGE}" \
  n8n export:credentials --backup --output="/backup/${BACKUP_PREFIX}-credentials/"

if [ $? -eq 0 ]; then
    CRED_COUNT=$(find "${BACKUP_BASE}/${BACKUP_PREFIX}-credentials" -name "*.json" | wc -l)
    log "✓ ${CRED_COUNT} credenciais exportadas"
else
    error "Falha ao exportar credenciais"
fi

# ==================== VALIDAÇÃO ====================
log "Validando integridade dos backups..."
INVALID=0
for json_file in "${BACKUP_BASE}/${BACKUP_PREFIX}"-*/*.json; do
    if ! jq empty "$json_file" 2>/dev/null; then
        log "⚠️ Arquivo inválido: $json_file"
        ((INVALID++))
    fi
done

if [ $INVALID -gt 0 ]; then
    error "${INVALID} arquivo(s) JSON inválido(s)"
fi

log "✓ Todos os arquivos JSON são válidos"

# ==================== ENVIO PARA REPOSITÓRIO ====================
log "Enviando para repositório remoto..."

# Opção 1: rsync
rsync -avz --progress \
  "${BACKUP_BASE}/${BACKUP_PREFIX}"-* \
  "${REMOTE_BACKUP_SERVER}:${REMOTE_BACKUP_PATH}/" \
  && log "✓ Backup enviado via rsync" \
  || error "Falha ao enviar backup via rsync"

# Opção 2: rclone (comentado, descomente se usar)
# rclone copy "${BACKUP_BASE}/" remote:n8n-backups/ \
#   --include "${BACKUP_PREFIX}-*/**" \
#   && log "✓ Backup enviado via rclone"

# Opção 3: AWS S3 (comentado, descomente se usar)
# aws s3 sync "${BACKUP_BASE}/" s3://empresa-backups/n8n/ \
#   --exclude "*" --include "${BACKUP_PREFIX}-*/*" \
#   --sse AES256 \
#   && log "✓ Backup enviado para S3"

# ==================== LIMPEZA ====================
cleanup

# ==================== RESUMO ====================
BACKUP_SIZE=$(du -sh "${BACKUP_BASE}/${BACKUP_PREFIX}"-* | awk '{print $1}' | paste -sd+ | bc)
log "=========================================="
log "Backup concluído com sucesso!"
log "Prefix: ${BACKUP_PREFIX}"
log "Workflows: ${WORKFLOW_COUNT}"
log "Credenciais: ${CRED_COUNT}"
log "Tamanho total: ${BACKUP_SIZE}"
log "=========================================="

# Opcional: Enviar notificação (Slack, email, etc.)
# curl -X POST https://hooks.slack.com/... \
#   -d "{\"text\":\"Backup N8N concluído: ${BACKUP_PREFIX}\"}"

exit 0
```

**Instalação e configuração**:
```bash
# Salvar script
sudo nano /usr/local/bin/n8n-backup.sh

# Tornar executável
sudo chmod +x /usr/local/bin/n8n-backup.sh

# Testar manualmente
/usr/local/bin/n8n-backup.sh

# Adicionar ao crontab para execução diária às 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/n8n-backup.sh >> /var/log/n8n-backup.log 2>&1") | crontab -
```

---

### Script Completo de Restore

```bash
#!/bin/bash
#
# n8n-restore.sh - Script de restore N8N
# Uso: ./n8n-restore.sh <BACKUP_PREFIX>
# Exemplo: ./n8n-restore.sh 20260120-020000-prod-server-n8n
#

set -euo pipefail

# ==================== CONFIGURAÇÕES ====================
BACKUP_TO_RESTORE="${1:-}"
BACKUP_BASE="/tmp/bkpfile"
SERVER_NAME=$(hostname)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ROLLBACK_PREFIX="${TIMESTAMP}-${SERVER_NAME}-n8n-rollback"
N8N_CONTAINER="n8n-container"
N8N_IMAGE="n8nio/n8n:latest"

REMOTE_BACKUP_SERVER="backup-server"
REMOTE_BACKUP_PATH="/backups/n8n"

# ==================== FUNÇÕES ====================
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

usage() {
    echo "Uso: $0 <BACKUP_PREFIX>"
    echo "Exemplo: $0 20260120-020000-prod-server-n8n"
    echo ""
    echo "Backups disponíveis no repositório:"
    ssh "${REMOTE_BACKUP_SERVER}" "ls -1d ${REMOTE_BACKUP_PATH}/*-n8n-credentials 2>/dev/null | xargs -n1 basename | sed 's/-credentials//'"
    exit 1
}

# ==================== VALIDAÇÕES ====================
[ -z "$BACKUP_TO_RESTORE" ] && usage

log "=========================================="
log "RESTORE N8N"
log "Backup: ${BACKUP_TO_RESTORE}"
log "=========================================="

# Confirmar com usuário
read -p "⚠️  ATENÇÃO: Esta operação irá SOBRESCREVER dados atuais. Continuar? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    log "Operação cancelada pelo usuário"
    exit 0
fi

# Verificar se container está rodando
if ! docker ps --format '{{.Names}}' | grep -q "^${N8N_CONTAINER}$"; then
    log "Container não está rodando. Iniciando..."
    docker start "${N8N_CONTAINER}"
    sleep 5
fi

mkdir -p "${BACKUP_BASE}"

# ==================== DOWNLOAD DO BACKUP ====================
log "Baixando backup do repositório..."
rsync -avz --progress \
  "${REMOTE_BACKUP_SERVER}:${REMOTE_BACKUP_PATH}/${BACKUP_TO_RESTORE}"-* \
  "${BACKUP_BASE}/" \
  || error "Falha ao baixar backup"

# Verificar arquivos
if [ ! -d "${BACKUP_BASE}/${BACKUP_TO_RESTORE}-credentials" ]; then
    error "Diretório de credenciais não encontrado"
fi
if [ ! -d "${BACKUP_BASE}/${BACKUP_TO_RESTORE}-workflows" ]; then
    error "Diretório de workflows não encontrado"
fi

log "✓ Backup baixado"

# ==================== BACKUP DE SEGURANÇA ====================
log "Criando backup de segurança do estado atual..."

docker run --rm \
  --volumes-from "${N8N_CONTAINER}" \
  -v "${BACKUP_BASE}:/backup" \
  "${N8N_IMAGE}" \
  n8n export:credentials --backup --output="/backup/${ROLLBACK_PREFIX}-credentials/" \
  || error "Falha ao criar backup de segurança (credenciais)"

docker run --rm \
  --volumes-from "${N8N_CONTAINER}" \
  -v "${BACKUP_BASE}:/backup" \
  "${N8N_IMAGE}" \
  n8n export:workflow --backup --output="/backup/${ROLLBACK_PREFIX}-workflows/" \
  || error "Falha ao criar backup de segurança (workflows)"

log "✓ Backup de segurança criado: ${ROLLBACK_PREFIX}"

# ==================== DESABILITAR WORKFLOWS ====================
log "Desabilitando workflows ativos..."
curl -s -X POST http://localhost:5678/rest/workflows/deactivate-all || log "⚠️ Não foi possível desabilitar workflows via API"

# ==================== RESTORE ====================
log "Restaurando credenciais..."
docker run --rm \
  --volumes-from "${N8N_CONTAINER}" \
  -v "${BACKUP_BASE}:/backup" \
  "${N8N_IMAGE}" \
  n8n import:credentials --separate --input="/backup/${BACKUP_TO_RESTORE}-credentials/"

if [ $? -ne 0 ]; then
    error "Falha ao restaurar credenciais. Backup de segurança disponível em: ${ROLLBACK_PREFIX}"
fi

CRED_COUNT=$(find "${BACKUP_BASE}/${BACKUP_TO_RESTORE}-credentials" -name "*.json" | wc -l)
log "✓ ${CRED_COUNT} credenciais restauradas"

log "Restaurando workflows..."
docker run --rm \
  --volumes-from "${N8N_CONTAINER}" \
  -v "${BACKUP_BASE}:/backup" \
  "${N8N_IMAGE}" \
  n8n import:workflow --separate --input="/backup/${BACKUP_TO_RESTORE}-workflows/"

if [ $? -ne 0 ]; then
    error "Falha ao restaurar workflows. Backup de segurança disponível em: ${ROLLBACK_PREFIX}"
fi

WORKFLOW_COUNT=$(find "${BACKUP_BASE}/${BACKUP_TO_RESTORE}-workflows" -name "*.json" | wc -l)
log "✓ ${WORKFLOW_COUNT} workflows restaurados"

# ==================== VERIFICAÇÃO ====================
log "Verificando restore..."
sleep 5

# Verificar via API
CRED_API=$(curl -s http://localhost:5678/rest/credentials 2>/dev/null | jq '.data | length' 2>/dev/null || echo "0")
WORKFLOW_API=$(curl -s http://localhost:5678/rest/workflows 2>/dev/null | jq '.data | length' 2>/dev/null || echo "0")

log "Credenciais na API: ${CRED_API}"
log "Workflows na API: ${WORKFLOW_API}"

# ==================== RESUMO ====================
log "=========================================="
log "✓ RESTORE CONCLUÍDO COM SUCESSO"
log "Backup restaurado: ${BACKUP_TO_RESTORE}"
log "Credenciais: ${CRED_COUNT}"
log "Workflows: ${WORKFLOW_COUNT}"
log "Backup de segurança: ${ROLLBACK_PREFIX}"
log "=========================================="
log ""
log "PRÓXIMOS PASSOS:"
log "1. Verificar logs: docker logs ${N8N_CONTAINER} --tail 50"
log "2. Testar workflows críticos na UI"
log "3. Reabilitar workflows se necessário"
log "4. Remover backup de segurança: rm -rf ${BACKUP_BASE}/${ROLLBACK_PREFIX}-*"

exit 0
```

**Uso do script**:
```bash
# Listar backups disponíveis
ssh backup-server "ls -1d /backups/n8n/*-n8n-credentials" | sed 's/-credentials//'

# Executar restore
sudo /usr/local/bin/n8n-restore.sh 20260120-020000-prod-server-n8n

# Monitorar progresso
tail -f /var/log/n8n-restore.log
```

---

## Conclusão

Esta **Constitution** e seu documento de explicação servem como fonte única de verdade para operações de backup/restore no N8N Enterprise. 

**Pontos-chave para memorizar**:
1. **Segurança primeiro**: N8N_ENCRYPTION_KEY é a chave de tudo (literalmente)
2. **`--backup` sempre**: Preserve IDs ou sofra as consequências
3. **Backup antes de restore**: Sempre tenha um plano B
4. **Automatize**: Humanos esquecem, cron não
5. **Teste regularmente**: Backup não testado = backup inexistente
6. **Volume mount**: Use `/tmp/bkpfile` para isolamento e organização
7. **Nomenclatura padronizada**: `YYYYMMDD-HHMMSS-{server}-n8n-{type}`
8. **Repositório centralizado**: Sempre envie backups para repositório externo

**Arquitetura de Backup Recomendada**:
```
┌─────────────────┐
│   Servidor N8N  │
│                 │
│  ┌───────────┐  │
│  │ Container │  │
│  │    N8N    │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ /tmp/     │  │ (1) Backup local
│  │  bkpfile  │  │     YYYYMMDD-HHMMSS-server-n8n-*
│  └─────┬─────┘  │
└────────┼────────┘
         │
         │ (2) Envio automatizado
         │     (rsync/rclone/S3)
         │
         ▼
┌────────────────────────┐
│  Repositório de Backup │
│                        │
│  • Servidor remoto     │
│  • Cloud Storage       │
│  • NAS/SAN             │
│                        │
│  Retenção:             │
│  • Diários: 7 dias     │
│  • Semanais: 4 semanas │
│  • Mensais: 12 meses   │
└────────────────────────┘
```

**Próximos passos recomendados**:
- [x] ✅ Scripts automatizados criados (veja Apêndice)
- [ ] Configurar cron para execução diária às 2 AM
- [ ] Configurar servidor/repositório remoto de backup
- [ ] Armazenar N8N_ENCRYPTION_KEY no Vault/Secrets Manager
- [ ] Documentar procedimento de restore no runbook da equipe
- [ ] Agendar teste de restore mensal (primeiro domingo de cada mês)
- [ ] Configurar monitoramento de backups (alertas se falhar)
- [ ] Configurar notificações (Slack/email) para status de backup
- [ ] Validar permissões de acesso a `/tmp/bkpfile` e repositório
- [ ] Testar recuperação completa em ambiente staging

**Comandos rápidos de referência**:
```bash
# Backup manual
docker run --rm --volumes-from n8n-container \
  -v /tmp/bkpfile:/backup n8nio/n8n:latest \
  n8n export:credentials --backup --output=/backup/$(date +%Y%m%d-%H%M%S)-$(hostname)-n8n-credentials/

# Restore manual
docker run --rm --volumes-from n8n-container \
  -v /tmp/bkpfile:/backup n8nio/n8n:latest \
  n8n import:credentials --separate --input=/backup/20260120-020000-server-n8n-credentials/

# Listar backups locais
ls -lth /tmp/bkpfile/ | head -20

# Verificar tamanho de backups
du -sh /tmp/bkpfile/*-n8n-*

# Limpar backups antigos (>7 dias)
find /tmp/bkpfile -type d -mtime +7 -name "*-n8n-*" -delete
```

**Contato para dúvidas**:
- Consultar equipe DevOps
- Abrir issue no repositório interno
- Revisar esta documentação regularmente (atualizar quando N8N for upgradado)
- Scripts de produção disponíveis no Apêndice deste documento
