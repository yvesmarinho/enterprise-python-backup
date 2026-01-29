# Restore de Credenciais no N8N Versão 2.3.0

## Visão Geral

Este documento detalha o processo de restauração (restore) das credenciais no N8N versão 2.3.0. A restauração é usada para recuperar credenciais de um backup, útil em cenários de recuperação de desastre, migração ou rollback de atualizações. As credenciais são importadas criptografadas, preservando IDs para compatibilidade.

## Pré-requisitos

- N8N versão 2.3.0 instalado e configurado.
- Arquivos de backup de credenciais gerados anteriormente (ver documento de backup).
- Chave de criptografia N8N_ENCRYPTION_KEY idêntica à usada no backup.
- Acesso ao terminal CLI do N8N.
- Instância N8N parada ou em modo manutenção para evitar conflitos.

## Procedimento de Restore

### Passo 1: Preparar o Ambiente

1. **Parar o N8N**: Para evitar modificações concorrentes, pare a instância:

```bash
# Docker
docker stop <container_name>

# Processo
pkill -f n8n
```

2. **Verificar Backup**: Confirme que os arquivos de backup existem e são válidos:

```bash
ls -la /caminho/para/backup/credenciais/
# Exemplo: credenciais.json ou múltiplos arquivos .json
```

3. **Backup Atual (Opcional)**: Antes de restaurar, faça backup das credenciais atuais para rollback:

```bash
mkdir -p /tmp/backup-atual
n8n export:credentials --backup --output=/tmp/backup-atual/
```

### Passo 2: Executar o Comando de Importação

Use o comando CLI `n8n import:credentials` para restaurar as credenciais. O flag `--separate` indica que os arquivos estão separados (padrão para backups com --backup). O flag `--input` aponta para o diretório ou arquivo de backup.

```bash
n8n import:credentials --separate --input=/caminho/para/backup/credenciais/
```

- `--separate`: Processa arquivos separados (um por credencial).
- `--input`: Caminho para o diretório contendo os arquivos JSON ou arquivo único.

#### Exemplo Completo

```bash
# Restaurar de diretório com múltiplos arquivos
n8n import:credentials --separate --input=/home/user/n8n-backups/credenciais/

# Restaurar de arquivo único
n8n import:credentials --input=/home/user/n8n-backups/credenciais.json
```

### Passo 3: Verificar a Restauração

Após a importação, inicie o N8N e verifique:

1. **Logs**: Procure mensagens de sucesso nos logs:

```bash
tail -f /home/node/.n8n/logs/n8n.log | grep -i credential
```

2. **Interface Web**: Acesse a UI do N8N e confirme que as credenciais aparecem na seção "Credentials" com IDs e nomes corretos.

3. **Teste de Funcionalidade**: Teste uma credencial importada em um workflow simples para validar descriptografia e funcionamento.

### Passo 4: Limpeza e Reinício

- Remova backups temporários se criados.
- Reinicie o N8N:

```bash
# Docker
docker start <container_name>

# npm
npm run start

# Binário
n8n start
```

## Considerações Técnicas

- **Criptografia**: A restauração requer a mesma N8N_ENCRYPTION_KEY do backup. Se alterada, as credenciais não serão descriptografáveis, resultando em erro.
- **Sobrescrita**: Credenciais com IDs existentes são atualizadas; novas são adicionadas. Não há exclusão automática.
- **Estrutura**: Arquivos JSON devem seguir o formato exportado (id, name, type, data criptografado).
- **Limitações**: Restauração falha se a estrutura do banco de dados mudou significativamente entre versões.
- **Performance**: Em instâncias grandes, monitore CPU/memória durante a importação.

## Script Automatizado

Para automação do restore:

```bash
#!/bin/bash
# restore-credenciais.sh

BACKUP_DIR="$1"
if [ -z "$BACKUP_DIR" ]; then
    echo "Uso: $0 <diretorio_backup>"
    exit 1
fi

echo "Iniciando restore de credenciais de $BACKUP_DIR..."
n8n import:credentials --separate --input="$BACKUP_DIR/"
if [ $? -eq 0 ]; then
    echo "Restore concluído com sucesso."
else
    echo "Erro no restore. Verifique logs e chave de criptografia."
    exit 1
fi
```

Execução:

```bash
./restore-credenciais.sh /home/user/n8n-backups/credenciais/
```

## Troubleshooting

- **Erro de Criptografia**: Verifique N8N_ENCRYPTION_KEY no ambiente.
- **Arquivo Inválido**: Use `jq` para validar JSON: `jq . <arquivo.json>`
- **Permissões**: Execute como usuário N8N.
- **Conflitos de ID**: Se IDs conflitarem, renomeie ou delete credenciais existentes manualmente.
- **Logs Detalhados**: Ative debug: `N8N_LOG_LEVEL=debug n8n import:credentials ...`

## Referências

- Documentação Oficial: https://docs.n8n.io/hosting/cli-commands/#import-workflows-and-credentials
- Repositório: https://github.com/n8n-io/n8n
- Segurança: https://docs.n8n.io/hosting/configuration/#encryption-key